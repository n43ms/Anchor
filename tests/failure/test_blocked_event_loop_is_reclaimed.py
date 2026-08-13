"""T196 — a fully blocked event loop results in lease expiry and reclaim,
never in continued renewal: the renewer cannot signal liveness that
outlives a stalled process, because it shares the same loop as everything
else this worker is doing. Uses `anchor.chaos.injections.stall` (T212) to
construct the stall on demand rather than waiting for one to happen.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

import asyncpg
import pytest

from anchor.chaos.injections.stall import block_event_loop
from anchor.core.config.profiles import ConfigProfile, profile_settings
from anchor.core.db.errors import LeaseFencedError
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one
from anchor.worker.renewer import renew_forever

MAX_PAYLOAD = 1_000_000


@pytest.mark.asyncio
async def test_blocked_loop_lease_lapses_and_is_reclaimed(db_pool: asyncpg.Pool) -> None:
    lease_duration_ms = 200

    async with db_pool.acquire() as conn:
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
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-blocked#1', 'worker-blocked', 1, 'test', 1, 10, 'dev') "
            "ON CONFLICT DO NOTHING"
        )
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-b#1', 'worker-b', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        first_claim = await claim_one(
            conn,
            worker_id="worker-blocked#1",
            lease_duration_ms=lease_duration_ms,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert first_claim is not None

    # A real renewer is running, on the same event loop this test blocks
    # next — proving the renewer specifically cannot outlive a stalled
    # process (T216), rather than merely proving "nobody happened to renew."
    settings = profile_settings(ConfigProfile.DEMO).model_copy(
        update={"renewal_interval_ms": 20, "lease_duration_ms": lease_duration_ms}
    )
    renew_task = asyncio.create_task(
        renew_forever(
            db_pool,
            run_id=run_id,
            epoch=first_claim.epoch,
            worker_id="worker-blocked#1",
            settings=settings,
        )
    )
    await asyncio.sleep(0.05)  # let it renew normally at least once

    # Block the shared event loop synchronously — the renewer, sharing this
    # same thread, cannot run its next tick until this call returns, no
    # matter how short its own `renewal_interval_ms` is.
    block_event_loop(lease_duration_ms / 1000 * 3)

    renew_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, LeaseFencedError):
        await renew_task

    async with db_pool.acquire() as conn:
        second_claim = await claim_one(
            conn,
            worker_id="worker-b#1",
            lease_duration_ms=60_000,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )

    assert second_claim is not None
    assert second_claim.reason == "reclaimed_after_lease_expiry"
    assert second_claim.epoch == first_claim.epoch + 1
    assert second_claim.previous_worker_id == "worker-blocked#1"
