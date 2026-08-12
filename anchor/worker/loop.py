"""The worker's claim-execute loop (plan.md P1.4, extended by P2.4/P2.5).

**Claiming, still interim.** `claim_one` now picks up two kinds of row in
one `SELECT ... FOR UPDATE SKIP LOCKED`: a `pending` run, or a `running` run
whose lease has expired — the second branch is what phase 2's hard gate
needs (a killed worker's run must become claimable by someone else) and it
is genuinely a claim decision made atomically in one transaction (I4), so it
is not a correctness gap. What it is *not yet* is phase 3's `core/leases/claim.py`:
there is no global-concurrency-cap count in this statement, and contention
between many simultaneously-claiming workers is handled by lock-wait order
rather than by the single all-branches CTE Principle II describes. That
statement, with `SKIP LOCKED` doing real work under contention, is P3.1
(T157-T162); this one is scoped to "one worker's poll loop can recover a
run whose owner died," which is all phase 2 requires.

**Replay, now real.** Every claim — including the first — folds the run's
complete log through `core.replay.reconstruct` before any step executes,
and resumes at `last_completed_step_index + 1`, never at 0. A step already
carrying `STEP_COMPLETED` is therefore never re-presented to
`decide_next_step` at all: the loop starts *at* the correct index rather
than iterating past completed ones (P2.5 — this is what makes T110's
not-re-executed property hold without a `STEP_SKIPPED_ON_REPLAY` event
needing to exist yet; that event belongs to phase 5's per-tool dedup on a
*partially* completed step, not to whole-step skip).

Crash behaviour: a crash before the claim transaction commits leaves the
run exactly as it was — `pending`, or `running` under its previous owner
until that lease also expires. A crash mid-run (after claim, before
`RUN_COMPLETED`) leaves the run `running` with an expiring lease, which the
next poll cycle — on this worker or another — reclaims once it expires.
A crash between a tool's execution and its `TOOL_RESULT` is still lost
without dedup until phase 5 (P2.5's stated interim limitation).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import asyncpg

from anchor.core.config.settings import RuntimeSettings
from anchor.core.determinism.actions import Done, ModelCall, ToolCall, require_action
from anchor.core.determinism.context import StepContext
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.replay.load import load_run_events
from anchor.core.replay.reconstruct import reconstruct
from anchor.runtime.agents.registry import resolve
from anchor.runtime.tools.demo import DEMO_TOOLS
from anchor.runtime.tools.model import StubAdapter

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 1.0

# Picks up a `pending` run, or a `running` run whose lease has already
# expired — both branches in one statement so there is no window between
# "check eligibility" and "claim" in which two workers could observe the
# same row as available (I4). `SKIP LOCKED` means a worker mid-transaction
# on a row is invisible to this query rather than a blocking target.
_CLAIM_SQL = """
    SELECT id, agent_type, input, epoch, status, owner_worker_id
    FROM runs
    WHERE status = 'pending'
       OR (status = 'running' AND lease_expires_at < now())
    ORDER BY priority ASC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
"""


async def claim_one(
    conn: asyncpg.Connection[Any], *, worker_id: str, lease_duration_ms: int, max_payload_bytes: int
) -> tuple[int, str, dict[str, Any], int] | None:
    """Claim one eligible run — new or reclaimed — and append `RUN_CLAIMED`
    in the same transaction as the ownership change (I4). Returns
    `(run_id, agent_type, input, epoch)`, or `None` if nothing is eligible.
    """
    async with conn.transaction():
        row = await conn.fetchrow(_CLAIM_SQL)
        if row is None:
            return None

        run_id = row["id"]
        new_epoch = row["epoch"] + 1
        reason = "reclaimed_after_lease_expiry" if row["status"] == "running" else "initial"
        previous_worker_id = row["owner_worker_id"]

        updated = await conn.fetchrow(
            """
            UPDATE runs
            SET status = 'running',
                epoch = $2,
                owner_worker_id = $3,
                lease_expires_at = now() + ($4 || ' milliseconds')::interval,
                claimed_at = now()
            WHERE id = $1
            RETURNING lease_expires_at
            """,
            run_id,
            new_epoch,
            worker_id,
            str(lease_duration_ms),
        )
        assert updated is not None
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_CLAIMED,
            payload={
                "worker_id": worker_id,
                "epoch": new_epoch,
                "reason": reason,
                "lease_expires_at": updated["lease_expires_at"].isoformat(),
                "previous_worker_id": previous_worker_id,
            },
            epoch=new_epoch,
            worker_id=worker_id,
            max_payload_bytes=max_payload_bytes,
        )
        return run_id, row["agent_type"], json.loads(row["input"]), new_epoch


async def execute_run(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    agent_type: str,
    input: dict[str, Any],
    epoch: int,
    worker_id: str,
    settings: RuntimeSettings,
) -> None:
    """Replay the log, then run `decide_next_step` to completion from the
    correct step (P2.4).
    """
    decide_next_step = resolve(agent_type)
    if decide_next_step is None:
        raise ValueError(f"unregistered agent_type: {agent_type}")

    replay_start = time.monotonic()
    events = await load_run_events(conn, run_id)
    run_context = reconstruct(events)
    replay_ms = (time.monotonic() - replay_start) * 1000

    await append(
        conn,
        run_id=run_id,
        type=EventType.REPLAY_COMPLETED,
        payload={
            "steps_replayed": run_context.steps_replayed,
            "replay_ms": replay_ms,
            "last_completed_step_index": run_context.last_completed_step_index,
            "journal_entries_loaded": run_context.journal_entries_loaded,
            "nondet_values_loaded": run_context.nondet_values_loaded,
        },
        epoch=epoch,
        worker_id=worker_id,
        max_payload_bytes=settings.max_event_payload_bytes,
    )

    model_adapter = StubAdapter()
    messages: list[dict[str, Any]] = list(run_context.messages)
    # Resume strictly after the highest completed step — never re-present
    # an already-completed step to decide_next_step (P2.5, T110/T133).
    step_index = run_context.last_completed_step_index + 1
    assert step_index >= 0, "resume index must never be lower than the highest completed step"
    total_start = time.monotonic()

    while True:
        ctx = StepContext(
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            input=input,
            messages=messages,
            attempt=run_context.attempts_by_step.get(step_index, 0) + 1,
            run_context=run_context,
            conn=conn,
            model_adapter=model_adapter,
            tool_registry=DEMO_TOOLS,
            max_payload_bytes=settings.max_event_payload_bytes,
        )
        raw_action = decide_next_step(ctx)
        action = require_action(raw_action)

        if isinstance(action, Done):
            break

        action_kind = "tool" if isinstance(action, ToolCall) else "model"
        await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_STARTED,
            payload={"step_index": step_index, "action_kind": action_kind},
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            max_payload_bytes=settings.max_event_payload_bytes,
        )

        step_start = time.monotonic()
        if isinstance(action, ToolCall):
            # Any buffered non-determinism is flushed inside call_tool,
            # atomically with TOOL_INTENT (D-47) — nothing left to flush
            # here.
            await ctx.call_tool(action.name, action.args)
        elif isinstance(action, ModelCall):
            await ctx.call_model(action.messages, action.model)
        step_duration_ms = (time.monotonic() - step_start) * 1000

        if isinstance(action, ToolCall):
            await append(
                conn,
                run_id=run_id,
                type=EventType.STEP_COMPLETED,
                payload={
                    "step_index": step_index,
                    "duration_ms": step_duration_ms,
                    "action_kind": action_kind,
                },
                epoch=epoch,
                worker_id=worker_id,
                step_index=step_index,
                max_payload_bytes=settings.max_event_payload_bytes,
            )
        else:
            # A model-only step has no side effect to pair the buffer with,
            # so any nondet values it consulted are flushed atomically with
            # STEP_COMPLETED instead of TOOL_INTENT (D-47, T112).
            async with conn.transaction():
                await ctx.flush_pending_nondet()
                await append(
                    conn,
                    run_id=run_id,
                    type=EventType.STEP_COMPLETED,
                    payload={
                        "step_index": step_index,
                        "duration_ms": step_duration_ms,
                        "action_kind": action_kind,
                    },
                    epoch=epoch,
                    worker_id=worker_id,
                    step_index=step_index,
                    max_payload_bytes=settings.max_event_payload_bytes,
                )
        step_index += 1

    total_duration_ms = (time.monotonic() - total_start) * 1000
    async with conn.transaction():
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_COMPLETED,
            payload={
                "output": action.output,
                "total_steps": step_index,
                "total_duration_ms": total_duration_ms,
                "handoff_count": 0,
            },
            epoch=epoch,
            worker_id=worker_id,
            max_payload_bytes=settings.max_event_payload_bytes,
        )
        await conn.execute(
            """
            UPDATE runs
            SET status = 'completed',
                owner_worker_id = NULL,
                lease_expires_at = NULL,
                finished_at = now()
            WHERE id = $1
            """,
            run_id,
        )


async def poll_and_execute_forever(
    pool: asyncpg.Pool, *, worker_id: str, settings: RuntimeSettings
) -> None:
    """Poll for one claimable run at a time and run it to completion.

    Deliberately sequential in phase 1/2 — one worker, one run at a time —
    since the concurrency structure (per-run `TaskGroup`, background
    renewal, many runs in flight) is phase 3's job (P3.4).
    """
    while True:
        async with pool.acquire() as conn:
            claimed = await claim_one(
                conn,
                worker_id=worker_id,
                lease_duration_ms=settings.lease_duration_ms,
                max_payload_bytes=settings.max_event_payload_bytes,
            )
        if claimed is None:
            await asyncio.sleep(POLL_INTERVAL_S)
            continue

        run_id, agent_type, input_payload, epoch = claimed
        logger.info("run claimed", extra={"run_id": run_id, "worker_id": worker_id, "epoch": epoch})
        async with pool.acquire() as conn:
            await execute_run(
                conn,
                run_id=run_id,
                agent_type=agent_type,
                input=input_payload,
                epoch=epoch,
                worker_id=worker_id,
                settings=settings,
            )
