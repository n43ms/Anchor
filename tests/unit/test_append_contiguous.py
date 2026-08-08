"""T063 — seq starts at 1 and increases by exactly 1 across many appends,
with no gaps (FR-024)."""

from __future__ import annotations

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
    )
    return run_id


@pytest.mark.asyncio
async def test_seq_contiguous_from_one(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)

        seqs = []
        for i in range(20):
            seq, _ = await append(
                conn,
                run_id=run_id,
                type=EventType.STEP_STARTED,
                payload={"step_index": i, "action_kind": "tool"},
                epoch=0,
                worker_id="worker-a#1",
                step_index=i,
                max_payload_bytes=1_000_000,
            )
            seqs.append(seq)

        assert seqs == list(range(1, 21))
        last_seq = await conn.fetchval("SELECT last_seq FROM runs WHERE id = $1", run_id)
        assert last_seq == 20
