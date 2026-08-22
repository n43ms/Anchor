"""T483 — an API restart mid-harness marks the chaos run `abandoned`
rather than leaving it `running` with a stale heartbeat (T497). Called at
API startup (`anchor.api.app`'s lifespan).
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.chaos.harness import mark_abandoned_chaos_runs


async def _insert_chaos_run(conn: asyncpg.Connection, *, heartbeat_age_s: float | None) -> int:
    if heartbeat_age_s is None:
        run_id: int = await conn.fetchval(
            """
            INSERT INTO chaos_runs (status, params, deployment_mode, config_profile,
                                     lease_duration_ms, renewal_interval_ms)
            VALUES ('running', '{}'::jsonb, 'local', 'demo', 4000, 1000)
            RETURNING id
            """
        )
    else:
        run_id = await conn.fetchval(
            """
            INSERT INTO chaos_runs (status, params, deployment_mode, config_profile,
                                     lease_duration_ms, renewal_interval_ms, heartbeat_at)
            VALUES ('running', '{}'::jsonb, 'local', 'demo', 4000, 1000,
                     now() - ($1 * interval '1 second'))
            RETURNING id
            """,
            heartbeat_age_s,
        )
    return run_id


@pytest.mark.asyncio
async def test_stale_running_run_is_marked_abandoned(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_chaos_run(conn, heartbeat_age_s=120)
        count = await mark_abandoned_chaos_runs(conn, stale_after_s=60)
        assert count == 1
        status = await conn.fetchval("SELECT status FROM chaos_runs WHERE id = $1", run_id)
        assert status == "abandoned"


@pytest.mark.asyncio
async def test_never_heartbeated_running_run_is_marked_abandoned(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_chaos_run(conn, heartbeat_age_s=None)
        await mark_abandoned_chaos_runs(conn, stale_after_s=60)
        status = await conn.fetchval("SELECT status FROM chaos_runs WHERE id = $1", run_id)
        assert status == "abandoned"


@pytest.mark.asyncio
async def test_fresh_running_run_is_left_alone(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_chaos_run(conn, heartbeat_age_s=1)
        count = await mark_abandoned_chaos_runs(conn, stale_after_s=60)
        assert count == 0
        status = await conn.fetchval("SELECT status FROM chaos_runs WHERE id = $1", run_id)
        assert status == "running"
