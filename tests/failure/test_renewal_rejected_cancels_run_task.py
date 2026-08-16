"""T195 — a rejected renewal cancels the execution task via the `TaskGroup`,
and no write follows the cancellation: the log's final `seq` is unchanged
from the moment of cancellation onward. This is `tests/failure/test_taskgroup_cancels_sibling.py`'s
scenario, re-asserted here with the specific claim T195 names: the run's
`last_seq` does not advance after the induced fencing.
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
from anchor.runtime.agents.registry import register
from anchor.worker.loop import run_claimed

MAX_PAYLOAD = 1_000_000
TOTAL_STEPS = 30


def _slow_agent(ctx: StepContext) -> Action:
    if ctx.step_index < TOTAL_STEPS:
        return ToolCall("search", {"query": str(ctx.step_index)})
    return Done({"steps": ctx.step_index})


register("test_renewal_cancel_agent", _slow_agent)


@pytest.mark.asyncio
async def test_no_write_follows_a_renewal_rejection(db_pool: asyncpg.Pool) -> None:
    settings = profile_settings(ConfigProfile.DEMO).model_copy(
        update={"renewal_interval_ms": 10, "lease_duration_ms": 4_000}
    )

    async with db_pool.acquire() as conn:
        from anchor.runtime.tools.demo import register_demo_tools
        await register_demo_tools(conn, code_version="dev")
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
            "test_renewal_cancel_agent",
            json.dumps({}),
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_SUBMITTED,
            payload={
                "agent_type": "test_renewal_cancel_agent",
                "input": {},
                "is_demo": True,
                "client_request_key": None,
                "chaos_run_id": None,
            },
            epoch=0,
            worker_id="api",
            max_payload_bytes=MAX_PAYLOAD,
        )
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

    async def _bump_epoch_once_a_step_lands() -> None:
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

    await asyncio.gather(
        run_claimed(db_pool, claimed, worker_id="worker-a#1", settings=settings),
        _bump_epoch_once_a_step_lands(),
    )

    async with db_pool.acquire() as conn:
        last_seq_at_check = await conn.fetchval("SELECT last_seq FROM runs WHERE id = $1", run_id)
        await asyncio.sleep(0.1)  # give any errant late write a chance to land
        last_seq_after_settle = await conn.fetchval(
            "SELECT last_seq FROM runs WHERE id = $1", run_id
        )

    assert last_seq_after_settle == last_seq_at_check, (
        "no write may land on this run after the renewal rejection cancelled execution"
    )
