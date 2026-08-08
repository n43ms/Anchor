"""T009 — worker self-registration (FR-065).

Requires a live PostgreSQL with migration 001 applied.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.worker.registry.register import register


@pytest.mark.asyncio
async def test_registration_claims_the_first_free_label_at_incarnation_one(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        registered = await register(
            conn,
            label_pool=["test-a", "test-b", "test-c"],
            capacity=10,
            code_version="abc123",
        )

    assert registered.identity.label == "test-a"
    assert registered.identity.incarnation == 1
    assert registered.identity.id == "test-a#1"

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM workers WHERE id = $1", registered.identity.id)

    assert row is not None
    assert row["capacity"] == 10
    assert row["code_version"] == "abc123"
    assert row["stopped_at"] is None


@pytest.mark.asyncio
async def test_registration_skips_a_label_already_held_by_a_live_worker(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        first = await register(
            conn, label_pool=["test-a", "test-b"], capacity=10, code_version="v1"
        )
        second = await register(
            conn, label_pool=["test-a", "test-b"], capacity=10, code_version="v1"
        )

    assert first.identity.label == "test-a"
    assert second.identity.label == "test-b"


@pytest.mark.asyncio
async def test_registration_raises_when_every_label_is_held(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        await register(conn, label_pool=["only-slot"], capacity=10, code_version="v1")

        with pytest.raises(RuntimeError, match="no free fleet-slot label"):
            await register(conn, label_pool=["only-slot"], capacity=10, code_version="v1")
