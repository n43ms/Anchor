"""T224 — the race between two workers claiming the same run is
structurally impossible, not merely rare: one locking transaction
(`FOR UPDATE SKIP LOCKED`) that skips rows locked elsewhere means a second
worker's scan never observes the row as a candidate while the first
worker's claim transaction is in flight, regardless of how many times the
race is repeated.
"""

from __future__ import annotations

import asyncio
import json

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one

MAX_PAYLOAD = 1_000_000
N_ITERATIONS = 50


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
        "demo_minimal",
        json.dumps({}),
    )
    await append(
        conn,
        run_id=run_id,
        type=EventType.RUN_SUBMITTED,
        payload={
            "agent_type": "demo_minimal",
            "input": {},
            "is_demo": True,
            "client_request_key": None,
            "chaos_run_id": None,
        },
        epoch=0,
        worker_id="api",
        max_payload_bytes=MAX_PAYLOAD,
    )
    return run_id


@pytest.mark.asyncio
async def test_two_workers_never_both_win_the_same_run_across_many_repetitions(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-race-a#1', 'worker-race-a', 1, 'test', 1, 10, 'dev') "
            "ON CONFLICT DO NOTHING"
        )
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-race-b#1', 'worker-race-b', 1, 'test', 1, 10, 'dev') "
            "ON CONFLICT DO NOTHING"
        )

    for _ in range(N_ITERATIONS):
        async with db_pool.acquire() as conn:
            run_id = await _insert_run(conn)

        async def _attempt(worker_id: str) -> int | None:
            async with db_pool.acquire() as conn:
                claimed = await claim_one(
                    conn,
                    worker_id=worker_id,
                    lease_duration_ms=60_000,
                    global_concurrency_cap=50,
                    max_payload_bytes=MAX_PAYLOAD,
                )
                return claimed.run_id if claimed is not None else None

        results = await asyncio.gather(_attempt("worker-race-a#1"), _attempt("worker-race-b#1"))
        winners = [r for r in results if r is not None]
        assert winners == [run_id], f"exactly one worker must win run {run_id}, got {results}"
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE runs SET status = 'completed', owner_worker_id = NULL, "
                "lease_expires_at = NULL, finished_at = now() WHERE id = $1",
                run_id,
            )
