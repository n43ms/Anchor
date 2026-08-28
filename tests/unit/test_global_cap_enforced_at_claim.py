"""T152 — the global concurrency cap is enforced inside the claim
statement, never at submission (D-44, FR-003). Submitting far beyond the
cap leaves the running count AT the cap with the remainder `pending`, and
no submission is ever rejected — a cap applied at submission would enforce
nothing and would contradict "new runs stay pending" when the fleet is
saturated.
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one

MAX_PAYLOAD = 1_000_000
CAP = 3
N_RUNS = CAP + 5


async def _insert_runs(conn: asyncpg.Connection, n: int) -> list[int]:
    ids = []
    for _ in range(n):
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
            "test_isolated_cap_agent",
            json.dumps({}),
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_SUBMITTED,
            payload={
                "agent_type": "test_isolated_cap_agent",
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


@pytest.mark.asyncio
async def test_running_count_stops_at_cap_remainder_stays_pending(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        if conn.is_in_transaction():
            await conn.execute("ROLLBACK")
        await conn.execute("TRUNCATE TABLE runs RESTART IDENTITY CASCADE")
        run_ids = await _insert_runs(conn, N_RUNS)
        assert len(run_ids) == N_RUNS, "every submission succeeded — the cap never rejects one"

        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 100, 'dev') ON CONFLICT DO NOTHING"
        )

        claimed_count = 0
        for _ in range(N_RUNS):
            claimed = await claim_one(
                conn,
                worker_id="worker-a#1",
                lease_duration_ms=4_000,
                global_concurrency_cap=CAP,
                max_payload_bytes=MAX_PAYLOAD,
            )
            if claimed is None:
                break
            claimed_count += 1

        assert claimed_count == CAP, "claiming must stop exactly at the cap, not before or after"

        counts = await conn.fetchrow(
            """
            SELECT
                count(*) FILTER (WHERE status = 'running') AS running_count,
                count(*) FILTER (WHERE status = 'pending') AS pending_count
            FROM runs
            WHERE id = ANY($1::bigint[])
            """,
            run_ids,
        )
        assert counts is not None
        assert counts["running_count"] == CAP
        assert counts["pending_count"] == N_RUNS - CAP


@pytest.mark.asyncio
async def test_a_reclaim_is_never_blocked_by_a_saturated_cap(db_pool: asyncpg.Pool) -> None:
    """The cap correction stated in `core.leases.claim`'s module docstring:
    reclaiming an orphaned run does not grow the running count (the row is
    already `running`), so it must succeed even when the fleet sits exactly
    at the cap.
    """
    import asyncio

    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE runs RESTART IDENTITY CASCADE")
        (run_id,) = await _insert_runs(conn, 1)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev'), "
            "('worker-b#1', 'worker-b', 1, 'test', 2, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        first = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=50,
            global_concurrency_cap=1,  # the fleet is now exactly at cap
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert first is not None

        await asyncio.sleep(0.2)

        second = await claim_one(
            conn,
            worker_id="worker-b#1",
            lease_duration_ms=4_000,
            global_concurrency_cap=1,  # still at cap — this must still reclaim
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert second is not None
        assert second.run_id == run_id
        assert second.reason == "reclaimed_after_lease_expiry"
