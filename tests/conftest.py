"""Shared fixtures: a real PostgreSQL pool and a real Redis client.

No database double is used anywhere in this suite. Every invariant claimed
by the constitution is enforced by PostgreSQL itself, so a mock connection
would test the mock's behaviour rather than the guarantee (research.md D-34).

Both fixtures read their DSNs from the environment so the same test suite
runs unmodified against docker-compose locally and against the `postgres:16`
/ `redis:7` service containers in CI (see .github/workflows/ci.yml).

**Reachability is checked, not assumed.** A developer machine without
Docker running has neither service available, and the pure, no-I/O tests
(canonical serialization, config assertion, AST boundary checks, ...)
should still run and pass in that environment. So: a test that explicitly
requests `db_pool` or `redis_client` skips cleanly with a clear reason when
the service is unreachable, and the autouse truncation step degrades to a
no-op rather than failing every test in the suite over a fixture none of
them asked for.
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

CONNECT_TIMEOUT_S = 2.0

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
    "worker_label_incarnations",
    "metrics_rollup",
    "metrics_rollup_watermark",
    "runtime_config",
)


async def _do_truncate_and_reseed(conn: asyncpg.Connection) -> None:
    """Truncate all test tables and re-seed `runtime_config` in one shot.

    Extracted so both the session-start and between-tests fixtures share
    exactly the same logic without duplication.

    The runtime_config re-seed uses `ON CONFLICT DO UPDATE` rather than
    `DO NOTHING` so that if rows survived a partial truncation they are
    always reset to the current profile's defaults.
    """
    import json

    from anchor.core.config.profiles import ConfigProfile, profile_settings

    existing = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    names = {row["tablename"] for row in existing}
    to_truncate = [t for t in _ALL_TABLES if t in names]
    if to_truncate:
        await conn.execute(f"TRUNCATE {', '.join(to_truncate)} RESTART IDENTITY CASCADE")
        if "runtime_config" in to_truncate:
            profile_name = os.environ.get("ANCHOR_CONFIG_PROFILE", "demo")
            settings = profile_settings(ConfigProfile(profile_name))
            for key, value in settings.model_dump(mode="json").items():
                await conn.execute(
                    "INSERT INTO runtime_config (key, value, updated_by) "
                    "VALUES ($1, CAST($2 AS jsonb), 'seed') "
                    "ON CONFLICT (key) DO UPDATE "
                    "SET value = EXCLUDED.value, updated_by = 'seed'",
                    key,
                    json.dumps(value),
                )


@pytest.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    """A session-scoped connection pool against the real test database.

    Skips every test that requests this fixture — directly or via
    `_truncate_between_tests` — with a clear reason, rather than erroring,
    when PostgreSQL is unreachable. A skip is the honest report: these
    tests were not run, as distinct from run-and-failed.
    """
    try:
        pool = await asyncpg.create_pool(
            TEST_DATABASE_URL, min_size=1, max_size=10, timeout=CONNECT_TIMEOUT_S
        )
    except (OSError, asyncpg.PostgresError, TimeoutError) as exc:
        pytest.skip(f"PostgreSQL not reachable at {TEST_DATABASE_URL}: {exc}")
    try:
        yield pool
    finally:
        await pool.close()


@pytest.fixture(scope="session", autouse=True)
async def _truncate_at_session_start() -> AsyncIterator[None]:
    """Truncate all tables ONCE at the very start of the test session.

    This handles leftover state from a previous run that was killed or
    crashed before its own between-tests truncation could complete. Without
    this, re-running pytest on a dirty database causes ordering-dependent
    failures: tests that assume a clean slate (e.g. expecting `run_id = 1`
    from RESTART IDENTITY, or expecting zero `running` rows before inserting
    their own) will fail when old rows are present.

    The function-scoped `_truncate_between_tests` handles isolation between
    individual tests within a single run; this fixture handles isolation
    between runs.

    Like `_truncate_between_tests`, this deliberately does NOT depend on
    `db_pool` so that pure unit tests (no DB needed) are not skipped when
    PostgreSQL is unreachable.
    """
    try:
        conn = await asyncpg.connect(TEST_DATABASE_URL, timeout=CONNECT_TIMEOUT_S)
    except (OSError, asyncpg.PostgresError, TimeoutError):
        yield
        return

    try:
        await _do_truncate_and_reseed(conn)
    finally:
        await conn.close()
    yield


@pytest.fixture(autouse=True)
async def _truncate_between_tests() -> AsyncIterator[None]:
    """Truncate every table before each test so tests never depend on order.

    Runs before the test rather than after, so a failed test's data is left
    in place for post-mortem inspection until the next test starts.

    Deliberately does **not** depend on the `db_pool` fixture: this fixture
    is autouse, so it runs for every test in the suite, including the ones
    that never touch a database at all. If it required `db_pool` directly,
    an unreachable PostgreSQL would skip the entire suite rather than just
    the tests that actually need one. Instead it makes its own short-lived
    connection attempt and degrades to a no-op when that fails — a test
    that genuinely needs the database will still fail or skip on its own
    terms, via its own `db_pool` request.
    """
    try:
        conn = await asyncpg.connect(TEST_DATABASE_URL, timeout=CONNECT_TIMEOUT_S)
    except (OSError, asyncpg.PostgresError, TimeoutError):
        yield
        return

    try:
        await _do_truncate_and_reseed(conn)
    finally:
        await conn.close()
    yield


@pytest.fixture
async def redis_client() -> AsyncIterator[redis_asyncio.Redis]:
    """A real Redis client against the test database (db 1, not the dev db 0).

    Skips, rather than errors, when Redis is unreachable — same reasoning
    as `db_pool`.
    """
    client = redis_asyncio.from_url(TEST_REDIS_URL, socket_connect_timeout=CONNECT_TIMEOUT_S)
    try:
        await client.ping()
    except (OSError, TimeoutError) as exc:
        pytest.skip(f"Redis not reachable at {TEST_REDIS_URL}: {exc}")
    try:
        await client.flushdb()
        yield client
    finally:
        await client.flushdb()
        await client.aclose()
