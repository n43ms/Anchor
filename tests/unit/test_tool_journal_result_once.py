"""T234 — `tool_journal_result_once`: `NULL -> result` is permitted, an
`attempts` increment is permitted, setting `resolution` is permitted, and
overwriting a non-null `result` with a different value raises `AN004`. A
result, once recorded, is final (I1).
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.core.db.errors import ResultOverwriteError
from anchor.core.db.pool import acquire as acquire_translated


async def _insert_run_and_intent(conn: asyncpg.Connection, key: str) -> int:
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
    await conn.execute(
        """
        INSERT INTO tool_journal
            (idempotency_key, run_id, step_index, tool_name, args_canonical, args_hash, intent_epoch)
        VALUES ($1, $2, 0, 'web_search', '{}'::jsonb, 'h', 0)
        """,
        key,
        run_id,
    )
    return run_id


@pytest.mark.asyncio
async def test_null_to_result_is_permitted(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        await _insert_run_and_intent(conn, "key-null-to-result")
        await conn.execute(
            "UPDATE tool_journal SET result = $2::jsonb, result_at = now(), result_epoch = 0 "
            "WHERE idempotency_key = $1",
            "key-null-to-result",
            json.dumps({"ok": True}),
        )
        row = await conn.fetchrow(
            "SELECT result FROM tool_journal WHERE idempotency_key = $1", "key-null-to-result"
        )
        assert row is not None
        assert json.loads(row["result"]) == {"ok": True}


@pytest.mark.asyncio
async def test_attempts_increment_is_permitted(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        await _insert_run_and_intent(conn, "key-attempts")
        await conn.execute(
            "UPDATE tool_journal SET attempts = attempts + 1 WHERE idempotency_key = $1",
            "key-attempts",
        )
        attempts = await conn.fetchval(
            "SELECT attempts FROM tool_journal WHERE idempotency_key = $1", "key-attempts"
        )
        assert attempts == 2


@pytest.mark.asyncio
async def test_setting_resolution_is_permitted(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        await _insert_run_and_intent(conn, "key-resolution")
        await conn.execute(
            "UPDATE tool_journal SET resolution = 'unsafe_halted', resolved_at = now() "
            "WHERE idempotency_key = $1",
            "key-resolution",
        )
        resolution = await conn.fetchval(
            "SELECT resolution FROM tool_journal WHERE idempotency_key = $1", "key-resolution"
        )
        assert resolution == "unsafe_halted"


@pytest.mark.asyncio
async def test_overwriting_a_recorded_result_raises_an004(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        await _insert_run_and_intent(conn, "key-overwrite")
        await conn.execute(
            "UPDATE tool_journal SET result = $2::jsonb, result_at = now(), result_epoch = 0 "
            "WHERE idempotency_key = $1",
            "key-overwrite",
            json.dumps({"first": True}),
        )

    with pytest.raises(ResultOverwriteError) as excinfo:
        async with acquire_translated(db_pool) as conn:
            await conn.execute(
                "UPDATE tool_journal SET result = $2::jsonb WHERE idempotency_key = $1",
                "key-overwrite",
                json.dumps({"second": True}),
            )
    assert excinfo.value.idempotency_key == "key-overwrite"


@pytest.mark.asyncio
async def test_rewriting_the_same_result_value_does_not_raise(db_pool: asyncpg.Pool) -> None:
    """`NEW.result IS DISTINCT FROM OLD.result` is the guard, not a bare
    non-null check — an idempotent re-write of the identical value (e.g. a
    retried UPDATE after a connection blip) must not be treated as a
    violation.
    """
    async with db_pool.acquire() as conn:
        await _insert_run_and_intent(conn, "key-same-value")
        payload = json.dumps({"same": True})
        await conn.execute(
            "UPDATE tool_journal SET result = $2::jsonb, result_at = now(), result_epoch = 0 "
            "WHERE idempotency_key = $1",
            "key-same-value",
            payload,
        )
        # Re-affirming the identical value must not raise.
        await conn.execute(
            "UPDATE tool_journal SET result = $2::jsonb WHERE idempotency_key = $1",
            "key-same-value",
            payload,
        )
