"""The single always-on Redis subscription (plan.md P6.8, T339; D-50).

**Why one subscription, demultiplexed in process, rather than one per
run.** A per-run channel would have to be subscribed to at connect time,
which puts subscribe/unsubscribe on the request path and opens a race with
a name: an event published between "the client connected" and "the API
finished subscribing" is lost, invisible unless someone notices a gap in
`seq`. A single, always-on subscription — held for the lifetime of the API
process, started here in `anchor.api.app`'s lifespan — removes that race
by construction: every event is seen by this one subscriber before any
client could possibly have missed it, and routing to the right client is
then a synchronous, in-process dictionary lookup in `Hub`.

Redis is a delivery mechanism and nothing more (contracts/websocket.md): if
this subscriber's connection drops, the console falls back to polling and
execution is entirely unaffected (FR-058). This module never becomes
authoritative about anything — it only decides which already-connected
client queue receives a copy of a message this process already received.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Protocol

from anchor.api.ws.backpressure import BoundedClientQueue
from anchor.core.events.publish import EVENTS_CHANNEL
from anchor.worker.registry.heartbeat import FLEET_TELEMETRY_CHANNEL

logger = logging.getLogger(__name__)


class Hub:
    """Per-process fan-out registry: which connected client queues want
    which run's events, and which want fleet telemetry. Read and written
    only from the event loop this process runs on — no lock is needed
    because there is never an `await` between a membership check and the
    mutation that follows it in any method here.
    """

    def __init__(self) -> None:
        self._run_subscribers: dict[int, set[BoundedClientQueue]] = {}
        self._fleet_subscribers: set[BoundedClientQueue] = set()

    def subscribe_run(self, run_id: int, queue: BoundedClientQueue) -> None:
        self._run_subscribers.setdefault(run_id, set()).add(queue)

    def unsubscribe_run(self, run_id: int, queue: BoundedClientQueue) -> None:
        subscribers = self._run_subscribers.get(run_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            del self._run_subscribers[run_id]

    def subscribe_fleet(self, queue: BoundedClientQueue) -> None:
        self._fleet_subscribers.add(queue)

    def unsubscribe_fleet(self, queue: BoundedClientQueue) -> None:
        self._fleet_subscribers.discard(queue)

    def route_run_event(self, run_id: int, frame: dict[str, Any]) -> list[BoundedClientQueue]:
        """Push `frame` to every subscriber of `run_id`; return the ones
        whose queue was already full (slow consumers the caller must
        close).
        """
        overflowed = []
        for queue in list(self._run_subscribers.get(run_id, ())):
            if not queue.push(frame):
                overflowed.append(queue)
        return overflowed

    def route_fleet_frame(self, frame: dict[str, Any]) -> list[BoundedClientQueue]:
        overflowed = []
        for queue in list(self._fleet_subscribers):
            if not queue.push(frame):
                overflowed.append(queue)
        return overflowed

    def push_lag(self, run_id: int, frame: dict[str, Any]) -> None:
        """`lag` frames (orphan transitions, T343) are pushed the same way
        as an `event` frame — same queue, same overflow handling — just a
        different `kind`.
        """
        self.route_run_event(run_id, frame)


class _RedisPubSubLike(Protocol):
    def pubsub(self) -> Any: ...


async def run_subscriber(redis_client: _RedisPubSubLike, app_state: Any) -> None:
    """Subscribe to `anchor:events` and `anchor:fleet` for the life of the
    process, routing each message through `app_state.ws_hub`. Runs as a
    background task started by `anchor.api.app`'s lifespan and cancelled on
    shutdown; a dropped Redis connection here degrades the console to
    polling and changes nothing about execution.
    """
    hub: Hub = app_state.ws_hub

    while True:
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(EVENTS_CHANNEL, FLEET_TELEMETRY_CHANNEL)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode("utf-8")
                raw = message["data"]
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")

                if channel == EVENTS_CHANNEL:
                    envelope = json.loads(raw)
                    run_id = envelope["data"]["run_id"]
                    # `route_run_event` already sets `queue.overflowed` on
                    # every full queue via `BoundedClientQueue.push`; the
                    # connection handler owning each queue is the one that
                    # notices and closes it (T342), not this function.
                    hub.route_run_event(run_id, envelope)
                elif channel == FLEET_TELEMETRY_CHANNEL:
                    # The heartbeat-tick payload is a display advisory only
                    # (T175/T345); the full worker list a `fleet` frame
                    # must carry (contracts/websocket.md) is assembled by
                    # `anchor.api.ws.fleet`'s own DB-backed refresh loop,
                    # not reconstructed from this single worker's tick. This
                    # message's only job here is to wake that loop early —
                    # handled by `anchor.api.ws.fleet` subscribing to the
                    # same hub-level nudge, not by this function.
                    hub.route_fleet_frame({"kind": "fleet-nudge", "data": json.loads(raw)})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("redis subscriber connection lost; retrying", extra={"error": str(exc)})
            await asyncio.sleep(1.0)
