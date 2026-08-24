"""T476 — invariant 3 detects a planted `(run_id, epoch)` carrying events
from two worker ids. The epoch write-gate trigger prevents a *stale*
epoch from writing at all; it does not prevent two rows at the *same*
epoch from naming different workers, which is the complementary property
this assertion checks. Planted via raw `INSERT`, since no real code path
produces it.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.chaos.invariants import check_single_writer_per_epoch


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
    )
    return run_id


@pytest.mark.asyncio
async def test_clean_log_passes(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
            "VALUES ($1, 1, 'RUN_SUBMITTED', 0, 'api')",
            run_id,
        )
        await conn.execute("UPDATE runs SET epoch = 1 WHERE id = $1", run_id)
        await conn.execute(
            "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
            "VALUES ($1, 2, 'RUN_CLAIMED', 1, 'worker-a#1')",
            run_id,
        )
        result = await check_single_writer_per_epoch(conn)
        assert result.passed


@pytest.mark.asyncio
async def test_planted_dual_writer_is_detected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute("UPDATE runs SET epoch = 1 WHERE id = $1", run_id)
        await conn.execute(
            "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
            "VALUES ($1, 1, 'STEP_STARTED', 1, 'worker-a#1')",
            run_id,
        )
        await conn.execute(
            "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
            "VALUES ($1, 2, 'STEP_STARTED', 1, 'worker-b#1')",
            run_id,
        )
        result = await check_single_writer_per_epoch(conn)
        assert not result.passed
        assert result.violations[0]["run_id"] == run_id
        assert result.violations[0]["epoch"] == 1
        assert result.violations[0]["distinct_writers"] == 2
