"""T479 — `chaos_events` and `chaos_reports` are immutable in every
deployment mode (FR-083, data-model.md §6/§8, constitution Principle II).

This is published evidence, not application state: unlike `runs`, which
gets a soft-hide `archived_at` column (`005_runs_archived_at.py`), there is
no reset affordance that is even supposed to reach these two tables, so
`UPDATE`/`DELETE` are rejected unconditionally by the same
`BEFORE UPDATE OR DELETE ... RAISE ... AN003` shape `run_events_immutable`
established in migration 001.

Requires a live PostgreSQL with migration 006 applied.
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.core.db import pool as anchor_pool
from anchor.core.db.errors import ImmutableRecordError


async def _insert_chaos_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        """
        INSERT INTO chaos_runs
            (status, params, deployment_mode, config_profile,
             lease_duration_ms, renewal_interval_ms)
        VALUES ('completed', $1::jsonb, 'local', 'demo', 4000, 1000)
        RETURNING id
        """,
        json.dumps({"worker_count": 3, "duration_seconds": 10}),
    )
    return run_id


async def _insert_chaos_event(conn: asyncpg.Connection, chaos_run_id: int) -> int:
    event_id: int = await conn.fetchval(
        """
        INSERT INTO chaos_events (chaos_run_id, type, target_worker_id)
        VALUES ($1, 'worker_kill', 'w-1#1')
        RETURNING id
        """,
        chaos_run_id,
    )
    return event_id


async def _insert_chaos_report(conn: asyncpg.Connection, chaos_run_id: int) -> None:
    await conn.execute(
        """
        INSERT INTO chaos_reports
            (chaos_run_id, inv_no_duplicate_effects, inv_log_monotonic,
             inv_single_writer_per_epoch, inv_terminal_reachability,
             inv_replay_determinism, duplicate_effect_count, stranded_run_count,
             kills_injected, runs_total, steps_total, duration_seconds)
        VALUES ($1, true, true, true, true, true, 0, 0, 0, 5, 20, 10)
        """,
        chaos_run_id,
    )


@pytest.mark.asyncio
async def test_chaos_events_update_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_chaos_run(conn)
        event_id = await _insert_chaos_event(conn, run_id)

    with pytest.raises(ImmutableRecordError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await conn.execute(
                "UPDATE chaos_events SET target_worker_id = 'tampered' WHERE id = $1",
                event_id,
            )
    assert exc_info.value.table == "chaos_events"
    assert exc_info.value.operation == "UPDATE"


@pytest.mark.asyncio
async def test_chaos_events_delete_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_chaos_run(conn)
        event_id = await _insert_chaos_event(conn, run_id)

    with pytest.raises(ImmutableRecordError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await conn.execute("DELETE FROM chaos_events WHERE id = $1", event_id)
    assert exc_info.value.operation == "DELETE"

    async with db_pool.acquire() as conn:
        count = await conn.fetchval("SELECT count(*) FROM chaos_events WHERE id = $1", event_id)
    assert count == 1, "the row must survive the rejected DELETE"


@pytest.mark.asyncio
async def test_chaos_reports_update_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_chaos_run(conn)
        await _insert_chaos_report(conn, run_id)

    with pytest.raises(ImmutableRecordError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await conn.execute(
                "UPDATE chaos_reports SET duplicate_effect_count = 1 WHERE chaos_run_id = $1",
                run_id,
            )
    assert exc_info.value.table == "chaos_reports"
    assert exc_info.value.operation == "UPDATE"


@pytest.mark.asyncio
async def test_chaos_reports_delete_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_chaos_run(conn)
        await _insert_chaos_report(conn, run_id)

    with pytest.raises(ImmutableRecordError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await conn.execute("DELETE FROM chaos_reports WHERE chaos_run_id = $1", run_id)
    assert exc_info.value.operation == "DELETE"

    async with db_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM chaos_reports WHERE chaos_run_id = $1", run_id
        )
    assert count == 1, "the row must survive the rejected DELETE"


@pytest.mark.asyncio
async def test_recovery_percentiles_null_iff_no_kills(db_pool: asyncpg.Pool) -> None:
    """Schema-level half of data-model.md §8: `recovery_ms_p50 IS NULL`
    exactly when `kills_injected = 0` — a recovery figure on a run that
    never lost a worker is not a measurement.
    """
    async with db_pool.acquire() as conn:
        run_id = await _insert_chaos_run(conn)
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                """
                INSERT INTO chaos_reports
                    (chaos_run_id, inv_no_duplicate_effects, inv_log_monotonic,
                     inv_single_writer_per_epoch, inv_terminal_reachability,
                     inv_replay_determinism, duplicate_effect_count, stranded_run_count,
                     kills_injected, runs_total, steps_total, duration_seconds,
                     recovery_ms_p50)
                VALUES ($1, true, true, true, true, true, 0, 0, 0, 5, 20, 10, 100)
                """,
                run_id,
            )
