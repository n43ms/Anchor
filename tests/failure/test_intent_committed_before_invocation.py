"""T245 — no side effect can occur without a preceding **committed**
journaled intent. Simulated here by a tool whose `fn` raises immediately
after being invoked: the intent transaction has already committed by the
time `fn` runs at all (`core.journal.two_phase`'s ordering), so the crash
must still leave a durable `tool_journal` row with `result IS NULL` —
proof that "intent, then invoke" is the actual sequence, not just the
documented one.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import pytest

from anchor.core.determinism.context import StepContext
from anchor.core.journal.keys import derive_key
from anchor.core.replay.context import RunContext
from anchor.runtime.tools.registry import ToolDeclaration, register_tool


class _SimulatedCrash(Exception):
    pass


@pytest.mark.asyncio
async def test_a_crash_during_invocation_leaves_a_committed_intent(db_pool: asyncpg.Pool) -> None:
    async def _boom(args: dict[str, Any], **_: Any) -> Any:
        raise _SimulatedCrash("the process would have died here in a real crash")

    decl = ToolDeclaration(name="test_crashing_tool", fn=_boom, safety="unsafe")

    async with db_pool.acquire() as conn:
        await register_tool(conn, decl, code_version="test")
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, status, owner_worker_id, lease_expires_at) "
            "VALUES ('demo_short', 'running', 'worker-a#1', now() + interval '1 minute') "
            "RETURNING id"
        )
        args = {"x": 1}
        key = derive_key(run_id, 0, decl.name, args)

        ctx = StepContext(
            run_id=run_id,
            epoch=0,
            worker_id="worker-a#1",
            step_index=0,
            input={},
            step_timeout_ms=5000,
            run_context=RunContext(),
            conn=conn,
            tool_registry={"test_crashing_tool": decl},
        )

        with pytest.raises(_SimulatedCrash):
            await ctx.call_tool("test_crashing_tool", args)

        row = await conn.fetchrow(
            "SELECT result, intent_epoch FROM tool_journal WHERE idempotency_key = $1", key
        )

    assert row is not None, "the intent must be durable even though invocation crashed"
    assert row["result"] is None, "no result can exist for a call whose invocation never returned"
    assert row["intent_epoch"] == 0
