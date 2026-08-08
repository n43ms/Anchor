"""T079 — `anchor.core.events.append` is the single append path. No module
outside it issues an `INSERT INTO run_events`."""

from __future__ import annotations

from pathlib import Path

ANCHOR_ROOT = Path(__file__).resolve().parents[2] / "anchor"
ALLOWED_FILE = ANCHOR_ROOT / "core" / "events" / "append.py"


def test_no_module_outside_append_inserts_into_run_events() -> None:
    offenders = []
    for path in ANCHOR_ROOT.rglob("*.py"):
        if path == ALLOWED_FILE:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if "`" in line:
                continue  # a markdown-style reference in a docstring, not SQL
            if "insert into run_events" in line.lower():
                offenders.append(f"{path}: {line.strip()!r}")

    assert not offenders, f"modules issuing INSERT INTO run_events outside append.py: {offenders}"
