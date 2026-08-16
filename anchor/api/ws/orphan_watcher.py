"""Pushes the `lag` frame the instant a lease expires with no new claim yet
(plan.md P6.8, T343; contracts/websocket.md: "the most important two
seconds in the product").

**Why this is a poll loop and not something event-driven.** Nothing writes
an event when a lease merely expires — expiry is a fact about the current
time versus a stored timestamp, not a state transition anyone commits
(`orphaned` is derived at read time everywhere else in this system too,
data-model.md §12). This watcher polls specifically so the *push* can
still happen without waiting for a client's own poll interval; the poll
target here is short (`POLL_INTERVAL_S`) precisely because the two-second
window it exists to shrink is the product's own claim.
"""

from __future__ import annotations

import asyncio
import logging

import asyncpg

from anchor.api.ws.subscriber import Hub

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 1.0


async def watch_for_orphans(
    pool: asyncpg.Pool, hub: Hub, *, poll_interval_s: float = POLL_INTERVAL_S
) -> None:
    """Poll for runs whose lease has just expired with no new claim yet,
    and push exactly one `lag` frame per orphan transition — not a `lag`
    frame every tick for as long as the run stays orphaned, which would
    just be a slow-motion firehose that says nothing new after the first
    one.
    """
    previously_orphaned: set[int] = set()

    while True:
        await asyncio.sleep(poll_interval_s)
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, lease_expires_at
                    FROM runs
                    WHERE status = 'running' AND lease_expires_at < now()
                    """
                )
        except (asyncpg.PostgresError, OSError, TimeoutError) as exc:
            logger.warning("orphan watcher poll failed", extra={"error": str(exc)})
            continue

        currently_orphaned = {row["id"]: row["lease_expires_at"] for row in rows}

        for run_id, lease_expires_at in currently_orphaned.items():
            if run_id not in previously_orphaned:
                hub.push_lag(
                    run_id,
                    {
                        "kind": "lag",
                        "data": {
                            "orphaned": True,
                            "lease_expired_at": lease_expires_at.isoformat(),
                        },
                    },
                )

        previously_orphaned = set(currently_orphaned)
