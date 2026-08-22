"""T482 — `violations` is returned as `[]` rather than `null` when clean
(data-model.md §8): the empty case is the expected one and is represented
explicitly, not by absence.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.api.serializers.chaos import CHAOS_REPORT_COLUMNS, serialize_chaos_report
from anchor.chaos.invariants import AllInvariants, InvariantResult
from anchor.chaos.report import ChaosReport, persist_report


async def _insert_chaos_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        """
        INSERT INTO chaos_runs (status, params, deployment_mode, config_profile,
                                 lease_duration_ms, renewal_interval_ms, heartbeat_at)
        VALUES ('completed', '{}'::jsonb, 'local', 'demo', 4000, 1000, now())
        RETURNING id
        """
    )
    return run_id


@pytest.mark.asyncio
async def test_violations_column_defaults_to_empty_array_not_null(db_pool: asyncpg.Pool) -> None:
    passing = InvariantResult("x", passed=True)
    async with db_pool.acquire() as conn:
        chaos_run_id = await _insert_chaos_run(conn)
        report = ChaosReport(
            chaos_run_id=chaos_run_id,
            invariants=AllInvariants(passing, passing, passing, passing, passing),
            duplicate_effect_count=0,
            stranded_run_count=0,
            kills_injected=0,
            runs_total=1,
            steps_total=1,
            recovery=None,
            replay_steps_mean=None,
            replay_ms_mean=None,
            steps_per_second=None,
            fencing_events=0,
            uncertainty_entries={},
            dead_letter_count=0,
            duration_seconds=10,
        )
        await persist_report(conn, report)

        raw = await conn.fetchval(
            "SELECT violations FROM chaos_reports WHERE chaos_run_id = $1", chaos_run_id
        )
        assert raw == "[]"

        row = await conn.fetchrow(
            f"SELECT {CHAOS_REPORT_COLUMNS} FROM chaos_reports cr "
            "JOIN chaos_runs run ON run.id = cr.chaos_run_id WHERE cr.chaos_run_id = $1",
            chaos_run_id,
        )
        assert row is not None
        serialized = serialize_chaos_report(row)

    assert serialized.violations == []
