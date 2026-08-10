"""Load a run's full event log for replay (plan.md P2.4, T130).

Deliberately unbounded and unpaginated: replay must fold the *entire* log to
reconstruct correct state, unlike `GET /api/runs/{id}/events`'s keyset page,
which serves a UI that scrolls incrementally and is allowed to be partial.
"""

from __future__ import annotations

import json
from typing import Any

import asyncpg

from anchor.core.events.models import RunEvent

_LOAD_SQL = """
    SELECT run_id, seq, type, payload, epoch, worker_id, step_index, created_at
    FROM run_events
    WHERE run_id = $1
    ORDER BY seq ASC
"""


async def load_run_events(conn: asyncpg.Connection[Any], run_id: int) -> list[RunEvent]:
    rows = await conn.fetch(_LOAD_SQL, run_id)
    return [
        RunEvent(
            run_id=row["run_id"],
            seq=row["seq"],
            type=row["type"],
            payload=json.loads(row["payload"]),
            epoch=row["epoch"],
            worker_id=row["worker_id"],
            step_index=row["step_index"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
