"""`POST /api/runs` and the read endpoints (plan.md P1.3, P1.7)."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Annotated, Any, Literal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from anchor.api.serializers.runs import RUN_COLUMNS, RunResponse, serialize_run
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
        raise HTTPException(status_code=422, detail="malformed cursor") from exc


@router.post("/api/runs", response_model=RunResponse, status_code=201)
async def submit_run(
    submission: RunSubmission,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> RunResponse:
    if not is_registered(submission.agent_type):
        raise HTTPException(status_code=404, detail=f"unknown agent_type: {submission.agent_type}")

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
    status: list[str] | None = None,
    agent_type: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Newest first, keyset-paginated on `(created_at, id)` — never
    offset-based, so a page boundary stays correct while runs are being
    submitted concurrently (contracts/openapi.yaml).
    """
    page_size = min(limit, 200)
    async with pool.acquire() as conn:
        clauses = []
        params: list[Any] = []
        if status:
            params.append(status)
            clauses.append(f"status = ANY(${len(params)})")
        if agent_type:
            params.append(agent_type)
            clauses.append(f"agent_type = ${len(params)}")
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

    items = [
        serialize_run(r, needs_review=needs_review_by_id.get(r["id"])).model_dump() for r in rows
    ]
    next_cursor = (
        _encode_cursor(rows[-1]["created_at"], rows[-1]["id"]) if len(rows) == page_size else None
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: int, pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> RunResponse:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")
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
            raise HTTPException(status_code=404, detail="run not found")
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
            raise HTTPException(status_code=404, detail="run not found")
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


class ResolveRequest(BaseModel):
    resolution: Literal["mark_executed", "mark_not_executed", "retry"]
    note: str | None = None


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
            raise HTTPException(status_code=404, detail="run not found")

        deployment_mode: str = request.app.state.deployment_mode
        if deployment_mode == "demonstration" and not run_row["is_demo"]:
            raise HTTPException(
                status_code=403, detail="only demo runs may be resolved in demonstration mode"
            )
        if run_row["status"] != "needs_review":
            raise HTTPException(status_code=409, detail="run is not in needs_review")

        epoch = run_row["epoch"]
        journal_row = await _open_journal_row(conn, run_id)
        if journal_row is None:
            # Should be unreachable — a needs_review run always halted on
            # exactly one open journal row (halt_needs_review always
            # follows an Uncertain lookup) — but a bare assert here would
            # be an internal-error crash a caller cannot act on, so this
            # names the actual state instead.
            raise HTTPException(
                status_code=409, detail="no open uncertainty window found for this run"
            )

        settings = await load_runtime_settings(conn)

        if body.resolution == "mark_executed":
            operator_result = {"operator_marked_executed": True, "note": body.note}
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
            # Re-consult the tool's declared policy from a clean slate: no
            # tool_journal write here at all. For a tool whose safety is
            # genuinely `unsafe`, the next resumption re-enters this exact
            # halt immediately — expected, since no automatic policy exists
            # for that category; `mark_executed` / `mark_not_executed` are
            # the only ways to clear it.
            async with conn.transaction():
                await conn.execute(
                    "UPDATE runs SET status = 'pending', finished_at = NULL WHERE id = $1", run_id
                )

        row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
        assert row is not None
        return serialize_run(row)
