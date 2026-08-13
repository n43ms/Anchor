"""T223 — under deliberate racing, a duplicate `(run_id, seq)` is rejected
by the primary key rather than silently overwriting. Bypasses
`core.events.append` on purpose (two raw, concurrent inserts claiming the
same `seq`) to prove the backstop constraint itself, independent of whether
`append`'s own CTE would ever produce this shape in practice (`test_duplicate_seq_rejected.py`
already covers a single hand-crafted duplicate; this file adds genuine
concurrency).
"""

from __future__ import annotations

import asyncio
import json

import asyncpg
import pytest

MAX_PAYLOAD = 1_000_000
N_RACERS = 8


@pytest.mark.asyncio
async def test_concurrent_inserts_at_the_same_seq_reject_all_but_one(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
            "demo_minimal",
            json.dumps({}),
        )

    async def _insert_at_seq_one() -> bool:
        async with db_pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO run_events (run_id, seq, type, payload, epoch, worker_id) "
                    "VALUES ($1, 1, 'RUN_SUBMITTED', $2::jsonb, 0, 'api')",
                    run_id,
                    json.dumps(
                        {
                            "agent_type": "demo_minimal",
                            "input": {},
                            "is_demo": True,
                            "client_request_key": None,
                            "chaos_run_id": None,
                        }
                    ),
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    results = await asyncio.gather(*[_insert_at_seq_one() for _ in range(N_RACERS)])
    assert sum(results) == 1, "exactly one racer's insert at (run_id, seq=1) may succeed"

    async with db_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM run_events WHERE run_id = $1 AND seq = 1", run_id
        )
    assert count == 1, "the row is never silently overwritten by a losing racer"
