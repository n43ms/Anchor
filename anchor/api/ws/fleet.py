"""`WS /ws/fleet` (plan.md P6.8, T344-T345; contracts/websocket.md).

`hello`, then a `fleet` frame carrying the full worker list on connect,
then another full `fleet` frame on every change — never a delta, so a
client can render directly from the latest frame without accumulating
diffs. "Every change" is driven by the same `anchor:fleet` telemetry tick
`anchor.worker.registry.heartbeat` already publishes (T175); this handler
re-queries the authoritative worker list from PostgreSQL on each tick
rather than trusting the tick's own payload, because `workers.last_seen_at`
in PostgreSQL — not a Redis message — remains the only thing anyone
reasons about for staleness (data-model.md §5).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from anchor.api.serializers.workers import WORKER_COLUMNS, serialize_worker
from anchor.api.ws.backpressure import SLOW_CONSUMER_CLOSE_CODE, BoundedClientQueue
from anchor.api.ws.subscriber import Hub

router = APIRouter()


async def _fetch_fleet_frame(pool: object) -> dict[str, object]:
    async with pool.acquire() as conn:  # type: ignore[attr-defined]
        rows = await conn.fetch(
            f"SELECT {WORKER_COLUMNS} FROM workers ORDER BY label, incarnation DESC"
        )
    workers = [serialize_worker(row).model_dump() for row in rows]
    degraded = any(w["stale"] for w in workers)
    return {"kind": "fleet", "data": {"workers": workers, "degraded": degraded}}


@router.websocket("/ws/fleet")
async def fleet_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    pool = websocket.app.state.db_pool
    hub: Hub = websocket.app.state.ws_hub
    deployment_mode: str = websocket.app.state.deployment_mode

    queue = BoundedClientQueue()
    hub.subscribe_fleet(queue)

    try:
        await websocket.send_json({"kind": "hello", "data": {"deployment_mode": deployment_mode}})
        await websocket.send_json(await _fetch_fleet_frame(pool))

        while True:
            get_task: asyncio.Task[dict[str, object]] = asyncio.ensure_future(queue.get())
            overflow_task: asyncio.Task[bool] = asyncio.ensure_future(queue.overflowed.wait())
            done, pending = await asyncio.wait(
                {get_task, overflow_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

            if overflow_task in done:
                await websocket.send_json(
                    {"kind": "bye", "data": {"reason": "slow_consumer", "last_sent_seq": None}}
                )
                await websocket.close(code=SLOW_CONSUMER_CLOSE_CODE)
                return

            nudge = get_task.result()
            if nudge.get("kind") == "fleet-nudge":
                # The heartbeat tick is only a wake-up; the authoritative
                # frame is re-fetched from PostgreSQL, never assembled from
                # the tick's own payload (see module docstring).
                await websocket.send_json(await _fetch_fleet_frame(pool))
            else:
                # A kill advisory or another already-fully-formed `fleet`
                # frame pushed directly (T345) — sent as-is.
                await websocket.send_json(nudge)
    except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
        pass
    finally:
        hub.unsubscribe_fleet(queue)
