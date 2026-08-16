"""T246 — a step containing two side-effecting tool calls is rejected. This
is what makes the idempotency key unique without a within-step counter
(D-26): `idempotency_key = hash(run_id, step_index, action_name, args)` has
no way to distinguish a first and second call within the same step_index.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import pytest

from anchor.core.determinism.context import StepContext
from anchor.core.replay.context import RunContext
from anchor.runtime.tools.registry import ToolDeclaration, register_tool


@pytest.mark.asyncio
async def test_second_tool_call_in_the_same_step_raises(db_pool: asyncpg.Pool) -> None:
    async def _fn(args: dict[str, Any], **_: Any) -> Any:
        return {"ok": True}

    decl = ToolDeclaration(
        name="test_one_effect_tool", fn=_fn, safety="retry_safe", naturally_idempotent=True
    )

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

        ctx = StepContext(
            run_id=run_id,
            epoch=0,
            worker_id="worker-a#1",
            step_index=0,
            input={},
            run_context=RunContext(),
            conn=conn,
            tool_registry={"test_one_effect_tool": decl},
        )

        first = await ctx.call_tool("test_one_effect_tool", {"call": 1})
        assert first == {"ok": True}

        with pytest.raises(RuntimeError, match="second side-effecting tool"):
            await ctx.call_tool("test_one_effect_tool", {"call": 2})

        count = await conn.fetchval("SELECT count(*) FROM tool_journal WHERE run_id = $1", run_id)

    assert count == 1, "the rejected second call must never reach the journal"
