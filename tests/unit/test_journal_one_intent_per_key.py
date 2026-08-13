"""T233 — `tool_journal`'s primary key rejects a second intent row for the
same idempotency key (FR-041): "exactly one intent row per key" is a
database property, not an application convention.
"""

from __future__ import annotations

import json

import asyncpg
import pytest


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type) VALUES ('demo_short') RETURNING id"
    )
    return run_id


async def _insert_tool(conn: asyncpg.Connection, name: str = "web_search") -> None:
    await conn.execute(
        """
        INSERT INTO tool_registry
            (name, safety, naturally_idempotent, provider_accepts_key, has_reconcile_fn,
             default_policy, declaration_hash, declared_by_version)
        VALUES ($1, 'retry_safe', true, false, false, 'retry_safe', 'testhash', 'test')
        ON CONFLICT DO NOTHING
        """,
        name,
    )


@pytest.mark.asyncio
async def test_second_intent_for_same_key_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await _insert_tool(conn)

        insert_sql = """
            INSERT INTO tool_journal
                (idempotency_key, run_id, step_index, tool_name, args_canonical,
                 args_hash, intent_epoch)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
        """
        await conn.execute(
            insert_sql, "key-1", run_id, 0, "web_search", json.dumps({"query": "x"}), "argshash", 0
        )

        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                insert_sql,
                "key-1",
                run_id,
                0,
                "web_search",
                json.dumps({"query": "different args, same key"}),
                "argshash2",
                0,
            )
