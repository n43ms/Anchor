"""T150 — a step lasting longer than `lease_duration` is NOT fenced, because
the renewer extends the lease independently of step progress (FR-012). This
is the behaviour that makes two configuration profiles possible at all: a
4-second demo lease must survive a step that legitimately runs for longer
than 4 seconds, purely because the renewer keeps extending it on its own
1-second timer regardless of what the execution task is doing.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

import asyncpg
import pytest

from anchor.core.config.profiles import ConfigProfile, profile_settings
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one
from anchor.worker.renewer import renew_forever

MAX_PAYLOAD = 1_000_000


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
async def test_lease_survives_a_step_longer_than_the_original_lease_duration(
    db_pool: asyncpg.Pool,
) -> None:
    settings = profile_settings(ConfigProfile.DEMO)
    settings = settings.model_copy(update={"lease_duration_ms": 4000, "renewal_interval_ms": 1000})

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        claimed = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=settings.lease_duration_ms,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert claimed is not None

    renew_task = asyncio.create_task(
        renew_forever(
            db_pool,
            run_id=run_id,
            epoch=claimed.epoch,
            worker_id="worker-a#1",
            settings=settings,
        )
    )
    try:
        # Longer than the 1000ms renewal cycle, proving that the renewer extends it.
        await asyncio.sleep(1.5)
    finally:
        renew_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await renew_task

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT epoch, owner_worker_id, lease_expires_at, (lease_expires_at > now()) AS still_valid "
            "FROM runs WHERE id = $1",
            run_id,
        )
    assert row is not None
    assert row["epoch"] == claimed.epoch, "no reclaim occurred — the epoch never advanced"
    assert row["owner_worker_id"] == "worker-a#1"
    assert row["still_valid"], "continuous renewal must have kept the lease ahead of now()"
