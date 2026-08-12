"""T112 — a step emits **one** `NONDET_RECORDED` carrying all its entries,
committed in the same transaction as that step's `TOOL_INTENT` (D-47).
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
from anchor.core.replay.load import load_run_events
from anchor.runtime.agents.registry import register
from anchor.worker.loop import claim_one, execute_run


def _two_nondet_calls_then_tool(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        ctx.now()
        ctx.now()
        return ToolCall("search", {"query": "x"})
    return Done({"ok": True})


register("test_nondet_batch_agent", _two_nondet_calls_then_tool)


@pytest.mark.asyncio
async def test_one_nondet_recorded_event_atomic_with_tool_intent(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
            "test_nondet_batch_agent",
            json.dumps({}),
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_SUBMITTED,
            payload={
                "agent_type": "test_nondet_batch_agent",
                "input": {},
                "is_demo": True,
                "client_request_key": None,
                "chaos_run_id": None,
            },
            epoch=0,
            worker_id="api",
            max_payload_bytes=1_000_000,
        )
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        claimed = await claim_one(
            conn, worker_id="worker-a#1", lease_duration_ms=5_000, max_payload_bytes=1_000_000
        )
        assert claimed is not None
        run_id_out, agent_type, input_payload, epoch = claimed

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

        events = await load_run_events(conn, run_id)

    nondet_events = [e for e in events if e.type == EventType.NONDET_RECORDED]
    assert len(nondet_events) == 1, "exactly one NONDET_RECORDED for the whole step"
    assert len(nondet_events[0].payload["entries"]) == 2
    assert [e["call_ordinal"] for e in nondet_events[0].payload["entries"]] == [0, 1]

    tool_intent_events = [e for e in events if e.type == EventType.TOOL_INTENT]
    assert len(tool_intent_events) == 1
    # Committed in the same transaction, immediately before the intent —
    # no other append can land between them (D-47).
    assert nondet_events[0].seq == tool_intent_events[0].seq - 1
