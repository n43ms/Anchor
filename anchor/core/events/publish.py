"""Post-append publish to the single Redis firehose (plan.md P6.7, D-50, T336).

**Why this lives beside `core.events.append` rather than being threaded
through every caller.** `append` (P1.2, T079) is already, by construction
and by `tests/boundary/test_single_append_path.py`, the *only* place any
code may `INSERT INTO run_events`. Every event this system will ever publish
therefore passes through this one function — reusing that same chokepoint
for publish means the publish path inherits the same "exactly one place"
property the append path was built to have, instead of requiring a
`redis_client` parameter threaded through claim.py, two_phase.py,
policies.py, renew.py, the runs router, and StepContext, all of which call
`append` today without knowing anything about Redis.

The alternative — a process-wide, settable publisher — is the same shape as
`anchor/core/logging.py`'s stdlib logger: exactly one meaningful instance
per process, configured once at boot (`configure_publisher`, called from
`anchor/worker/__main__.py` and `anchor/api/app.py`'s lifespan), read
implicitly thereafter. This is deliberately looser than passing an explicit
dependency, and is acceptable specifically *because* Redis here is
non-authoritative and best-effort (`I7`, FR-058, D-50): no ownership,
dedup, or replay decision ever reads from it, so a global with no publisher
configured (every unit/replay/concurrency test, and any process that never
calls `configure_publisher`) makes every publish a silent no-op rather than
an error.

**Publish timing, stated precisely.** `append` calls `publish_event`
immediately after its `INSERT` statement returns, not after the *caller's*
enclosing transaction commits. For the majority of call sites this is the
same instant — asyncpg auto-commits a bare statement issued outside an
explicit `conn.transaction()` block the moment it returns, so "after the
INSERT returns" already *is* "after commit". Where `append` is one of
several statements inside a caller's own explicit transaction (e.g.
`core.leases.claim.claim_one`'s `RUN_CLAIMED` append, alongside the same
transaction's ownership `UPDATE`), a publish happens a few instructions
before that outer transaction's `COMMIT`, rather than strictly after it —
a deliberate, documented relaxation, not an oversight. It is acceptable
because nothing about correctness depends on the notification: the
partition data-model.md draws between "the log" (authoritative, `I2`) and
"the firehose" (informational, D-50) means the absolute worst case of this
relaxation is a WebSocket client being told about an event whose enclosing
transaction then fails to commit for an unrelated reason (e.g. a
serialization failure) — which would show a client one extra event with no
counterpart in `GET /api/runs/{id}/events`, detectable and harmless, never
a duplicated side effect or a divergent replay.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable
from datetime import datetime
from typing import Any, Protocol

logger = logging.getLogger(__name__)

EVENTS_CHANNEL = "anchor:events"


class _RedisLike(Protocol):
    # A plain `def` returning `Awaitable[Any]`, not `async def`, matching
    # redis-py's own declared shape for `publish` — an `async def` here
    # would make mypy synthesize a `Coroutine[Any, Any, Any]` return type,
    # which redis-py's actual `Awaitable[int]` does not structurally match.
    def publish(self, channel: str, message: str) -> Awaitable[Any]: ...


_publisher: _RedisLike | None = None


def configure_publisher(redis_client: _RedisLike | None) -> None:
    """Set the process-wide publish target. Called once at process startup.
    `None` (the default before this is ever called, and the state every test
    runs in unless it opts in) makes every publish a no-op.
    """
    global _publisher
    _publisher = redis_client


def configured_publisher() -> _RedisLike | None:
    return _publisher


async def publish_event(
    *,
    run_id: int,
    seq: int,
    type: str,
    payload: dict[str, Any],
    epoch: int,
    worker_id: str,
    step_index: int | None,
    created_at: datetime,
) -> None:
    """Publish one `RunEvent` to `anchor:events`, envelope per
    contracts/websocket.md. Best-effort: any failure is logged and swallowed
    rather than allowed to propagate into the durable write path it
    follows — a publish failure must never look like, or cause, a write
    failure (I7 governs the database only; Redis loss degrades display,
    FR-058).
    """
    client = _publisher
    if client is None:
        return

    envelope = {
        "channel": f"run:{run_id}",
        "kind": "event",
        "seq": seq,
        "sent_at": created_at.isoformat(),
        "data": {
            "run_id": run_id,
            "seq": seq,
            "type": type,
            "payload": payload,
            "epoch": epoch,
            "worker_id": worker_id,
            "step_index": step_index,
            "created_at": created_at.isoformat(),
        },
    }
    try:
        await client.publish(EVENTS_CHANNEL, json.dumps(envelope))
    except Exception as exc:
        # Broad by design and narrowly scoped to this one call: the redis
        # client's exception hierarchy isn't part of this module's
        # `_RedisLike` protocol (mirroring `ModelAdapter` /
        # `RegisteredToolLike`'s structural-typing pattern elsewhere), and
        # every failure mode here — a dropped connection, a timeout, a
        # protocol error — has exactly one correct handling: log and
        # continue, matching `worker.registry.heartbeat`'s identical
        # best-effort publish (T175).
        logger.warning(
            "event publish failed; console degrades to polling",
            extra={"run_id": run_id, "seq": seq, "error": str(exc)},
        )
