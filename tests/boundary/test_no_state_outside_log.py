"""T070 — no table other than `run_events`, `tool_journal`, and
`demo_effects` records what happened during a run: everything else is
either the run's own row (status/lease bookkeeping, not history) or fleet
metadata."""

from __future__ import annotations

import asyncpg
import pytest

_ALLOWED_HISTORY_TABLES = {"run_events", "tool_journal", "demo_effects"}
_NON_HISTORY_TABLES = {
    "runs",
    "workers",
    "worker_label_incarnations",
    "runtime_config",
    "tool_registry",
    "chaos_runs",
    "chaos_reports",
    "chaos_events",
    "metrics_rollup",
    "metrics_rollup_watermark",
    "alembic_version",
}


@pytest.mark.asyncio
async def test_only_the_documented_tables_exist(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    names = {r["tablename"] for r in rows}
    undocumented = names - _ALLOWED_HISTORY_TABLES - _NON_HISTORY_TABLES
    assert not undocumented, f"undocumented table(s) recording run history: {undocumented}"
