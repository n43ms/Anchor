"""Fixture logs: hand-built and captured, for replay testing without a live worker.

`load(name)` returns an ordered list of `RunEvent` for the log at
`tests/fixtures/logs/{name}.json`. `capture.py` (phase 2) writes new fixtures
from a live run's log rather than requiring them to be hand-typed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from anchor.core.events.models import RunEvent

_LOGS_DIR = Path(__file__).parent / "logs"


def load_raw(name: str) -> list[dict[str, Any]]:
    """Load a fixture log's raw JSON event list, by file stem under logs/."""
    path = _LOGS_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)
    return data


def load(name: str) -> list[RunEvent]:
    """Load a fixture log as ordered `RunEvent`s (T140).

    Parses each raw event through the `RunEvent` envelope model — a
    malformed fixture fails here, at load time, rather than surfacing as a
    confusing assertion failure deep inside `reconstruct`.
    """
    return [RunEvent.model_validate(raw) for raw in load_raw(name)]


def all_fixture_names() -> list[str]:
    """Every fixture file stem under `logs/`, for the parses-against-the-
    payload-models test to iterate without hand-listing them."""
    return sorted(p.stem for p in _LOGS_DIR.glob("*.json"))
