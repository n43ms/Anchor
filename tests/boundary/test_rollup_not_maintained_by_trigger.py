"""T309 — no trigger on `run_events` maintains `metrics_rollup` (D-49).

A trigger upserting the current bucket on every append would make every
worker contend on the *same* bucket row, serializing appends across runs
that currently never contend at all — the rollup is maintained by a
periodic job instead (`anchor.api.serializers.rollup`, run from
`anchor.api.app`'s background task). Pure: reads the migration source
directly, no database required.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "ops" / "migrations" / "versions"


def test_no_migration_creates_a_trigger_on_run_events_touching_metrics_rollup() -> None:
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "metrics_rollup" not in source:
            continue
        assert "CREATE TRIGGER" not in source.upper(), (
            f"{path.name} must not create a trigger touching metrics_rollup (D-49)"
        )


def test_rollup_job_is_periodic_not_trigger_driven() -> None:
    source = (REPO_ROOT / "anchor/api/app.py").read_text(encoding="utf-8")
    assert "run_rollup_once" in source
    assert "asyncio.sleep" in source
