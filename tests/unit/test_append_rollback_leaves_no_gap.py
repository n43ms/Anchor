"""T064 — a transaction that rolls back after appending leaves `runs.last_seq`
unchanged and no orphaned `seq`. Allocation from the run row (not a
sequence) is what makes this true — a sequence would gap on rollback.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType


@pytest.mark.asyncio
async def test_rollback_leaves_no_gap(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
        )

        seq1, _ = await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_STARTED,
            payload={"step_index": 0, "action_kind": "tool"},
            epoch=0,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=1_000_000,
        )
        assert seq1 == 1

        try:
            async with conn.transaction():
                await append(
                    conn,
                    run_id=run_id,
                    type=EventType.STEP_STARTED,
                    payload={"step_index": 1, "action_kind": "tool"},
                    epoch=0,
                    worker_id="worker-a#1",
                    step_index=1,
                    max_payload_bytes=1_000_000,
                )
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass

        last_seq = await conn.fetchval("SELECT last_seq FROM runs WHERE id = $1", run_id)
        assert last_seq == 1

        seq2, _ = await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_STARTED,
            payload={"step_index": 1, "action_kind": "tool"},
            epoch=0,
            worker_id="worker-a#1",
            step_index=1,
            max_payload_bytes=1_000_000,
        )
        assert seq2 == 2

        rows = await conn.fetch("SELECT seq FROM run_events WHERE run_id = $1 ORDER BY seq", run_id)
        assert [r["seq"] for r in rows] == [1, 2]
