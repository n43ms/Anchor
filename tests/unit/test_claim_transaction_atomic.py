"""T149 — the epoch increment, owner assignment, lease extension, status
transition, and `RUN_CLAIMED` append are all one transaction. An induced
failure after the UPDATE (but before the `RUN_CLAIMED` append commits)
leaves none of them — not a partial claim with no event, which would be a
worse failure mode than no claim at all.
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases import claim as claim_module

MAX_PAYLOAD = 1_000_000


class _BoomOnAppend(Exception):
    pass


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
async def test_failure_after_update_leaves_no_partial_claim(
    db_pool: asyncpg.Pool, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )

        async def _boom(*args: object, **kwargs: object) -> None:
            raise _BoomOnAppend("simulated crash between the claim UPDATE and its append")

        monkeypatch.setattr(claim_module, "append", _boom)

        with pytest.raises(_BoomOnAppend):
            await claim_module.claim_one(
                conn,
                worker_id="worker-a#1",
                lease_duration_ms=4_000,
                global_concurrency_cap=50,
                max_payload_bytes=MAX_PAYLOAD,
            )

        row = await conn.fetchrow(
            "SELECT status, epoch, owner_worker_id, lease_expires_at, claimed_at "
            "FROM runs WHERE id = $1",
            run_id,
        )
        assert row is not None
        assert row["status"] == "pending", "the UPDATE must have rolled back with everything else"
        assert row["epoch"] == 0
        assert row["owner_worker_id"] is None
        assert row["lease_expires_at"] is None
        assert row["claimed_at"] is None

        event_count = await conn.fetchval(
            "SELECT count(*) FROM run_events WHERE run_id = $1 AND type = 'RUN_CLAIMED'", run_id
        )
        assert event_count == 0
