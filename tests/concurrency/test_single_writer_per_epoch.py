"""T200 — across a contended, repeatedly-reclaimed workload, no
`(run_id, epoch)` pair ever carries events from two different worker ids
(`I3`). One run's lease is set deliberately short so it is reclaimed many
times over many rounds, each round racing N workers against the single
expired lease — the same contention `test_exactly_one_claim` exercises
once, repeated here specifically to check epoch/writer pairing across the
whole history, not just the outcome of one race.
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
N_WORKERS = 6
N_ROUNDS = 10
SHORT_LEASE_MS = 1


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


async def _register_workers(conn: asyncpg.Connection, n: int) -> list[str]:
    ids = []
    for i in range(n):
        worker_id = f"worker-epoch-race-{i}#1"
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ($1, $2, 1, 'test', $3, 10, 'dev') ON CONFLICT DO NOTHING",
            worker_id,
            f"worker-epoch-race-{i}",
            i,
        )
        ids.append(worker_id)
    return ids


@pytest.mark.asyncio
async def test_no_epoch_ever_carries_events_from_two_worker_ids(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as setup_conn:
        run_id = await _insert_run(setup_conn)
        worker_ids = await _register_workers(setup_conn, N_WORKERS)

    async def _attempt(worker_id: str) -> None:
        async with db_pool.acquire() as conn:
            await claim_one(
                conn,
                worker_id=worker_id,
                lease_duration_ms=SHORT_LEASE_MS,
                global_concurrency_cap=50,
                max_payload_bytes=MAX_PAYLOAD,
            )

    for _ in range(N_ROUNDS):
        await asyncio.sleep(SHORT_LEASE_MS / 1000 * 2)  # ensure the previous round's lease expired
        await asyncio.gather(*[_attempt(w) for w in worker_ids])

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT epoch, worker_id FROM run_events WHERE run_id = $1", run_id)

    writers_by_epoch: dict[int, set[str]] = {}
    for row in rows:
        writers_by_epoch.setdefault(row["epoch"], set()).add(row["worker_id"])

    offenders = {epoch: writers for epoch, writers in writers_by_epoch.items() if len(writers) > 1}
    assert offenders == {}, f"epochs carrying events from more than one worker id: {offenders}"
