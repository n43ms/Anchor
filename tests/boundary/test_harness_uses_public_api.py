"""T484 — the harness drives the system under test through the public HTTP
API (D-36), so the console's launch button and a scheduled CI run can never
silently diverge in what they actually exercise.

Scans the workload-generation and injection modules for a direct mutating
SQL statement against `runs`, `run_events`, or `workers` — the protocol
tables only `core/` and `worker/` are supposed to write. `anchor.chaos.recorder`
(and the `chaos_events` inserts inside the injection modules that call it)
is exempt: recording the harness's own evidence is not driving the system
under test, and `chaos_events` is not one of the tables this check
protects. `anchor.chaos.chaos_worker` is exempt too — it is the one
deliberate exception (its own module docstring), reusing `anchor.worker.loop`'s
real claim/execute code directly rather than either HTTP or raw SQL.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_CHECKED_MODULES = (
    "anchor/chaos/workload.py",
    "anchor/chaos/injections/kill.py",
    "anchor/chaos/injections/latency.py",
    "anchor/chaos/injections/tool_failure.py",
    "anchor/chaos/injections/uncertainty.py",
)
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT INTO|UPDATE|DELETE FROM)\s+(runs|run_events|workers)\b", re.IGNORECASE
)


def test_workload_and_injection_modules_issue_no_direct_protocol_sql() -> None:
    for relative_path in _CHECKED_MODULES:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        match = _FORBIDDEN_SQL.search(source)
        assert match is None, (
            f"{relative_path} issues direct SQL against a protocol table "
            f"({match.group(0) if match else ''!r}) — the harness must drive "
            "the system under test through the public API (D-36), not around it"
        )


def test_harness_and_workload_modules_import_httpx() -> None:
    for relative_path in _CHECKED_MODULES:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "import httpx" in source, f"{relative_path} does not use the public HTTP client"
