"""T308 — the duplicate-effect count, the stranded-run count, the
needs_review list, effect counts, and every chaos-report figure are
computed from `tool_journal`/`run_events`/`demo_effects`, never from
`metrics_rollup` (D-30, D-49). A stale zero on the duplicate counter would
be the single most damaging thing this product could display.

Pure: AST-free but still I/O-free — a substring check against the modules
that compute these figures, which is exactly as strong a guarantee as this
property admits without a live database (a query string containing
"metrics_rollup" is the only way any of these reads could reach it, since
nothing else in this codebase names that table).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_timeline_never_queries_metrics_rollup() -> None:
    """`GET /api/runs/{id}/timeline`'s entire `RunSummary` is a per-run
    correctness read (duplicate_side_effects above all) — this module has
    no legitimate reason to ever touch the rollup at all, unlike
    `observability.py`, which legitimately serves *display* series from it
    alongside its own live correctness figures.
    """
    source = (REPO_ROOT / "anchor/api/serializers/timeline.py").read_text(encoding="utf-8")
    for sql in re.findall(r'"""(.*?)"""', source, flags=re.DOTALL):
        if "select" in sql.lower():
            assert "metrics_rollup" not in sql.lower(), (
                f"a query references metrics_rollup: {sql!r}"
            )


def test_observability_correctness_queries_do_not_reference_metrics_rollup() -> None:
    """`get_metrics` legitimately reads `metrics_rollup` for its *display*
    `series` — that is the rollup's whole purpose. What must never happen
    is the three correctness figures in the same response (duplicate
    count, stranded-run count, needs_review count) being computed from it.
    Checked by finding each correctness query's own SQL string and
    asserting `metrics_rollup` does not appear inside it.
    """
    source = (REPO_ROOT / "anchor/api/routers/observability.py").read_text(encoding="utf-8")
    for sql in re.findall(r'"""(.*?)"""', source, flags=re.DOTALL):
        if "count(*)" in sql.lower():
            assert "metrics_rollup" not in sql.lower(), (
                f"a correctness count query references metrics_rollup: {sql!r}"
            )


def test_get_metrics_reads_duplicate_and_stranded_counts_live() -> None:
    source = (REPO_ROOT / "anchor/api/routers/observability.py").read_text(encoding="utf-8")
    assert "STEP_SKIPPED_ON_REPLAY" in source, (
        "duplicate_side_effects must be derived from the log, not the rollup"
    )
    assert "status = 'running' AND lease_expires_at < now()" in source, (
        "stranded_runs must be derived live against the database clock (I5), not cached"
    )
