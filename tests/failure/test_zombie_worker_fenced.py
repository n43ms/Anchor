"""T191-T194 — the zombie-fencing scenario, the hardest and most valuable
phase-4 behaviour: a worker holding a stale epoch attempts an append after
a second worker has already reclaimed the run, and the **database** rejects
it, not Python.
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.core.db.errors import LeaseFencedError
from anchor.core.db.pool import acquire as acquire_translated
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one

from .conftest import MAX_PAYLOAD, MakeZombie, Zombie


@pytest.mark.asyncio
async def test_zombie_append_rejected_by_database_as_an001(
    db_pool: asyncpg.Pool, make_zombie: MakeZombie
) -> None:
    zombie: Zombie = await make_zombie()

    with pytest.raises(LeaseFencedError) as excinfo:
        async with acquire_translated(db_pool) as conn:
            await append(
                conn,
                run_id=zombie.run_id,
                type=EventType.STEP_STARTED,
                payload={"step_index": 0, "action_kind": "tool"},
                epoch=zombie.stale_epoch,
                worker_id=zombie.stale_worker_id,
                step_index=0,
                max_payload_bytes=MAX_PAYLOAD,
            )

    # T199: both epochs are present, because the console (§22.4) requires
    # displaying both, and the rejection genuinely knows both.
    assert excinfo.value.stale_epoch == zombie.stale_epoch
    assert excinfo.value.current_epoch == zombie.current_epoch
    assert excinfo.value.run_id == zombie.run_id


@pytest.mark.asyncio
async def test_zombie_append_leaves_no_partial_write(
    db_pool: asyncpg.Pool, make_zombie: MakeZombie
) -> None:
    zombie: Zombie = await make_zombie()

    async with db_pool.acquire() as conn:
        last_seq_before = await conn.fetchval(
            "SELECT last_seq FROM runs WHERE id = $1", zombie.run_id
        )

    with pytest.raises(LeaseFencedError):
        async with acquire_translated(db_pool) as conn:
            await append(
                conn,
                run_id=zombie.run_id,
                type=EventType.STEP_STARTED,
                payload={"step_index": 0, "action_kind": "tool"},
                epoch=zombie.stale_epoch,
                worker_id=zombie.stale_worker_id,
                step_index=0,
                max_payload_bytes=MAX_PAYLOAD,
            )

    async with db_pool.acquire() as conn:
        last_seq_after = await conn.fetchval(
            "SELECT last_seq FROM runs WHERE id = $1", zombie.run_id
        )

    assert last_seq_after == last_seq_before, "a rejected append must not advance the counter"


@pytest.mark.asyncio
async def test_fenced_worker_writes_nothing_further_including_no_error_event(
    db_pool: asyncpg.Pool, make_zombie: MakeZombie
) -> None:
    zombie: Zombie = await make_zombie()

    with pytest.raises(LeaseFencedError):
        async with acquire_translated(db_pool) as conn:
            await append(
                conn,
                run_id=zombie.run_id,
                type=EventType.STEP_STARTED,
                payload={"step_index": 0, "action_kind": "tool"},
                epoch=zombie.stale_epoch,
                worker_id=zombie.stale_worker_id,
                step_index=0,
                max_payload_bytes=MAX_PAYLOAD,
            )

    # I3/FR-019: the fenced worker's own opinion about what happened —
    # including a STEP_FAILED describing the rejection itself — must never
    # reach the run's log. Only the survivor's RUN_CLAIMED + WORKER_FENCED
    # (appended by make_zombie's reclaim) may carry the stale worker's id.
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT type, worker_id FROM run_events WHERE run_id = $1 ORDER BY seq", zombie.run_id
        )

    events_by_zombie = [
        r for r in rows 
        if r["worker_id"] == zombie.stale_worker_id and r["type"] != "RUN_CLAIMED"
    ]
    assert events_by_zombie == [], (
        "the fenced worker must not appear as the writer of any subsequent event in the run's log"
    )
    fenced_events = [r for r in rows if r["type"] == "WORKER_FENCED"]
    assert len(fenced_events) == 1, "the survivor's reclaim must have recorded exactly one fencing"
    assert fenced_events[0]["worker_id"] == zombie.surviving_worker_id


@pytest.mark.asyncio
async def test_fenced_worker_does_not_retry_and_claims_other_work_normally(
    db_pool: asyncpg.Pool, make_zombie: MakeZombie
) -> None:
    zombie: Zombie = await make_zombie()

    with pytest.raises(LeaseFencedError):
        async with acquire_translated(db_pool) as conn:
            await append(
                conn,
                run_id=zombie.run_id,
                type=EventType.STEP_STARTED,
                payload={"step_index": 0, "action_kind": "tool"},
                epoch=zombie.stale_epoch,
                worker_id=zombie.stale_worker_id,
                step_index=0,
                max_payload_bytes=MAX_PAYLOAD,
            )
    # No retry: per I3, the caller must not attempt this append again with
    # the same stale epoch. This test asserts the *contract*, not a retry
    # loop's absence, by exercising exactly one attempt above and then
    # proving the same worker id can claim a fresh, unrelated run normally.

    async with db_pool.acquire() as conn:
        other_run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
            "demo_minimal",
            json.dumps({}),
        )
        await append(
            conn,
            run_id=other_run_id,
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
        claimed = await claim_one(
            conn,
            worker_id=zombie.stale_worker_id,
            lease_duration_ms=60_000,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )

    assert claimed is not None
    assert claimed.run_id == other_run_id, (
        "the previously-fenced worker id must be able to claim unrelated work normally"
    )
