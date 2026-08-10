"""Capture a live run's log as a fixture file (plan.md P2.6, T141).

Future fixtures should be captured from real chaos or integration runs
rather than hand-typed, so their event shapes never drift from what the
system actually produces. This helper is what makes that the path of
least resistance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import asyncpg

_LOGS_DIR = Path(__file__).parent / "logs"


async def capture_run_log(conn: asyncpg.Connection[Any], run_id: int, fixture_name: str) -> Path:
    """Serialize `run_id`'s complete event log to
    `tests/fixtures/logs/{fixture_name}.json`, in the same shape `load()`
    reads back, and return the written path.
    """
    rows = await conn.fetch(
        """
        SELECT run_id, seq, type, payload, epoch, worker_id, step_index, created_at
        FROM run_events
        WHERE run_id = $1
        ORDER BY seq ASC
        """,
        run_id,
    )
    events = [
        {
            "run_id": row["run_id"],
            "seq": row["seq"],
            "type": row["type"],
            "payload": json.loads(row["payload"]),
            "epoch": row["epoch"],
            "worker_id": row["worker_id"],
            "step_index": row["step_index"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]
    destination = _LOGS_DIR / f"{fixture_name}.json"
    destination.write_text(json.dumps(events, indent=2), encoding="utf-8")
    return destination
