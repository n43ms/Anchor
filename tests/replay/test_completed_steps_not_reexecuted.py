"""T110 — a step carrying `STEP_COMPLETED` is not re-executed on the
resuming worker.

Isolated from `test_kill_and_resume` (which proves the same property as
part of the full hard-gate scenario): this test counts `decide_next_step`
invocations per step_index directly, so the assertion does not depend on
any side-effecting tool actually running.
"""

from __future__ import annotations

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
from anchor.worker.loop import execute_run

MAX_PAYLOAD = 1_000_000
_invocations: list[int] = []


def _counting_agent(ctx: StepContext) -> Action:
    _invocations.append(ctx.step_index)
    if ctx.step_index < 2:
        return ToolCall("search", {"query": str(ctx.step_index)})
    return Done({"steps": ctx.step_index})


register("test_step_skip_agent", _counting_agent)


@pytest.mark.asyncio
async def test_resumed_step_is_not_re_presented_to_decide_next_step(db_pool: asyncpg.Pool) -> None:
    _invocations.clear()
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
            "test_step_skip_agent",
            json.dumps({}),
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_SUBMITTED,
            payload={
                "agent_type": "test_step_skip_agent",
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
            lease_duration_ms=5_000,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert claimed is not None
        run_id_out, agent_type, input_payload, epoch = (
            claimed.run_id,
            claimed.agent_type,
            claimed.input,
            claimed.epoch,
        )

        # Hand-craft that step 0 already completed, exactly as a prior
        # (dead) worker would have left it.
        await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_STARTED,
            payload={"step_index": 0, "action_kind": "tool"},
            epoch=epoch,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=MAX_PAYLOAD,
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.TOOL_INTENT,
            payload={
                "step_index": 0,
                "tool_name": "search",
                "args_canonical": {"query": "0"},
                "idempotency_key": "key-0",
                "args_hash": "hash-0",
                "safety": "retry_safe",
            },
            epoch=epoch,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=MAX_PAYLOAD,
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.TOOL_RESULT,
            payload={
                "step_index": 0,
                "tool_name": "search",
                "idempotency_key": "key-0",
                "result": {"results": []},
                "latency_ms": 1.0,
                "resolution": None,
            },
            epoch=epoch,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=MAX_PAYLOAD,
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_COMPLETED,
            payload={"step_index": 0, "duration_ms": 1.0, "action_kind": "tool"},
            epoch=epoch,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=MAX_PAYLOAD,
        )

        settings = profile_settings(ConfigProfile.DEMO)
        await execute_run(
            conn,
            run_id=run_id_out,
            agent_type=agent_type,
            input=input_payload,
            epoch=epoch,
            worker_id="worker-a#1",
            settings=settings,
        )

    assert 0 not in _invocations, "step 0 was already completed and must not be re-presented"
    assert 1 in _invocations
