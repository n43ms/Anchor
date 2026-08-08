"""Shared fixtures: a real PostgreSQL pool and a real Redis client.

No database double is used anywhere in this suite. Every invariant claimed
by the constitution is enforced by PostgreSQL itself, so a mock connection
would test the mock's behaviour rather than the guarantee (research.md D-34).

Both fixtures read their DSNs from the environment so the same test suite
runs unmodified against docker-compose locally and against the `postgres:16`
/ `redis:7` service containers in CI (see .github/workflows/ci.yml).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import asyncpg
import pytest
import redis.asyncio as redis_asyncio

TEST_DATABASE_URL = os.environ.get(
    "ANCHOR_TEST_DATABASE_URL",
    "postgresql://anchor:anchor@localhost:5432/anchor_test",
)
TEST_REDIS_URL = os.environ.get("ANCHOR_TEST_REDIS_URL", "redis://localhost:6379/1")

# Every table that a test might write to, in FK-safe truncation order.
# Kept as an explicit list rather than introspected from the catalog so that
# adding a table is a deliberate one-line change here, matching the
# constitution's "no schema change without raising it first."
_ALL_TABLES = (
    "demo_effects",
    "tool_journal",
    "tool_registry",
    "chaos_events",
    "chaos_reports",
    "chaos_runs",
    "run_events",
    "runs",
    "workers",
    "metrics_rollup",
    "metrics_rollup_watermark",
    "runtime_config",
)


@pytest.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    """A session-scoped connection pool against the real test database."""
    pool = await asyncpg.create_pool(TEST_DATABASE_URL, min_size=1, max_size=10)
    try:
        yield pool
    finally:
        await pool.close()


@pytest.fixture(autouse=True)
async def _truncate_between_tests(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """Truncate every table before each test so tests never depend on order.

    Runs before the test rather than after, so a failed test's data is left
    in place for post-mortem inspection until the next test starts.
    """
    async with db_pool.acquire() as conn:
        existing = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        names = {row["tablename"] for row in existing}
        to_truncate = [t for t in _ALL_TABLES if t in names]
        if to_truncate:
            await conn.execute(
                f"TRUNCATE {', '.join(to_truncate)} RESTART IDENTITY CASCADE"
            )
    yield


@pytest.fixture
async def redis_client() -> AsyncIterator[redis_asyncio.Redis]:
    """A real Redis client against the test database (db 1, not the dev db 0)."""
    client = redis_asyncio.from_url(TEST_REDIS_URL)
    try:
        await client.flushdb()
        yield client
    finally:
        await client.flushdb()
        await client.aclose()
