"""T145 — N workers, one available run, exactly one claim succeeds.

No assertion in this file says "usually" or "eventually": `FOR UPDATE SKIP
LOCKED` inside one transaction (core.leases.claim) makes the property exact,
because a worker mid-transaction on the candidate row is invisible to every
other worker's scan rather than a blocking target they might still land on.
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
N_WORKERS = 8


async def _insert_run(conn: asyncpg.Connection, agent_type: str = "demo_minimal") -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
        agent_type,
        json.dumps({}),
    )
    await append(
        conn,
        run_id=run_id,
        type=EventType.RUN_SUBMITTED,
        payload={
            "agent_type": agent_type,
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
        worker_id = f"worker-race-{i}#1"
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ($1, $2, 1, 'test', $3, 10, 'dev') ON CONFLICT DO NOTHING",
            worker_id,
            f"worker-race-{i}",
            i,
        )
        ids.append(worker_id)
    return ids


@pytest.mark.asyncio
async def test_exactly_one_claim_succeeds_among_contending_workers(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as setup_conn:
        run_id = await _insert_run(setup_conn)
        worker_ids = await _register_workers(setup_conn, N_WORKERS)

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

    results = await asyncio.gather(*[_attempt(w) for w in worker_ids])
    successes = [r for r in results if r is not None]
    assert successes == [run_id], "exactly one worker must claim the single available run"

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT epoch, owner_worker_id FROM runs WHERE id = $1", run_id)
    assert row is not None
    assert row["epoch"] == 1
    assert row["owner_worker_id"] in worker_ids

    claim_events = None
    async with db_pool.acquire() as conn:
        claim_events = await conn.fetch(
            "SELECT worker_id FROM run_events WHERE run_id = $1 AND type = 'RUN_CLAIMED'", run_id
        )
    assert len(claim_events) == 1, "exactly one RUN_CLAIMED event, never a duplicate"
