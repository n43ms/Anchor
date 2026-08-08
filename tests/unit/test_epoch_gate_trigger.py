"""T004 — the epoch write gate (I3, FR-017).

Requires a live PostgreSQL with migration 001 applied. Skips cleanly
(via the `db_pool` fixture) when one isn't reachable — see tests/conftest.py.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.core.db import pool as anchor_pool
from anchor.core.db.errors import LeaseFencedError


async def _insert_run(conn: asyncpg.Connection, *, epoch: int = 0) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, epoch) VALUES ('demo_minimal', $1) RETURNING id",
        epoch,
    )
    return run_id


async def _insert_event(conn: asyncpg.Connection, *, run_id: int, epoch: int, seq: int) -> None:
    await conn.execute(
        """
        INSERT INTO run_events (run_id, seq, type, epoch, worker_id)
        VALUES ($1, $2, 'RUN_SUBMITTED', $3, 'test-worker#1')
        """,
        run_id,
        seq,
        epoch,
    )


@pytest.mark.asyncio
async def test_insert_at_the_current_epoch_succeeds(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn, epoch=3)
        await _insert_event(conn, run_id=run_id, epoch=3, seq=1)

        row = await conn.fetchrow("SELECT * FROM run_events WHERE run_id = $1", run_id)
        assert row["epoch"] == 3


@pytest.mark.asyncio
async def test_insert_below_the_current_epoch_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn, epoch=5)

    with pytest.raises(LeaseFencedError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await _insert_event(conn, run_id=run_id, epoch=3, seq=1)

    assert exc_info.value.run_id == run_id
    assert exc_info.value.stale_epoch == 3
    assert exc_info.value.current_epoch == 5


@pytest.mark.asyncio
async def test_insert_above_the_current_epoch_is_also_rejected(db_pool: asyncpg.Pool) -> None:
    """A writer inventing an epoch higher than the run's current one is
    exactly as wrong as a stale writer — both claim an epoch they did not
    win — so the gate rejects both directions, not just staleness.
    """
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn, epoch=2)

    with pytest.raises(LeaseFencedError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await _insert_event(conn, run_id=run_id, epoch=99, seq=1)

    assert exc_info.value.stale_epoch == 99
    assert exc_info.value.current_epoch == 2


@pytest.mark.asyncio
async def test_a_rejected_insert_leaves_no_partial_write(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn, epoch=5)

    with pytest.raises(LeaseFencedError):
        async with anchor_pool.acquire(db_pool) as conn:
            await _insert_event(conn, run_id=run_id, epoch=3, seq=1)

    async with db_pool.acquire() as conn:
        count = await conn.fetchval("SELECT count(*) FROM run_events WHERE run_id = $1", run_id)
    assert count == 0
