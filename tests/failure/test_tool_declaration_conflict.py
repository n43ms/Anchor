"""T240-T241 — two code versions registering one tool with different safety
fields makes that tool, and only that tool, unexecutable fleet-wide, with
both dissenting versions recorded (D-46, FR-131); and the uncertainty
window is never resolved from an ambiguous declaration — the run halts
instead.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import pytest

from anchor.core.journal.keys import derive_key
from anchor.core.journal.policies import NeedsReviewHalted
from anchor.core.journal.two_phase import execute_tool_call
from anchor.runtime.tools import registry as registry_module
from anchor.runtime.tools.registry import ToolDeclaration, register_tool

MAX_PAYLOAD = 1_000_000


async def _noop_flush() -> None:
    return None


@pytest.mark.asyncio
async def test_conflicting_declarations_mark_only_that_tool_refused(db_pool: asyncpg.Pool) -> None:
    async def _fn(args: dict[str, Any], **_: Any) -> Any:
        return {}

    registry_module._REGISTRY.pop("conflicted_tool", None)  # test isolation across runs

    v1 = ToolDeclaration(name="conflicted_tool", fn=_fn, safety="unsafe")
    v2 = ToolDeclaration(
        name="conflicted_tool", fn=_fn, safety="retry_safe", naturally_idempotent=True
    )
    other = ToolDeclaration(name="unrelated_tool", fn=_fn, safety="unsafe")

    async with db_pool.acquire() as conn:
        conflicted_first = await register_tool(conn, v1, code_version="build-1")
        conflicted_second = await register_tool(conn, v2, code_version="build-2")
        await register_tool(conn, other, code_version="build-1")

        row = await conn.fetchrow(
            "SELECT conflict_at, conflict_version, declared_by_version FROM tool_registry "
            "WHERE name = 'conflicted_tool'"
        )
        unrelated_row = await conn.fetchrow(
            "SELECT conflict_at FROM tool_registry WHERE name = 'unrelated_tool'"
        )

    assert conflicted_first is False, "the first registration is never conflicted with itself"
    assert conflicted_second is True
    assert row is not None
    assert row["conflict_at"] is not None
    assert row["conflict_version"] == "build-2"
    assert unrelated_row is not None
    assert unrelated_row["conflict_at"] is None, "an unrelated tool must not be affected"


@pytest.mark.asyncio
async def test_conflicted_tool_halts_rather_than_resolving_the_uncertainty_window(
    db_pool: asyncpg.Pool,
) -> None:
    async def _fn(args: dict[str, Any], **_: Any) -> Any:
        raise AssertionError("a conflicted tool must never execute")

    registry_module._REGISTRY.pop("conflicted_tool_2", None)

    v1 = ToolDeclaration(
        name="conflicted_tool_2", fn=_fn, safety="retry_safe", naturally_idempotent=True
    )
    v2 = ToolDeclaration(name="conflicted_tool_2", fn=_fn, safety="unsafe")

    async with db_pool.acquire() as conn:
        await register_tool(conn, v1, code_version="build-1")
        await register_tool(conn, v2, code_version="build-2")

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
        key = derive_key(run_id, 0, v2.name, args)

        with pytest.raises(NeedsReviewHalted):
            await execute_tool_call(
                conn,
                run_id=run_id,
                epoch=0,
                worker_id="worker-a#1",
                step_index=0,
                tool=v2,
                args=args,
                flush_pending_nondet=_noop_flush,
                max_payload_bytes=MAX_PAYLOAD,
            )

        run_row = await conn.fetchrow("SELECT status FROM runs WHERE id = $1", run_id)
        journal_row = await conn.fetchrow(
            "SELECT * FROM tool_journal WHERE idempotency_key = $1", key
        )

    assert run_row is not None
    assert run_row["status"] == "needs_review"
    assert journal_row is None, (
        "a conflicted tool must be refused before any intent is ever recorded for it — "
        "there is nothing to resolve, ambiguously or otherwise"
    )
