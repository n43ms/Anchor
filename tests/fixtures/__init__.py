"""Fixture logs: hand-built and captured, for replay testing without a live worker.

`load(name)` returns an ordered list of `RunEvent` for the log at
`tests/fixtures/logs/{name}.json`. `capture.py` (phase 2) writes new fixtures
from a live run's log rather than requiring them to be hand-typed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_LOGS_DIR = Path(__file__).parent / "logs"


def load_raw(name: str) -> list[dict[str, Any]]:
    """Load a fixture log's raw JSON event list, by file stem under logs/."""
    path = _LOGS_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)
    return data
