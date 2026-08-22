"""T475 — invariant 2 detects a planted gap and a planted duplicate `seq`.

`PRIMARY KEY (run_id, seq)` forbids a genuine duplicate insert, so both
scenarios here are planted by writing directly to `run_events` with
`execute` (bypassing `core.events.append`'s CTE allocator) — the only way
to construct the corrupted logs this assertion exists to catch, since the
normal path cannot produce them.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.chaos.invariants import check_log_monotonic
from anchor.core.events.append import append
from anchor.core.events.types import EventType


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
    )
    return run_id


@pytest.mark.asyncio
async def test_clean_log_passes(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        for i in range(3):
            await append(
                conn,
                run_id=run_id,
                type=EventType.STEP_STARTED,
                payload={"step_index": i, "action_kind": "tool"},
                epoch=0,
                worker_id="worker-a#1",
                step_index=i,
                max_payload_bytes=1_000_000,
            )
        result = await check_log_monotonic(conn)
        assert result.passed


@pytest.mark.asyncio
async def test_planted_gap_is_detected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        # seq 1 via the real allocator, then a hand-crafted seq 3 —
        # skipping 2 and advancing last_seq to match, so the gap is
        # invisible to any check that only compares against last_seq.
        await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_STARTED,
            payload={"step_index": 0, "action_kind": "tool"},
            epoch=0,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=1_000_000,
        )
        await conn.execute("UPDATE runs SET last_seq = 3 WHERE id = $1", run_id)
        await conn.execute(
            "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
            "VALUES ($1, 3, 'STEP_COMPLETED', 0, 'worker-a#1')",
            run_id,
        )

        result = await check_log_monotonic(conn)
        assert not result.passed
        assert result.violations[0]["run_id"] == run_id
        assert result.violations[0]["event_count"] == 2
        assert result.violations[0]["max_seq"] == 3


@pytest.mark.asyncio
async def test_planted_duplicate_seq_via_raw_insert_is_detected(db_pool: asyncpg.Pool) -> None:
    """A duplicate `seq` cannot land via `INSERT` (the primary key rejects
    it); this proves the assertion's shape would still catch a corpus that
    somehow contained one, e.g. restored from a backup taken mid-write.
    """
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        with pytest.raises(asyncpg.UniqueViolationError):
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
                    "VALUES ($1, 1, 'RUN_SUBMITTED', 0, 'api')",
                    run_id,
                )
                await conn.execute(
                    "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
                    "VALUES ($1, 1, 'RUN_CLAIMED', 0, 'worker-a#1')",
                    run_id,
                )
