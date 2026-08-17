"""T147 — the second claim of an orphaned run carries
`reason: reclaimed_after_lease_expiry` and `epoch + 1`, and `status` stays
`running` throughout — reclaim is an ownership handoff, never a status
transition (data-model.md §1's state machine; the derived `orphaned` display
state is never stored, per `core.leases.claim`'s own docstring).
"""

from __future__ import annotations

import asyncio
import json

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one
from anchor.core.replay.load import load_run_events

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
async def test_reclaim_carries_correct_reason_and_epoch_and_keeps_status_running(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev'), "
            "('worker-b#1', 'worker-b', 1, 'test', 2, 10, 'dev') ON CONFLICT DO NOTHING"
        )

        first = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=50,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert first is not None
        assert first.reason == "initial"
        assert first.epoch == 1

        mid_row = await conn.fetchrow(
            "SELECT status, lease_expires_at FROM runs WHERE id = $1", run_id
        )
        assert mid_row is not None
        assert mid_row["status"] == "running"

        await asyncio.sleep(1.0)  # let the 50ms lease expire

        second = await claim_one(
            conn,
            worker_id="worker-b#1",
            lease_duration_ms=4_000,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert second is not None
        assert second.run_id == run_id
        assert second.reason == "reclaimed_after_lease_expiry"
        assert second.epoch == 2
        assert second.previous_worker_id == "worker-a#1"

        final_row = await conn.fetchrow(
            "SELECT status, owner_worker_id, epoch FROM runs WHERE id = $1", run_id
        )
        assert final_row is not None
        assert final_row["status"] == "running", (
            "reclaim never transitions status away from running"
        )
        assert final_row["owner_worker_id"] == "worker-b#1"
        assert final_row["epoch"] == 2

        events = await load_run_events(conn, run_id)
        claim_payloads = [e.payload for e in events if e.type == EventType.RUN_CLAIMED]
        assert len(claim_payloads) == 2
        assert claim_payloads[1]["reason"] == "reclaimed_after_lease_expiry"
