"""`POST /api/runs` and the read endpoints (plan.md P1.3, P1.7)."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import asyncpg
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from anchor.api.errors import ApiError
from anchor.api.serializers.runs import (
    RUN_COLUMNS,
    RunResponse,
    serialize_run,
    serialize_run_list_item,
)
from anchor.api.serializers.timeline import RunTimeline, build_run_timeline
from anchor.core.config.loader import load_runtime_settings
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.runtime.agents.registry import is_registered

router = APIRouter()


async def _load_needs_review_details(
    conn: asyncpg.Connection[Any], run_id: int
) -> dict[str, Any] | None:
    """The most recent `RUN_NEEDS_REVIEW` event's payload for `run_id`, or
    `None` if the run never halted. Read from the event log rather than
    `tool_journal` directly, so the API surfaces exactly what was recorded
    at halt time — `reason` and `available_resolutions` live only on the
    event, not on the journal row (data-model.md §11).
    """
    row = await conn.fetchrow(
        """
        SELECT payload FROM run_events
        WHERE run_id = $1 AND type = 'RUN_NEEDS_REVIEW'
        ORDER BY seq DESC
        LIMIT 1
        """,
        run_id,
    )
    if row is None:
        return None
    payload: dict[str, Any] = json.loads(row["payload"])
    return payload


async def _open_journal_row(conn: asyncpg.Connection[Any], run_id: int) -> asyncpg.Record | None:
    """The single open (`result IS NULL`) `tool_journal` row for this run —
    the call that caused the halt. At most one exists at a time: one side
    effect per step (D-26) plus the fact that nothing else executes once a
    run has halted for review.
    """
    return await conn.fetchrow(
        """
        SELECT idempotency_key, step_index, tool_name
        FROM tool_journal
        WHERE run_id = $1 AND result IS NULL
        ORDER BY intent_at DESC
        LIMIT 1
        """,
        run_id,
    )


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


class RunSubmission(BaseModel):
    agent_type: str
    input: dict[str, Any] = Field(default_factory=dict)
    client_request_key: str | None = None
    priority: int = 0
    is_demo: bool = False


_RUN_ROW_SQL = f"SELECT {RUN_COLUMNS} FROM runs WHERE id = $1"


def _encode_cursor(created_at: datetime, run_id: int) -> str:
    """Opaque keyset cursor over `(created_at, id)` — the same pair the
    `ORDER BY` sorts on, so the page boundary is stable even while newer
    rows are being inserted concurrently (T071/T098).
    """
    raw = f"{created_at.isoformat()}|{run_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        created_at_str, run_id_str = raw.rsplit("|", 1)
        return datetime.fromisoformat(created_at_str), int(run_id_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ApiError(
            status_code=422, error="malformed_cursor", message="malformed cursor"
        ) from exc


@router.post("/api/runs", response_model=RunResponse, status_code=201)
async def submit_run(
    submission: RunSubmission,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> RunResponse:
    if not is_registered(submission.agent_type):
        raise ApiError(
            status_code=404,
            error="unknown_agent",
            message=f"unknown agent_type: {submission.agent_type}",
        )

    async with pool.acquire() as conn:
        settings = await load_runtime_settings(conn)
        async with conn.transaction():
            if submission.client_request_key is not None:
                existing = await conn.fetchrow(
                    "SELECT id FROM runs WHERE client_request_key = $1",
                    submission.client_request_key,
                )
                if existing is not None:
                    row = await conn.fetchrow(_RUN_ROW_SQL, existing["id"])
                    assert row is not None
                    return serialize_run(row)

            run_row = await conn.fetchrow(
                """
                INSERT INTO runs (agent_type, input, client_request_key, priority, is_demo)
                VALUES ($1, $2::jsonb, $3, $4, $5)
                RETURNING id, epoch
                """,
                submission.agent_type,
                json.dumps(submission.input),
                submission.client_request_key,
                submission.priority,
                submission.is_demo,
            )
            assert run_row is not None
            run_id, epoch = run_row["id"], run_row["epoch"]

            await append(
                conn,
                run_id=run_id,
                type=EventType.RUN_SUBMITTED,
                payload={
                    "agent_type": submission.agent_type,
                    "input": submission.input,
                    "is_demo": submission.is_demo,
                    "client_request_key": submission.client_request_key,
                },
                epoch=epoch,
                worker_id="api",
                max_payload_bytes=settings.max_event_payload_bytes,
            )

            row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
            assert row is not None
            return serialize_run(row)


@router.get("/api/runs")
async def list_runs(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    status: Annotated[list[str] | None, Query()] = None,
    agent_type: Annotated[str | None, Query()] = None,
    is_demo: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query()] = 50,
    cursor: Annotated[str | None, Query()] = None,
    include_archived: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Newest first, keyset-paginated on `(created_at, id)` — never
    offset-based, so a page boundary stays correct while runs are being
    submitted concurrently (contracts/openapi.yaml `RunListItem`, which
    requires `summary` and `segments` per row — the same shape
    `GET /api/runs/{id}/timeline` derives, reused here rather than
    duplicated).

    Excludes archived runs by default (migration 005, T361-T362) —
    `POST /api/runs/demo/reset`'s target set — via `include_archived=true`.

    **A known N+1, stated rather than hidden**: each row's `segments` and
    `summary` are built by `build_run_timeline`, one call per row, because
    that is the one place this system computes them correctly (including
    the live `duplicate_side_effects` correctness read, D-30) and
    duplicating that logic into a batch query would be exactly the "same
    conceptual value computed two ways" the constitution's anti-patterns
    reject. Acceptable at this project's demo scale (page sizes up to 200);
    a batched variant would be the right optimization for a production
    listing endpoint, not attempted here without it being asked for.
    """
    page_size = min(limit, 200)
    async with pool.acquire() as conn:
        clauses = []
        params: list[Any] = []
        if not include_archived:
            clauses.append("archived_at IS NULL")
        if status:
            status_list = [status] if isinstance(status, str) else list(status)
            status_list = [s for s in status_list if s]
            if status_list:
                params.append(status_list)
                clauses.append(f"status = ANY(${len(params)})")
        if agent_type:
            params.append(agent_type)
            clauses.append(f"agent_type = ${len(params)}")
        if is_demo is not None:
            params.append(is_demo)
            clauses.append(f"is_demo = ${len(params)}")
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            params.append(cursor_created_at)
            params.append(cursor_id)
            clauses.append(f"(created_at, id) < (${len(params) - 1}, ${len(params)})")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(page_size)
        rows = await conn.fetch(
            f"""
            SELECT {RUN_COLUMNS}
            FROM runs
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ${len(params)}
            """,
            *params,
        )
        db_now = await conn.fetchval("SELECT now()")
        # Needs review is its own page, never only a filter (§13.3) — this
        # is what the filter path returns when it is used. One extra query
        # per needs_review row: rare in steady state (T279's whole point
        # is that a halted run holds no lease and cannot silently pile up
        # unnoticed), so this is not the hot path list_runs otherwise is.
        needs_review_by_id = {
            r["id"]: await _load_needs_review_details(conn, r["id"])
            for r in rows
            if r["status"] == "needs_review"
        }

        items = []
        for r in rows:
            timeline = await build_run_timeline(conn, r["id"])
            assert timeline is not None  # r came from `runs` in this same transaction snapshot
            items.append(
                serialize_run_list_item(
                    r,
                    db_now=db_now,
                    segments=timeline.segments,
                    summary=timeline.summary,
                    needs_review=needs_review_by_id.get(r["id"]),
                ).model_dump()
            )

    next_cursor = (
        _encode_cursor(rows[-1]["created_at"], rows[-1]["id"]) if len(rows) == page_size else None
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: int, pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> RunResponse:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
        if row is None:
            raise ApiError(status_code=404, error="run_not_found", message="run not found")
        needs_review = (
            await _load_needs_review_details(conn, run_id)
            if row["status"] == "needs_review"
            else None
        )
    return serialize_run(row, needs_review=needs_review)


@router.get("/api/runs/{run_id}/events")
async def get_run_events(
    run_id: int,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    after_seq: int = 0,
    limit: int = 200,
) -> dict[str, Any]:
    page_size = min(limit, 1000)
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM runs WHERE id = $1", run_id)
        if not exists:
            raise ApiError(status_code=404, error="run_not_found", message="run not found")
        rows = await conn.fetch(
            """
            SELECT run_id, seq, type, payload, epoch, worker_id, step_index, created_at
            FROM run_events
            WHERE run_id = $1 AND seq > $2
            ORDER BY seq ASC
            LIMIT $3
            """,
            run_id,
            after_seq,
            page_size,
        )
    items = [
        {
            "run_id": r["run_id"],
            "seq": r["seq"],
            "type": r["type"],
            "payload": json.loads(r["payload"]),
            "epoch": r["epoch"],
            "worker_id": r["worker_id"],
            "step_index": r["step_index"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
    next_after_seq = items[-1]["seq"] if len(items) == page_size else None
    return {"run_id": run_id, "items": items, "next_after_seq": next_after_seq}


@router.get("/api/runs/{run_id}/timeline", response_model=RunTimeline)
async def get_run_timeline(
    run_id: int, pool: Annotated[asyncpg.Pool, Depends(get_pool)]
) -> RunTimeline:
    """`contracts/openapi.yaml` `RunTimeline` (plan.md P6.9, T346). Also
    exactly what `WS /ws/runs/{run_id}` sends as its `snapshot` frame
    (contracts/websocket.md) — one builder, reused, so the two surfaces
    can never silently diverge in shape.
    """
    async with pool.acquire() as conn:
        timeline = await build_run_timeline(conn, run_id)
    if timeline is None:
        raise ApiError(status_code=404, error="run_not_found", message="run not found")
    return timeline


@router.get("/api/runs/{run_id}/effects")
async def get_run_effects(
    run_id: int, pool: Annotated[asyncpg.Pool, Depends(get_pool)]
) -> dict[str, Any]:
    """`demo_effects` rows for this run — the proof surface (§21.5). A
    count of 1 beside a timeline showing an interruption is a claim a
    reviewer can verify without trusting the log (P5.9, T290).
    """
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM runs WHERE id = $1", run_id)
        if not exists:
            raise ApiError(status_code=404, error="run_not_found", message="run not found")
        rows = await conn.fetch(
            """
            SELECT id, run_id, step_index, tool_name, idempotency_key, payload, executed_at
            FROM demo_effects
            WHERE run_id = $1
            ORDER BY step_index ASC
            """,
            run_id,
        )
    items = [
        {
            "id": r["id"],
            "run_id": r["run_id"],
            "step_index": r["step_index"],
            "tool_name": r["tool_name"],
            "idempotency_key": r["idempotency_key"],
            "payload": json.loads(r["payload"]),
            "executed_at": r["executed_at"].isoformat(),
        }
        for r in rows
    ]
    return {"run_id": run_id, "items": items, "total": len(items)}


@router.post("/api/runs/{run_id}/cancel", response_model=RunResponse, status_code=202)
async def cancel_run(
    run_id: int,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    request: Request,
) -> RunResponse:
    """`POST /api/runs/{id}/cancel` (plan.md P6.3, T323, T325; D-54).

    A `pending` run has no owner and no lease, so "the worker checks the
    flag between steps" (FR-054) never applies to it — waiting for a
    worker that will never claim it to notice a flag it can't yet see
    would just be a run stuck `pending` forever with `cancel_requested_at`
    set and nothing ever consulting it. The API finalizes it directly:
    leaseless, so there is no lease to fence against and no worker racing
    this write (D-54).

    A `running` run is different: a worker already owns it, under a lease
    this endpoint has no way to safely preempt without racing that
    worker's own writes. This just records the request; the owning worker
    notices at its next step boundary (`anchor.worker.loop._check_and_apply_cancellation`)
    and finalizes it there, never mid-step (FR-054).

    Any other status (already terminal) is a no-op 409 — cancelling an
    already-finished run has nothing to do.
    """
    async with pool.acquire() as conn:
        run_row = await conn.fetchrow(
            "SELECT status, epoch, is_demo FROM runs WHERE id = $1", run_id
        )
        if run_row is None:
            raise ApiError(status_code=404, error="run_not_found", message="run not found")

        deployment_mode: str = request.app.state.deployment_mode
        if deployment_mode == "demonstration" and not run_row["is_demo"]:
            raise ApiError(
                status_code=403,
                error="non_demo_run",
                message="only demo runs may be cancelled in demonstration mode",
            )

        if run_row["status"] == "pending":
            settings = await load_runtime_settings(conn)
            async with conn.transaction():
                await append(
                    conn,
                    run_id=run_id,
                    type=EventType.RUN_CANCELLED,
                    payload={
                        "requested_at": datetime.now(UTC).isoformat(),
                        "step_index": None,
                        "cancelled_by": "operator",
                    },
                    epoch=run_row["epoch"],
                    worker_id="api",
                    max_payload_bytes=settings.max_event_payload_bytes,
                )
                await conn.execute(
                    "UPDATE runs SET status = 'cancelled', finished_at = now() WHERE id = $1",
                    run_id,
                )
        elif run_row["status"] == "running":
            await conn.execute(
                "UPDATE runs SET cancel_requested_at = now() WHERE id = $1 AND cancel_requested_at IS NULL",
                run_id,
            )
        else:
            raise ApiError(
                status_code=409,
                error="run_already_terminal",
                message=f"run is already {run_row['status']}; cannot cancel",
            )

        row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
        assert row is not None
        return serialize_run(row)


@router.post("/api/runs/demo/reset")
async def reset_demo_runs(pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> dict[str, Any]:
    """ "Clear demo runs" (plan.md P6.13, T361-T362; FR-108, §21.6).

    **Archives, never deletes** (migration 005): `run_events_immutable`
    raises `AN003` on any `UPDATE OR DELETE` against the log unconditionally
    (`I2`), with no administrative carve-out, so a literal `DELETE FROM
    runs` is not available to this endpoint at all — it would fail on the
    foreign key from `run_events` the instant any targeted run had ever
    appended a single event. Setting `archived_at` gets the stated
    requirement ("the runs list stays legible") without touching the log:
    `GET /api/runs` excludes archived rows by default.

    Only **completed** demo runs are archived — `is_demo = true` and a
    terminal status other than `needs_review` (a halted run stays visible;
    archiving it out from under an operator who has not yet resolved it
    would hide exactly the state this product exists to surface).

    **Structurally unable to touch chaos history**: this statement is
    scoped by `runs.is_demo = true` and writes only `runs.archived_at` —
    there is no code path here that reaches `chaos_events` or
    `chaos_reports` at all, because the query never selects from those
    tables in the first place.

    Response key is `runs_deleted` (`contracts/openapi.yaml`) even though
    the mechanism is archival, not deletion — the contract names the
    user-visible effect ("these runs are gone from your list"), which
    archiving achieves exactly; see the docstring above for why a literal
    delete is not available to this endpoint at all.
    """
    async with pool.acquire() as conn:
        archived_ids = await conn.fetch(
            """
            UPDATE runs
            SET archived_at = now()
            WHERE is_demo = true
              AND status IN ('completed', 'failed', 'cancelled')
              AND archived_at IS NULL
            RETURNING id
            """
        )
    return {"runs_deleted": len(archived_ids)}


class ResolveRequest(BaseModel):
    resolution: Literal["mark_executed", "mark_not_executed", "retry"]
    note: str | None = None
    result: dict[str, Any] | None = None


@router.post("/api/runs/{run_id}/resolve", response_model=RunResponse, status_code=202)
async def resolve_run(
    run_id: int,
    body: ResolveRequest,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    request: Request,
) -> RunResponse:
    """Resolve a `needs_review` run (P5.7, T280-T281; D-24, FR-050).

    Permitted only while `status = 'needs_review'`, which is leaseless, so
    this write can never race a worker for ownership of the run (D-24) —
    there is no lease to fence against. The write is attributed to
    `worker_id = 'operator'` at the run's *current* epoch, because a human
    decision inside the uncertainty window belongs in the log, attributably
    (`I8`).

    None of the three outcomes is a guess: `mark_executed` records the
    missing result now, attributed to the operator; `mark_not_executed`
    authorizes execution on the next resumption without re-consulting the
    tool's own (in this case necessarily `unsafe`) declared policy, which
    would just halt again on the same ambiguity the operator just resolved;
    `retry` re-consults that declared policy from a clean slate.
    """
    async with pool.acquire() as conn:
        run_row = await conn.fetchrow(
            "SELECT status, epoch, is_demo FROM runs WHERE id = $1", run_id
        )
        if run_row is None:
            raise ApiError(status_code=404, error="run_not_found", message="run not found")

        deployment_mode: str = request.app.state.deployment_mode
        if deployment_mode == "demonstration" and not run_row["is_demo"]:
            raise ApiError(
                status_code=403,
                error="non_demo_run",
                message="only demo runs may be resolved in demonstration mode",
            )
        if run_row["status"] != "needs_review":
            raise ApiError(
                status_code=409,
                error="run_not_needs_review",
                message="run is not in needs_review",
            )

        epoch = run_row["epoch"]
        journal_row = await _open_journal_row(conn, run_id)
        if journal_row is None:
            # Should be unreachable — a needs_review run always halted on
            # exactly one open journal row (halt_needs_review always
            # follows an Uncertain lookup) — but a bare assert here would
            # be an internal-error crash a caller cannot act on, so this
            # names the actual state instead.
            raise ApiError(
                status_code=409,
                error="no_open_uncertainty_window",
                message="no open uncertainty window found for this run",
            )

        settings = await load_runtime_settings(conn)

        if body.resolution == "mark_executed":
            operator_result = body.result if body.result is not None else {"operator_marked_executed": True, "note": body.note}
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE tool_journal
                    SET result = $2::jsonb, result_at = now(), result_epoch = $3,
                        resolution = 'operator_marked_executed', resolved_at = now()
                    WHERE idempotency_key = $1
                    """,
                    journal_row["idempotency_key"],
                    json.dumps(operator_result),
                    epoch,
                )
                await append(
                    conn,
                    run_id=run_id,
                    type=EventType.TOOL_RESULT,
                    payload={
                        "step_index": journal_row["step_index"],
                        "tool_name": journal_row["tool_name"],
                        "idempotency_key": journal_row["idempotency_key"],
                        "result": operator_result,
                        "latency_ms": 0.0,
                        "resolution": "operator_marked_executed",
                    },
                    epoch=epoch,
                    worker_id="operator",
                    step_index=journal_row["step_index"],
                    max_payload_bytes=settings.max_event_payload_bytes,
                )
                await conn.execute(
                    "UPDATE runs SET status = 'pending', finished_at = NULL WHERE id = $1", run_id
                )

        elif body.resolution == "mark_not_executed":
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE tool_journal
                    SET resolution = 'operator_marked_not_executed', resolved_at = now()
                    WHERE idempotency_key = $1
                    """,
                    journal_row["idempotency_key"],
                )
                await conn.execute(
                    "UPDATE runs SET status = 'pending', finished_at = NULL WHERE id = $1", run_id
                )

        else:
            assert body.resolution == "retry"
            tool_name = journal_row["tool_name"]
            tool_row = await conn.fetchrow(
                "SELECT safety, has_reconcile_fn FROM tool_registry WHERE name = $1",
                tool_name,
            )
            from anchor.runtime.tools.registry import resolve as resolve_tool
            tool_decl = resolve_tool(tool_name)

            is_unsafe = (tool_row and tool_row["safety"] == "unsafe") or (
                tool_decl is not None and tool_decl.safety == "unsafe"
            )
            has_reconcile = (tool_row and tool_row["has_reconcile_fn"]) or (
                tool_decl is not None and tool_decl.reconcile_fn is not None
            )

            if is_unsafe and not has_reconcile:
                raise ApiError(
                    status_code=400,
                    error="cannot_retry_unsafe_tool",
                    message=(
                        f"Tool '{tool_name}' is declared unsafe with no automatic reconciliation handler. "
                        "Direct retry is unavailable. Please select 'mark_executed' or 'mark_not_executed'."
                    ),
                )
            # Re-consult the tool's declared policy from a clean slate: no
            # tool_journal write here at all.
            async with conn.transaction():
                await conn.execute(
                    "UPDATE runs SET status = 'pending', finished_at = NULL WHERE id = $1", run_id
                )

        row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
        assert row is not None
        return serialize_run(row)
