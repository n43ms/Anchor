"""`GET /api/runs/{id}/timeline` (plan.md P6.9, T346-T349;
contracts/openapi.yaml `RunTimeline`, contracts/component-contract.md).

Every figure in `RunSummary` that this module's docstring or D-30/D-49
name as a *correctness* read — `duplicate_side_effects` above all — is
computed here, live, straight from `run_events`/`tool_journal`/
`demo_effects`, every call, never from `metrics_rollup` (T349, T356). This
endpoint is deliberately *not* on the rollup's fast path: a timeline is
requested once per page view, not once per dashboard poll tick, so there
is no throughput argument for caching it, and every argument against
caching a number whose entire purpose is to be trusted.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import asyncpg
from pydantic import BaseModel


class TimelineStep(BaseModel):
    step_index: int
    name: str
    status: str
    action_kind: str
    started_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    attempt: int = 1
    idempotency_key: str | None = None
    executed: bool = True


class TimelineSegment(BaseModel):
    worker_id: str
    epoch: int
    claim_reason: str
    started_at: str
    ended_at: str | None
    steps: list[TimelineStep]


class FencingMarker(BaseModel):
    at: str
    fenced_worker_id: str
    stale_epoch: int
    current_epoch: int


class NeedsReviewSummary(BaseModel):
    step_index: int
    tool_name: str
    idempotency_key: str
    declared_policy: str | None
    available_resolutions: list[str]


class RunSummary(BaseModel):
    duplicate_side_effects: int
    handoff_count: int
    recovery_seconds: float | None = None
    effects_executed: int = 0
    replayed_step_count: int = 0


class RunTimeline(BaseModel):
    id: int
    display_id: str
    agent_type: str
    status: str
    started_at: str
    step_count: int
    orphaned: bool
    lease_expires_at: str | None
    segments: list[TimelineSegment]
    fencing_events: list[FencingMarker]
    needs_review: NeedsReviewSummary | None
    summary: RunSummary


async def _load_events(conn: asyncpg.Connection[Any], run_id: int) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT seq, type, payload, epoch, worker_id, step_index, created_at
        FROM run_events
        WHERE run_id = $1
        ORDER BY seq ASC
        """,
        run_id,
    )
    return [
        {
            "seq": r["seq"],
            "type": r["type"],
            "payload": json.loads(r["payload"]),
            "epoch": r["epoch"],
            "worker_id": r["worker_id"],
            "step_index": r["step_index"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


async def build_run_timeline(conn: asyncpg.Connection[Any], run_id: int) -> RunTimeline | None:
    run_row = await conn.fetchrow(
        """
        SELECT id, agent_type, status, created_at, finished_at, lease_expires_at,
               (status = 'running' AND lease_expires_at < now()) AS orphaned
        FROM runs
        WHERE id = $1
        """,
        run_id,
    )
    if run_row is None:
        return None

    events = await _load_events(conn, run_id)

    claims = [e for e in events if e["type"] == "RUN_CLAIMED"]
    fencings = [e for e in events if e["type"] == "WORKER_FENCED"]
    tool_intents_by_step = {
        e["step_index"]: e["payload"]["tool_name"] for e in events if e["type"] == "TOOL_INTENT"
    }
    intent_key_by_step = {
        e["step_index"]: e["payload"]["idempotency_key"]
        for e in events
        if e["type"] == "TOOL_INTENT"
    }
    skipped_by_step = {e["step_index"]: e for e in events if e["type"] == "STEP_SKIPPED_ON_REPLAY"}
    failed_by_step: dict[int, list[dict[str, Any]]] = {}
    for e in events:
        if e["type"] == "STEP_FAILED":
            failed_by_step.setdefault(e["step_index"], []).append(e)

    segments: list[TimelineSegment] = []
    for i, claim in enumerate(claims):
        segment_epoch = claim["epoch"]
        started_at = claim["created_at"]
        if i + 1 < len(claims):
            ended_at: Any = claims[i + 1]["created_at"]
        elif run_row["status"] in ("completed", "failed", "cancelled", "needs_review"):
            ended_at = run_row["finished_at"]
        else:
            ended_at = None

        steps: list[TimelineStep] = []
        started_by_step: dict[int, dict[str, Any]] = {}
        completed_by_step: dict[int, dict[str, Any]] = {}
        for e in events:
            if e["epoch"] != segment_epoch or e["step_index"] is None:
                continue
            if e["type"] == "STEP_STARTED":
                started_by_step[e["step_index"]] = e
            elif e["type"] == "STEP_COMPLETED":
                completed_by_step[e["step_index"]] = e

        for step_index, started_event in sorted(started_by_step.items()):
            action_kind = started_event["payload"]["action_kind"]
            completed_event = completed_by_step.get(step_index)
            skipped = skipped_by_step.get(step_index)
            failures = failed_by_step.get(step_index, [])
            name = tool_intents_by_step.get(step_index, action_kind)

            if skipped is not None:
                status = "skipped_on_replay"
            elif completed_event is not None:
                status = "done"
            elif failures:
                status = "failed"
            else:
                status = "active"

            steps.append(
                TimelineStep(
                    step_index=step_index,
                    name=name,
                    status=status,
                    action_kind=action_kind,
                    started_at=started_event["created_at"].isoformat(),
                    completed_at=completed_event["created_at"].isoformat()
                    if completed_event
                    else None,
                    duration_ms=int(completed_event["payload"]["duration_ms"])
                    if completed_event
                    else None,
                    attempt=len(failures) + 1,
                    idempotency_key=intent_key_by_step.get(step_index),
                    executed=skipped is None,
                )
            )

        segments.append(
            TimelineSegment(
                worker_id=claim["worker_id"],
                epoch=segment_epoch,
                claim_reason=claim["payload"]["reason"],
                started_at=started_at.isoformat(),
                ended_at=ended_at.isoformat() if ended_at else None,
                steps=steps,
            )
        )

    fencing_events = [
        FencingMarker(
            at=e["created_at"].isoformat(),
            fenced_worker_id=e["payload"]["fenced_worker_id"],
            stale_epoch=e["payload"]["stale_epoch"],
            current_epoch=e["payload"]["current_epoch"],
        )
        for e in fencings
    ]

    needs_review: NeedsReviewSummary | None = None
    if run_row["status"] == "needs_review":
        review_events = [e for e in events if e["type"] == "RUN_NEEDS_REVIEW"]
        if review_events:
            last = review_events[-1]
            policy_row = await conn.fetchrow(
                "SELECT safety FROM tool_registry WHERE name = $1", last["payload"]["tool_name"]
            )
            needs_review = NeedsReviewSummary(
                step_index=last["payload"]["step_index"],
                tool_name=last["payload"]["tool_name"],
                idempotency_key=last["payload"]["idempotency_key"],
                declared_policy=policy_row["safety"] if policy_row else None,
                available_resolutions=last["payload"]["available_resolutions"],
            )

    # --- Correctness reads: live, every call, never from metrics_rollup
    # (D-30/D-49/T349/T356). ---

    # A prevented re-execution: a second physical attempt at a step whose
    # result the two-phase journal had already recorded, caught by the
    # three-state lookup and skipped rather than re-run (core.journal.two_phase).
    # This is what "duplicate side effects" measures on a system that, by
    # construction, never lets one actually reach demo_effects twice.
    duplicate_side_effects = await conn.fetchval(
        "SELECT count(*) FROM run_events WHERE run_id = $1 AND type = 'STEP_SKIPPED_ON_REPLAY'",
        run_id,
    )
    effects_executed = await conn.fetchval(
        "SELECT count(*) FROM demo_effects WHERE run_id = $1", run_id
    )
    replayed_step_count = await conn.fetchval(
        """
        SELECT coalesce(sum((payload->>'steps_replayed')::int), 0)
        FROM run_events
        WHERE run_id = $1 AND type = 'REPLAY_COMPLETED'
        """,
        run_id,
    )

    handoff_count = max(0, len(claims) - 1)
    recovery_seconds: float | None = None
    if handoff_count > 0:
        total_recovery_s = 0.0
        for i in range(1, len(claims)):
            previous_lease_expires_at = claims[i - 1]["payload"]["lease_expires_at"]
            previous_expiry = datetime.fromisoformat(previous_lease_expires_at)
            gap = (claims[i]["created_at"] - previous_expiry).total_seconds()
            total_recovery_s += max(0.0, gap)
        recovery_seconds = total_recovery_s

    terminal_event = next(
        (e for e in reversed(events) if e["type"] in ("RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELLED")),
        None,
    )
    derived_status = run_row["status"]
    if terminal_event:
        if terminal_event["type"] == "RUN_COMPLETED":
            derived_status = "completed"
        elif terminal_event["type"] == "RUN_FAILED":
            derived_status = "failed"
        elif terminal_event["type"] == "RUN_CANCELLED":
            derived_status = "cancelled"

    step_count = len({e["step_index"] for e in events if e["step_index"] is not None})

    return RunTimeline(
        id=run_row["id"],
        display_id=f"r{run_row['id']}",
        agent_type=run_row["agent_type"],
        status=derived_status,
        started_at=run_row["created_at"].isoformat(),
        step_count=step_count,
        orphaned=run_row["orphaned"],
        lease_expires_at=run_row["lease_expires_at"].isoformat()
        if run_row["lease_expires_at"]
        else None,
        segments=segments,
        fencing_events=fencing_events,
        needs_review=needs_review,
        summary=RunSummary(
            duplicate_side_effects=int(duplicate_side_effects),
            handoff_count=handoff_count,
            recovery_seconds=recovery_seconds,
            effects_executed=int(effects_executed),
            replayed_step_count=int(replayed_step_count),
        ),
    )
