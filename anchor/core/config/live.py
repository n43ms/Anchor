"""Live configuration: read at startup, then a bounded re-poll (plan.md
P6.6, T330-T331; FR-062, FR-063).

`runtime_config` is authoritative for every timing, retry, and concurrency
value (FR-059); this module is what lets an already-running process notice
a change an operator makes through `PATCH /api/config` without restarting.

**The bounded poll is the correctness path; the Redis nudge is an
optimization only** (T331): `poll_forever` re-reads `runtime_config` on its
own timer regardless of Redis, so a live configuration change is observed
within one poll interval even with Redis down. The optional nudge
(`anchor:config`, published by the config route on every applied change)
only shortens that wait — its absence changes latency, never correctness
or eventual consistency.

**`POLL_INTERVAL_S` is a module constant, not a sixteenth `runtime_config`
key**, for the same reason `anchor.api.serializers.workers.STALE_AFTER_SECONDS`
is one: it is an operational latency knob no invariant depends on (unlike
the fifteen keys `RuntimeSettings` models, which the epoch/lease/fencing
machinery reads directly and which the `runtime_config_assert` trigger
enforces a cross-row relationship over). Widening or narrowing it changes
how quickly a change propagates, never whether the system stays correct
while it hasn't yet.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import asyncpg

from anchor.core.config.loader import load_runtime_settings
from anchor.core.config.settings import RuntimeSettings

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 5.0
CONFIG_CHANGED_CHANNEL = "anchor:config"


class _RedisSubscribable(Protocol):
    def pubsub(self) -> Any: ...


@dataclass
class LiveSettings:
    """Mutable holder for one process's current view of `runtime_config`.

    `poll_forever` is the only writer. Every reader takes `.current` at the
    instant it needs it — `anchor.worker.loop._run_steps` does so exactly
    once per loop iteration, at the top, which is what makes a change take
    effect only at a step boundary (T332) rather than mid-step: nothing
    inside one iteration re-reads `.current` a second time.
    """

    current: RuntimeSettings
    version: int


async def _read_version(conn: asyncpg.Connection[Any]) -> int:
    """The maximum `version` across the fifteen seeded rows — a single
    comparison that catches a change to *any* one of them, since every
    write to any row increments that row's own version (data-model.md §9).
    """
    value = await conn.fetchval("SELECT max(version) FROM runtime_config")
    return int(value) if value is not None else 0


async def load_live_settings(conn: asyncpg.Connection[Any]) -> LiveSettings:
    """Read `runtime_config` once, at startup (T330)."""
    settings = await load_runtime_settings(conn)
    version = await _read_version(conn)
    return LiveSettings(current=settings, version=version)


async def poll_forever(
    pool: asyncpg.Pool,
    live: LiveSettings,
    *,
    redis_client: _RedisSubscribable | None = None,
    poll_interval_s: float = POLL_INTERVAL_S,
) -> None:
    """Refresh `live.current` from `runtime_config` forever, on a bounded
    timer, optionally woken early by a `anchor:config` nudge.

    A refresh failure (the database is briefly unreachable) is logged and
    the previous values are kept — the same fail-safe posture as any other
    read of already-loaded configuration; it does not affect any run
    already in flight, which is holding its own already-loaded snapshot.
    """
    wake_early = asyncio.Event()
    subscriber_task: asyncio.Task[None] | None = None
    if redis_client is not None:
        subscriber_task = asyncio.create_task(
            _watch_for_nudge(redis_client, wake_early), name="config-nudge-subscriber"
        )

    try:
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(wake_early.wait(), timeout=poll_interval_s)
            wake_early.clear()

            try:
                async with pool.acquire() as conn:
                    new_version = await _read_version(conn)
                    if new_version != live.version:
                        settings = await load_runtime_settings(conn)
                        live.current = settings
                        live.version = new_version
                        logger.info("runtime_config reloaded", extra={"version": new_version})
            except (asyncpg.PostgresError, OSError, TimeoutError) as exc:
                logger.warning(
                    "live configuration refresh failed; keeping previous values",
                    extra={"error": str(exc)},
                )
    finally:
        if subscriber_task is not None:
            subscriber_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await subscriber_task


async def _watch_for_nudge(redis_client: _RedisSubscribable, wake_early: asyncio.Event) -> None:
    """Set `wake_early` on every `anchor:config` message. Best-effort and
    display/latency-only (FR-058 in spirit, though this channel never
    touches ownership or leases at all): a subscribe failure here just
    means `poll_forever` falls back to its bounded timer, unconditionally.
    """
    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(CONFIG_CHANGED_CHANNEL)
        async for message in pubsub.listen():
            if message.get("type") == "message":
                wake_early.set()
    except (OSError, TimeoutError) as exc:
        logger.warning(
            "config-change subscription failed; falling back to the bounded poll",
            extra={"error": str(exc)},
        )


async def publish_config_changed(redis_client: Any | None) -> None:
    """Best-effort nudge published by `PATCH /api/config` after a change is
    committed (T333). Never required for correctness — see module
    docstring.
    """
    if redis_client is None:
        return
    try:
        await redis_client.publish(CONFIG_CHANGED_CHANNEL, json.dumps({"changed": True}))
    except (OSError, TimeoutError) as exc:
        logger.warning("config-change nudge publish failed", extra={"error": str(exc)})
