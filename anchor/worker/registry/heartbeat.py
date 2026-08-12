"""The heartbeat task (FR-067, extended by P3.6/T175).

Refreshes `last_seen_at` on its own timer. Crash behaviour: a stopped
heartbeat is indistinguishable from a dead worker — **which is the intended
semantics**. There is no separate "I am alive" signal to fall out of sync
with the thing it is meant to represent.

`current_run_count` is updated here too, but it is telemetry, not an
authority: admission control (phase 6) reads the worker's own in-process
count before claiming, never this column. Using it to decide admission
would be a second source of truth for something the worker already knows.

**The Redis publish, added here, is the same story one layer further out**
(T175). `anchor:fleet` carries this tick's `worker_id`, `current_run_count`,
and `last_seen_at` for the console's live fleet view — display only.
`workers.last_seen_at` in PostgreSQL remains the only thing anyone reasons
about for staleness or liveness; a dropped Redis connection degrades the
console to polling PostgreSQL directly and changes nothing about execution
(`tests/boundary/test_redis_never_authoritative.py`, FR-058). Publishing is
best-effort: a publish failure is logged and swallowed rather than allowed
to interrupt the heartbeat itself, because a display-only channel failing
must never look like — or cause — a liveness problem.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import asyncpg
import redis.asyncio as redis_asyncio

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_S = 5.0
FLEET_TELEMETRY_CHANNEL = "anchor:fleet"


async def refresh_once(
    conn: asyncpg.Connection[Any], worker_id: str, current_run_count: int
) -> None:
    await conn.execute(
        "UPDATE workers SET last_seen_at = now(), current_run_count = $2 WHERE id = $1",
        worker_id,
        current_run_count,
    )


async def _publish_fleet_telemetry(
    redis_client: redis_asyncio.Redis, worker_id: str, current_run_count: int
) -> None:
    payload = json.dumps({"worker_id": worker_id, "current_run_count": current_run_count})
    try:
        await redis_client.publish(FLEET_TELEMETRY_CHANNEL, payload)
    except (OSError, TimeoutError) as exc:
        # Best-effort and display-only: nothing about ownership or lease
        # state depends on this succeeding (FR-058). Logged so a persistent
        # Redis outage is visible in the worker's own log, not silently
        # eaten.
        logger.warning(
            "fleet telemetry publish failed; console degrades to polling",
            extra={"worker_id": worker_id, "error": str(exc)},
        )


async def heartbeat_loop(
    pool: asyncpg.Pool,
    worker_id: str,
    get_current_run_count: Any,
    *,
    redis_client: redis_asyncio.Redis | None = None,
    interval_s: float = HEARTBEAT_INTERVAL_S,
) -> None:
    """Run forever, refreshing this worker's `last_seen_at` every
    `interval_s`. Intended to be one task inside the worker's top-level
    `asyncio.TaskGroup` (phase 3), so a failure here is visible rather than
    silently swallowed by a bare `create_task`.
    """
    while True:
        current_run_count = get_current_run_count()
        async with pool.acquire() as conn:
            await refresh_once(conn, worker_id, current_run_count)
        if redis_client is not None:
            await _publish_fleet_telemetry(redis_client, worker_id, current_run_count)
        await asyncio.sleep(interval_s)
