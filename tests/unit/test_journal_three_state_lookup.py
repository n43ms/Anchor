"""T235 — the three-state lookup (`core.journal.lookup`): a row with a
result -> skip and return; no row -> execute; a row with `result IS NULL`
-> apply policy (FR-042, FR-043).
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.core.journal.keys import derive_key
from anchor.core.journal.lookup import Completed, NeverAttempted, Uncertain, lookup


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type) VALUES ('demo_short') RETURNING id"
    )
    await conn.execute(
        """
        INSERT INTO tool_registry
            (name, safety, naturally_idempotent, provider_accepts_key, has_reconcile_fn,
             default_policy, declaration_hash, declared_by_version)
        VALUES ('web_search', 'retry_safe', true, false, false, 'retry_safe', 'h', 'test')
        ON CONFLICT DO NOTHING
        """
    )
    return run_id


@pytest.mark.asyncio
async def test_no_row_is_never_attempted(db_pool: asyncpg.Pool) -> None:
    key = derive_key(999_999, 0, "web_search", {"query": "never"})
    async with db_pool.acquire() as conn:
        state = await lookup(conn, key)
    assert isinstance(state, NeverAttempted)


@pytest.mark.asyncio
async def test_row_with_result_is_completed(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        key = derive_key(run_id, 0, "web_search", {"query": "x"})
        await conn.execute(
            """
            INSERT INTO tool_journal
                (idempotency_key, run_id, step_index, tool_name, args_canonical, args_hash,
                 intent_epoch, result, result_at, result_epoch)
            VALUES ($1, $2, 0, 'web_search', '{}'::jsonb, 'h', 0, $3::jsonb, now(), 0)
            """,
            key,
            run_id,
            json.dumps({"results": ["a"]}),
        )
        state = await lookup(conn, key)
    assert isinstance(state, Completed)
    assert state.result == {"results": ["a"]}
    assert state.result_epoch == 0


@pytest.mark.asyncio
async def test_row_with_null_result_is_uncertain(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        key = derive_key(run_id, 0, "web_search", {"query": "x"})
        await conn.execute(
            """
            INSERT INTO tool_journal
                (idempotency_key, run_id, step_index, tool_name, args_canonical, args_hash,
                 intent_epoch)
            VALUES ($1, $2, 0, 'web_search', '{}'::jsonb, 'h', 0)
            """,
            key,
            run_id,
        )
        state = await lookup(conn, key)
    assert isinstance(state, Uncertain)
    assert state.tool_name == "web_search"
    assert state.resolution is None
