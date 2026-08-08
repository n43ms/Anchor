"""The worker's claim-execute loop (plan.md P1.4).

Phase 1 scope only. The claim below is **deliberately naive** — a plain
`SELECT ... FOR UPDATE` over one `pending` run, not the `SKIP LOCKED`
epoch-incrementing statement of phase 3 (P3.1). Concurrent workers would
serialize on this `SELECT`'s lock rather than skip past it, which is
acceptable for now and stated rather than assumed.

Crash behaviour: a crash before the claim transaction commits leaves the
run `pending`, untouched. A crash mid-run (after claim, before
`RUN_COMPLETED`) leaves the run `running` with a lease that will expire —
and, in phase 1, nothing reclaims it. That is the honest interim state
phase 2 (replay) and phase 3 (reclaim) exist to fix.
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
from anchor.runtime.agents.registry import resolve
from anchor.runtime.tools.demo import DEMO_TOOLS
from anchor.runtime.tools.model import StubAdapter

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 1.0

_CLAIM_SQL = """
    SELECT id, agent_type, input, epoch
    FROM runs
    WHERE status = 'pending'
    ORDER BY priority ASC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
"""


async def claim_one(
    conn: asyncpg.Connection[Any], *, worker_id: str, lease_duration_ms: int, max_payload_bytes: int
) -> tuple[int, str, dict[str, Any], int] | None:
    """Claim one `pending` run: the naive branch only — no reclaim of
    expired leases yet (that is phase 3's job). Returns
    `(run_id, agent_type, input, epoch)`, or `None` if nothing is pending.
    """
    async with conn.transaction():
        row = await conn.fetchrow(_CLAIM_SQL)
        if row is None:
            return None

        run_id = row["id"]
        new_epoch = row["epoch"] + 1
        await conn.execute(
            """
            UPDATE runs
            SET status = 'running',
                epoch = $2,
                owner_worker_id = $3,
                lease_expires_at = now() + ($4 || ' milliseconds')::interval,
                claimed_at = now()
            WHERE id = $1
            """,
            run_id,
            new_epoch,
            worker_id,
            lease_duration_ms,
        )
        lease_expires_at = await conn.fetchval(
            "SELECT lease_expires_at FROM runs WHERE id = $1", run_id
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_CLAIMED,
            payload={
                "worker_id": worker_id,
                "epoch": new_epoch,
                "reason": "initial",
                "lease_expires_at": lease_expires_at.isoformat(),
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
    """Run `decide_next_step` to completion, one step at a time.

    Each event append is its own statement on an autocommit connection, so
    `TOOL_INTENT` genuinely commits before the tool it names is invoked —
    the two-phase *ordering* plan.md P1.5 establishes even though nothing
    can dedupe on it until phase 5.
    """
    decide_next_step = resolve(agent_type)
    if decide_next_step is None:
        raise ValueError(f"unregistered agent_type: {agent_type}")

    model_adapter = StubAdapter()
    messages: list[dict[str, Any]] = []
    step_index = 0
    total_start = time.monotonic()

    while True:
        ctx = StepContext(
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            input=input,
            messages=messages,
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
            await ctx.call_tool(action.name, action.args)
        elif isinstance(action, ModelCall):
            await ctx.call_model(action.messages, action.model)
        step_duration_ms = (time.monotonic() - step_start) * 1000

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

    Deliberately sequential in phase 1 — one worker, one run at a time —
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
