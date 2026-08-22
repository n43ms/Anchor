"""Record every injection as a `chaos_events` row (plan.md P8.3, T504).

**This table is one of the two inputs to the published recovery number**,
not documentation of the experiment (data-model.md §6) — `report.py`
measures recovery latency from a `worker_kill` row's `created_at` to the
reclaiming `RUN_CLAIMED`. `POST /api/workers/{id}/kill` records its own
row server-side (so a manual console kill and a harness-driven kill are
recorded identically, D-36); every other injection type is recorded here,
by the harness itself, at the moment it acts.
"""

from __future__ import annotations

import json
from typing import Any

import asyncpg


async def record_chaos_event(
    conn: asyncpg.Connection[Any],
    *,
    chaos_run_id: int | None,
    type: str,
    target_worker_id: str | None = None,
    affected_run_ids: list[int] | None = None,
    params: dict[str, Any] | None = None,
) -> int:
    event_id: int = await conn.fetchval(
        """
        INSERT INTO chaos_events (chaos_run_id, type, target_worker_id, affected_run_ids, params)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING id
        """,
        chaos_run_id,
        type,
        target_worker_id,
        affected_run_ids or [],
        json.dumps(params or {}),
    )
    return event_id
