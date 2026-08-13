"""T214 — a reusable "make me a zombie holding epoch N" fixture.

Four tests in this phase (T191-T195's `test_zombie_worker_fenced.py` and its
extensions) need the same setup: a run claimed once, then reclaimed by a
second worker after its lease has expired, leaving the first worker holding
a now-stale epoch it does not know is stale. Hand-rolling that four times is
how the four tests drift apart from each other and from what a real zombie
looks like — so it is built once here.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one

MAX_PAYLOAD = 1_000_000


@dataclass(frozen=True, slots=True)
class Zombie:
    """A worker that once legitimately held `run_id` at `stale_epoch`, and
    has since been superseded by `surviving_worker_id` at `current_epoch` —
    without the zombie itself having been told.
    """

    run_id: int
    stale_epoch: int
    stale_worker_id: str
    current_epoch: int
    surviving_worker_id: str


async def _insert_worker(conn: asyncpg.Connection, worker_id: str, label: str) -> None:
    await conn.execute(
        "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
        "VALUES ($1, $2, 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING",
        worker_id,
        label,
    )


async def _insert_run(conn: asyncpg.Connection, agent_type: str) -> int:
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


MakeZombie = Callable[..., Awaitable[Zombie]]


@pytest.fixture
def make_zombie(db_pool: asyncpg.Pool) -> MakeZombie:
    """Returns an async factory `make_zombie(agent_type="demo_minimal")
    -> Zombie`.

    Claims a run as `worker-zombie#1` with an already-lapsed lease (claimed
    with `lease_duration_ms=1`, then a short sleep), then reclaims it as
    `worker-survivor#1` — the same path a real reclaim takes
    (`core.leases.claim.claim_one`), so the resulting `WORKER_FENCED` event
    this fixture triggers is the real one, not a stand-in for it.
    """

    async def _make(agent_type: str = "demo_minimal") -> Zombie:
        async with db_pool.acquire() as conn:
            run_id = await _insert_run(conn, agent_type)
            await _insert_worker(conn, "worker-zombie#1", "worker-zombie")
            await _insert_worker(conn, "worker-survivor#1", "worker-survivor")

            zombie_claim = await claim_one(
                conn,
                worker_id="worker-zombie#1",
                lease_duration_ms=1,
                global_concurrency_cap=50,
                max_payload_bytes=MAX_PAYLOAD,
            )
        assert zombie_claim is not None, "setup failure: nothing to claim as the zombie"

        await asyncio.sleep(0.05)  # the 1ms lease is now well expired

        async with db_pool.acquire() as conn:
            survivor_claim = await claim_one(
                conn,
                worker_id="worker-survivor#1",
                lease_duration_ms=60_000,
                global_concurrency_cap=50,
                max_payload_bytes=MAX_PAYLOAD,
            )
        assert survivor_claim is not None, "setup failure: the survivor did not reclaim"
        assert survivor_claim.reason == "reclaimed_after_lease_expiry"

        return Zombie(
            run_id=run_id,
            stale_epoch=zombie_claim.epoch,
            stale_worker_id="worker-zombie#1",
            current_epoch=survivor_claim.epoch,
            surviving_worker_id="worker-survivor#1",
        )

    return _make
