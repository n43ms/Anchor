"""T481 — the config profile and lease duration are stored on the report
and returned with every figure (FR-061). A recovery figure without them is
not a measurement.
"""

from __future__ import annotations

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from anchor.api.app import create_app
from anchor.chaos.invariants import AllInvariants, InvariantResult
from anchor.chaos.report import ChaosReport, persist_report


async def _insert_chaos_run(conn: asyncpg.Connection, *, config_profile: str, lease_ms: int) -> int:
    run_id: int = await conn.fetchval(
        """
        INSERT INTO chaos_runs (status, params, deployment_mode, config_profile,
                                 lease_duration_ms, renewal_interval_ms, heartbeat_at)
        VALUES ('completed', '{}'::jsonb, 'local', $1, $2, 1000, now())
        RETURNING id
        """,
        config_profile,
        lease_ms,
    )
    return run_id


def _clean_report(chaos_run_id: int) -> ChaosReport:
    passing = InvariantResult("x", passed=True)
    return ChaosReport(
        chaos_run_id=chaos_run_id,
        invariants=AllInvariants(passing, passing, passing, passing, passing),
        duplicate_effect_count=0,
        stranded_run_count=0,
        kills_injected=0,
        runs_total=5,
        steps_total=20,
        recovery=None,
        replay_steps_mean=None,
        replay_ms_mean=None,
        steps_per_second=2.0,
        fencing_events=0,
        uncertainty_entries={},
        dead_letter_count=0,
        duration_seconds=10,
    )


@pytest.mark.asyncio
async def test_report_response_carries_profile_and_lease(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        chaos_run_id = await _insert_chaos_run(conn, config_profile="production", lease_ms=20000)
        await persist_report(conn, _clean_report(chaos_run_id))

    app = create_app()
    app.state.db_pool = db_pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/chaos/{chaos_run_id}/report")

    assert response.status_code == 200
    body = response.json()
    assert body["config_profile"] == "production"
    assert body["lease_duration_ms"] == 20000
