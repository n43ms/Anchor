"""T113 — no interleaving exists in which a `TOOL_INTENT` exists whose
`ctx.new_id()`-derived key inputs are unrecorded.

`ctx.new_id()` is buffered and flushed atomically with `TOOL_INTENT` inside
one database transaction (D-47) — this is a structural guarantee (both
appends are one statement group; PostgreSQL either commits both or neither),
not one a black-box test can prove by injecting a crash mid-transaction.
What this test proves at this level: the generated id that reaches the
tool's arguments is exactly the value recorded in `NONDET_RECORDED`, and
that record is never separated from its `TOOL_INTENT` by another event —
the observable consequence of the atomicity, which the chaos harness
(phase 8) proves under actual injected crashes.
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
from anchor.core.replay.load import load_run_events
from anchor.runtime.agents.registry import register
from anchor.worker.loop import execute_run


def _new_id_feeds_tool_args(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        generated_id = ctx.new_id()
        return ToolCall("notify", {"recipient": f"user-{generated_id}@example.com"})
    return Done({"ok": True})


register("test_new_id_atomicity_agent", _new_id_feeds_tool_args)


@pytest.mark.asyncio
async def test_new_id_value_is_recorded_atomically_with_its_tool_intent(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        from anchor.runtime.tools.demo import register_demo_tools

        await register_demo_tools(conn, code_version="dev")
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
            "test_new_id_atomicity_agent",
            json.dumps({}),
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_SUBMITTED,
            payload={
                "agent_type": "test_new_id_atomicity_agent",
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
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=5_000,
            global_concurrency_cap=50,
            max_payload_bytes=1_000_000,
        )
        assert claimed is not None
        run_id_out, agent_type, input_payload, epoch = (
            claimed.run_id,
            claimed.agent_type,
            claimed.input,
            claimed.epoch,
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

        events = await load_run_events(conn, run_id)

    nondet_events = [e for e in events if e.type == EventType.NONDET_RECORDED]
    intent_events = [e for e in events if e.type == EventType.TOOL_INTENT]
    assert len(nondet_events) == 1
    assert len(intent_events) == 1

    generated_id = nondet_events[0].payload["entries"][0]["value"]
    assert nondet_events[0].payload["entries"][0]["kind"] == "id"
    assert (
        intent_events[0].payload["args_canonical"]["recipient"]
        == f"user-{generated_id}@example.com"
    )

    # No event of any kind lands between the record of the id and the
    # intent it authorizes — the two are adjacent in the log.
    assert nondet_events[0].seq == intent_events[0].seq - 1
