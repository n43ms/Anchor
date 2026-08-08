"""T065 — a hand-crafted duplicate (run_id, seq) is rejected by the primary
key loudly, never silently overwritten."""

from __future__ import annotations

import asyncpg
import pytest


@pytest.mark.asyncio
async def test_duplicate_seq_rejected_by_primary_key(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
        )
        await conn.execute(
            "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
            "VALUES ($1, 1, 'RUN_SUBMITTED', 0, 'api')",
            run_id,
        )

        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                "INSERT INTO run_events (run_id, seq, type, epoch, worker_id) "
                "VALUES ($1, 1, 'RUN_SUBMITTED', 0, 'api')",
                run_id,
            )
