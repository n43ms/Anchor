"""T239 — the same three registration rules as table `CHECK` constraints,
so a row inserted by any path other than `register_tool` still satisfies
them (data-model.md §4).
"""

from __future__ import annotations

import asyncpg
import pytest

_INSERT = """
INSERT INTO tool_registry
    (name, safety, naturally_idempotent, provider_accepts_key, has_reconcile_fn,
     default_policy, declaration_hash, declared_by_version)
VALUES ($1, $2, $3, $4, $5, $6, 'h', 'test')
"""


@pytest.mark.asyncio
async def test_invalid_safety_value_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                _INSERT, "bad_check_safety", "not_a_category", True, False, False, "retry_safe"
            )


@pytest.mark.asyncio
async def test_reconcilable_without_has_reconcile_fn_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                _INSERT,
                "bad_check_reconcilable",
                "reconcilable",
                False,
                False,
                False,  # has_reconcile_fn = false
                "reconcilable",
            )


@pytest.mark.asyncio
async def test_retry_safe_without_a_reason_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                _INSERT,
                "bad_check_retry_safe",
                "retry_safe",
                False,  # naturally_idempotent = false
                False,  # provider_accepts_key = false
                False,
                "retry_safe",
            )


@pytest.mark.asyncio
async def test_conflict_columns_move_together(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                """
                INSERT INTO tool_registry
                    (name, safety, naturally_idempotent, provider_accepts_key, has_reconcile_fn,
                     default_policy, declaration_hash, declared_by_version, conflict_at)
                VALUES ('bad_conflict_pair', 'unsafe', false, false, false, 'unsafe', 'h', 'test', now())
                """
            )
