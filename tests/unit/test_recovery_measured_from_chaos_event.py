"""T480 — recovery latency is measured from a `worker_kill` chaos_events
row's `created_at` to the reclaiming `RUN_CLAIMED` event's `created_at`
(data-model.md §6, report.py's whole reason for reading this table).
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.chaos.report import compute_report


async def _insert_chaos_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        """
        INSERT INTO chaos_runs (status, params, deployment_mode, config_profile,
                                 lease_duration_ms, renewal_interval_ms, heartbeat_at)
        VALUES ('running', '{}'::jsonb, 'local', 'demo', 4000, 1000, now())
        RETURNING id
        """
    )
    return run_id


async def _insert_run(conn: asyncpg.Connection, *, status: str = "completed") -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, status, epoch, finished_at) "
        "VALUES ('demo_minimal', $1, 1, now()) RETURNING id",
        status,
    )
    return run_id


@pytest.mark.asyncio
async def test_recovery_ms_measured_from_kill_to_reclaim(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        chaos_run_id = await _insert_chaos_run(conn)
        run_id = await _insert_run(conn)

        killed_at = await conn.fetchval(
            """
            INSERT INTO chaos_events (chaos_run_id, type, target_worker_id, affected_run_ids)
            VALUES ($1, 'worker_kill', 'worker-a#1', $2)
            RETURNING created_at
            """,
            chaos_run_id,
            [run_id],
        )
        # The reclaim event must be strictly after the kill for the
        # comparison to find it (report.py's `WHERE re.created_at > ce.created_at`).
        # `run_events` is immutable (migration 001), so the offset is set at
        # INSERT time rather than by a follow-up UPDATE.
        await conn.execute(
            "INSERT INTO run_events (run_id, seq, type, epoch, worker_id, payload, created_at) "
            "VALUES ($1, 1, 'RUN_CLAIMED', 1, 'worker-b#1', $2::jsonb, "
            "$3::timestamptz + interval '250 milliseconds')",
            run_id,
            json.dumps({"reason": "reclaimed_after_lease_expiry"}),
            killed_at,
        )

        report = await compute_report(conn, chaos_run_id=chaos_run_id, run_ids=[run_id], duration_seconds=10)

    assert report.recovery is not None
    assert report.recovery.p50 >= 200
    assert report.kills_injected == 1
