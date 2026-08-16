"""The bounded per-client outbound queue (plan.md P6.8, T342; FR-074,
contracts/websocket.md).

`QUEUE_DEPTH` is a module constant, not a `runtime_config` key, for the
same reason `anchor.core.config.live.POLL_INTERVAL_S` is one: it governs
how much display-only WebSocket fan-out memory one slow browser tab can
accumulate server-side, not anything the epoch/lease/fencing machinery
reads. 256 frames comfortably absorbs a burst of a fast agent's per-step
frames between two client reads without letting a genuinely stalled tab
grow unbounded (constitution, Concurrency Rules: "backpressure is
explicit... unbounded growth is a bug, not a scaling characteristic").
"""

from __future__ import annotations

import asyncio
from typing import Any

QUEUE_DEPTH = 256

# WebSocket close code for "going away due to policy violation" — reused
# here, per contracts/websocket.md, for the slow-consumer disconnect.
SLOW_CONSUMER_CLOSE_CODE = 1013


class BoundedClientQueue:
    """One connected client's outbound frame queue. `push` never blocks the
    publisher: a full queue means this client is a slow consumer, and the
    caller (`anchor.api.ws.runs`/`fleet`) closes the connection with
    `SLOW_CONSUMER_CLOSE_CODE` and a `bye` frame rather than letting the
    queue, and therefore server memory, grow without bound.
    """

    def __init__(self, *, maxsize: int = QUEUE_DEPTH) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self.last_sent_seq: int | None = None
        # Set by `push` the instant the queue is found full — the
        # connection handler awaits this alongside `get()` so a slow
        # consumer is detected even while nothing new is being pulled off
        # the queue (asyncio.Queue has no other way to signal "someone
        # tried to add to me and couldn't").
        self.overflowed = asyncio.Event()

    def push(self, frame: dict[str, Any]) -> bool:
        """Enqueue `frame` without blocking. Returns `False` (and enqueues
        nothing, and sets `overflowed`) if the queue is already full — the
        caller's cue to close this client as a slow consumer.
        """
        try:
            self._queue.put_nowait(frame)
            return True
        except asyncio.QueueFull:
            self.overflowed.set()
            return False

    async def get(self) -> dict[str, Any]:
        frame = await self._queue.get()
        seq = frame.get("seq")
        if isinstance(seq, int):
            self.last_sent_seq = seq
        return frame
