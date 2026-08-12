"""T146 — sustained contention: many runs, many workers, repeated. No run is
ever claimed twice at the same epoch, and every claimable run is eventually
claimed by exactly one worker per pass.
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
N_RUNS = 15
N_WORKERS = 6


async def _insert_runs(conn: asyncpg.Connection, n: int) -> list[int]:
    ids = []
    for _ in range(n):
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
        ids.append(run_id)
    return ids


async def _register_workers(conn: asyncpg.Connection, n: int) -> list[str]:
    ids = []
    for i in range(n):
        worker_id = f"worker-load-{i}#1"
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ($1, $2, 1, 'test', $3, 10, 'dev') ON CONFLICT DO NOTHING",
            worker_id,
            f"worker-load-{i}",
            i,
        )
        ids.append(worker_id)
    return ids


@pytest.mark.asyncio
async def test_no_run_claimed_twice_at_the_same_epoch_under_sustained_contention(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as setup_conn:
        run_ids = await _insert_runs(setup_conn, N_RUNS)
        worker_ids = await _register_workers(setup_conn, N_WORKERS)

    claimed_run_ids: list[int] = []

    async def _attempt(worker_id: str) -> int | None:
        async with db_pool.acquire() as conn:
            claimed = await claim_one(
                conn,
                worker_id=worker_id,
                lease_duration_ms=4_000,
                global_concurrency_cap=50,
                max_payload_bytes=MAX_PAYLOAD,
            )
            return claimed.run_id if claimed is not None else None

    # Repeat several passes of full contention: every worker races every
    # other worker for whatever is left pending.
    for _ in range(4):
        results = await asyncio.gather(*[_attempt(w) for w in worker_ids])
        claimed_run_ids.extend(r for r in results if r is not None)

    assert sorted(claimed_run_ids) == sorted(set(claimed_run_ids)), (
        "no run id was returned as claimed more than once across all passes"
    )
    assert set(claimed_run_ids) == set(run_ids), "every run was eventually claimed exactly once"

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT run_id, epoch, worker_id FROM run_events "
            "WHERE type = 'RUN_CLAIMED' AND run_id = ANY($1::bigint[])",
            run_ids,
        )
    seen: set[tuple[int, int]] = set()
    for row in rows:
        key = (row["run_id"], row["epoch"])
        assert key not in seen, f"run {row['run_id']} epoch {row['epoch']} claimed twice"
        seen.add(key)
