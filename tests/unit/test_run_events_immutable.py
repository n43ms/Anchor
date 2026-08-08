"""T005 — `run_events` is append-only as a database property (I2, FR-022).

Requires a live PostgreSQL with migration 001 applied.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.core.db import pool as anchor_pool
from anchor.core.db.errors import ImmutableRecordError


async def _insert_run_and_event(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
    )
    await conn.execute(
        "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
        "VALUES ($1, 1, 'RUN_SUBMITTED', 0, 'api')",
        run_id,
    )
    return run_id


@pytest.mark.asyncio
async def test_update_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run_and_event(conn)

    with pytest.raises(ImmutableRecordError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await conn.execute(
                "UPDATE run_events SET payload = '{\"tampered\": true}' WHERE run_id = $1",
                run_id,
            )

    assert exc_info.value.table == "run_events"
    assert exc_info.value.operation == "UPDATE"


@pytest.mark.asyncio
async def test_delete_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run_and_event(conn)

    with pytest.raises(ImmutableRecordError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await conn.execute("DELETE FROM run_events WHERE run_id = $1", run_id)

    assert exc_info.value.operation == "DELETE"

    async with db_pool.acquire() as conn:
        count = await conn.fetchval("SELECT count(*) FROM run_events WHERE run_id = $1", run_id)
    assert count == 1, "the row must survive the rejected DELETE"
