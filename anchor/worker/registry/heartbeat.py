"""The heartbeat task (FR-067).

Refreshes `last_seen_at` on its own timer. Crash behaviour: a stopped
heartbeat is indistinguishable from a dead worker — **which is the intended
semantics**. There is no separate "I am alive" signal to fall out of sync
with the thing it is meant to represent.

`current_run_count` is updated here too, but it is telemetry, not an
authority: admission control (phase 6) reads the worker's own in-process
count before claiming, never this column. Using it to decide admission
would be a second source of truth for something the worker already knows.
"""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg

HEARTBEAT_INTERVAL_S = 5.0


async def refresh_once(
    conn: asyncpg.Connection[Any], worker_id: str, current_run_count: int
) -> None:
    await conn.execute(
        "UPDATE workers SET last_seen_at = now(), current_run_count = $2 WHERE id = $1",
        worker_id,
        current_run_count,
    )


async def heartbeat_loop(
    pool: asyncpg.Pool,
    worker_id: str,
    get_current_run_count: Any,
    *,
    interval_s: float = HEARTBEAT_INTERVAL_S,
) -> None:
    """Run forever, refreshing this worker's `last_seen_at` every
    `interval_s`. Intended to be one task inside the worker's top-level
    `asyncio.TaskGroup` (phase 3), so a failure here is visible rather than
    silently swallowed by a bare `create_task`.
    """
    while True:
        async with pool.acquire() as conn:
            await refresh_once(conn, worker_id, get_current_run_count())
        await asyncio.sleep(interval_s)
