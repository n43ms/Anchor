"""T156 — a failure in the renewer task cancels the execution task via the
`TaskGroup` rather than leaving an orphaned writer (plan.md P3.4). The
renewer is the fencing detector: once its lease extension is rejected, the
structured-concurrency group tears down the sibling immediately, mid-step
if necessary, rather than waiting for the execution task to notice on its
own.

The epoch mismatch here is induced directly with a raw `UPDATE` rather than
by a second worker's real claim — this test is only exercising the
`TaskGroup` wiring in `anchor.worker.loop.run_claimed`, not the claim
statement itself (which `tests/concurrency/test_reclaim_after_expiry.py`
already covers end to end).
"""

from __future__ import annotations

import asyncio
import json

import asyncpg
import pytest

from anchor.core.config.profiles import ConfigProfile, profile_settings
from anchor.core.determinism.actions import Action, Done, ToolCall
from anchor.core.determinism.context import StepContext
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one
from anchor.core.replay.load import load_run_events
from anchor.runtime.agents.registry import register
from anchor.worker.loop import run_claimed

MAX_PAYLOAD = 1_000_000
TOTAL_STEPS = 20  # 20 * 50ms tool latency ~= 1s of execution to interrupt


def _many_steps_agent(ctx: StepContext) -> Action:
    if ctx.step_index < TOTAL_STEPS:
        return ToolCall("search", {"query": str(ctx.step_index)})
    return Done({"steps": ctx.step_index})


register("test_taskgroup_fencing_agent", _many_steps_agent)


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
        "test_taskgroup_fencing_agent",
        json.dumps({}),
    )
    await append(
        conn,
        run_id=run_id,
        type=EventType.RUN_SUBMITTED,
        payload={
            "agent_type": "test_taskgroup_fencing_agent",
            "input": {},
            "is_demo": True,
            "client_request_key": None,
            "chaos_run_id": None,
        },
        epoch=0,
        worker_id="api",
        max_payload_bytes=MAX_PAYLOAD,
    )
    return run_id


@pytest.mark.asyncio
async def test_renewer_fencing_cancels_execution_task_mid_run(db_pool: asyncpg.Pool) -> None:
    settings = profile_settings(ConfigProfile.DEMO).model_copy(
        update={"renewal_interval_ms": 10, "lease_duration_ms": 4_000}
    )

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        claimed = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=settings.lease_duration_ms,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert claimed is not None

    async def _bump_epoch_mid_run() -> None:
        # Let a few steps complete correctly at the real epoch first, so
        # this exercises "the renewer notices while execution is mid-sleep
        # inside a tool call", not "the very first append after claim is
        # already stale" (which test_taskgroup's sibling scenario would
        # collapse into the execute path detecting its own fencing before
        # the renewer ever gets a tick). Simulates "another worker has
        # already reclaimed this run" without going through the full claim
        # protocol — this test only exercises what happens to *this*
        # worker's TaskGroup once its epoch goes stale mid-run, not the
        # claim statement itself.
        while True:
            await asyncio.sleep(0.01)
            async with db_pool.acquire() as check_conn:
                count = await check_conn.fetchval(
                    "SELECT COUNT(*) FROM run_events WHERE run_id = $1 AND type = 'STEP_COMPLETED'",
                    run_id,
                )
                if count > 0:
                    break
        async with db_pool.acquire() as bump_conn:
            await bump_conn.execute("UPDATE runs SET epoch = epoch + 1 WHERE id = $1", run_id)

    # Must not raise: LeaseFencedError is caught inside run_claimed, logged,
    # and swallowed so the worker returns to its idle poll loop (I3).
    await asyncio.gather(
        run_claimed(db_pool, claimed, worker_id="worker-a#1", settings=settings),
        _bump_epoch_mid_run(),
    )

    async with db_pool.acquire() as conn:
        events = await load_run_events(conn, run_id)
        run_row = await conn.fetchrow("SELECT status FROM runs WHERE id = $1", run_id)

    completed_steps = [e for e in events if e.type == EventType.STEP_COMPLETED]
    run_completed = [e for e in events if e.type == EventType.RUN_COMPLETED]

    assert len(run_completed) == 0, "the fenced worker must never reach the terminal append"
    assert 0 < len(completed_steps) < TOTAL_STEPS, (
        "some steps must have completed correctly before the bump, and execution must have been "
        "cancelled mid-run afterward — before all steps ran"
    )
    assert run_row is not None
    assert run_row["status"] == "running", "the fenced worker changes nothing about run status"
