"""The Redis kill subscriber (FR-068).

Hard-exits the process on message, with **no cleanup** — this models a
crash, not a graceful shutdown, which is the point: the kill endpoint is
how the product demonstrates recovery from real failure, not from a
simulated one.

Each worker subscribes to its own channel, `anchor:kill:{worker_id}`, rather
than a single shared channel filtered in-process. A kill is always addressed
to one specific worker (the API resolves "kill worker X" to a worker id
before publishing), so a per-worker channel means the subscribed worker does
no filtering work and a Redis outage silently degrades exactly one thing —
kill delivery — without touching any other channel (D-50's reasoning applied
here: Redis is never authoritative, so its unavailability must degrade
narrowly and visibly, never silently corrupt ownership).
"""

from __future__ import annotations

import os
import sys

import redis.asyncio as redis_asyncio


def kill_channel(worker_id: str) -> str:
    return f"anchor:kill:{worker_id}"


async def publish_kill(client: redis_asyncio.Redis, worker_id: str) -> None:
    await client.publish(kill_channel(worker_id), "kill")


async def subscribe_and_wait_for_kill(client: redis_asyncio.Redis, worker_id: str) -> None:
    """Block until a kill message arrives on this worker's channel, then
    hard-exit. Intended to run as one task inside the worker's top-level
    `TaskGroup`.
    """
    pubsub = client.pubsub()
    await pubsub.subscribe(kill_channel(worker_id))
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        # No cleanup, no cancellation of sibling tasks, no flush: a crash
        # does not wait its turn. os._exit bypasses atexit handlers and
        # finally blocks, which is the entire point.
        sys.stderr.write(f"{worker_id}: kill received, hard-exiting\n")
        sys.stderr.flush()
        os._exit(1)
