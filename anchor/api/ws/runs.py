"""`WS /ws/runs/{run_id}` (plan.md P6.8, T340-T343; contracts/websocket.md).

`hello` then one `snapshot` on connect, so a client never renders an empty
timeline while waiting for the next event (T340) — the snapshot is exactly
`build_run_timeline`'s output, the same builder `GET /api/runs/{id}/timeline`
uses, so the two can never silently diverge in shape. Then one `event`
frame per appended event, routed through the process-wide `Hub`
(`anchor.api.ws.subscriber`) — this connection's only job is to register a
queue with the hub, drain it, and translate a full queue into the
documented slow-consumer disconnect (T342).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from anchor.api.serializers.timeline import build_run_timeline
from anchor.api.ws.backpressure import SLOW_CONSUMER_CLOSE_CODE, BoundedClientQueue
from anchor.api.ws.subscriber import Hub

router = APIRouter()


@router.websocket("/ws/runs/{run_id}")
async def run_events_ws(websocket: WebSocket, run_id: int) -> None:
    await websocket.accept()

    pool = websocket.app.state.db_pool
    hub: Hub = websocket.app.state.ws_hub
    deployment_mode: str = websocket.app.state.deployment_mode

    async with pool.acquire() as conn:
        timeline = await build_run_timeline(conn, run_id)
        last_seq_row = await conn.fetchval(
            "SELECT max(seq) FROM run_events WHERE run_id = $1", run_id
        )

    if timeline is None:
        await websocket.close(code=1008, reason="run not found")
        return

    last_seq = int(last_seq_row) if last_seq_row is not None else 0

    await websocket.send_json(
        {
            "kind": "hello",
            "data": {"run_id": run_id, "last_seq": last_seq, "deployment_mode": deployment_mode},
        }
    )
    queue = BoundedClientQueue()
    queue.last_sent_seq = last_seq
    hub.subscribe_run(run_id, queue)

    try:
        await websocket.send_json(
            {
                "kind": "hello",
                "data": {
                    "run_id": run_id,
                    "last_seq": last_seq,
                    "deployment_mode": deployment_mode,
                },
            }
        )
        await websocket.send_json({"kind": "snapshot", "data": timeline.model_dump()})

        while True:
            get_task: asyncio.Task[dict[str, object]] = asyncio.ensure_future(queue.get())
            overflow_task: asyncio.Task[bool] = asyncio.ensure_future(queue.overflowed.wait())
            done, pending = await asyncio.wait(
                {get_task, overflow_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

            if overflow_task in done:
                # T342: the client's outbound queue overflowed — it is a
                # slow consumer, not a dropped connection, and the
                # interface must say so rather than silently going quiet.
                await websocket.send_json(
                    {
                        "kind": "bye",
                        "data": {
                            "reason": "slow_consumer",
                            "last_sent_seq": queue.last_sent_seq,
                        },
                    }
                )
                await websocket.close(code=SLOW_CONSUMER_CLOSE_CODE)
                return

            frame = get_task.result()
            await websocket.send_json(frame)
    except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
        pass
    finally:
        hub.unsubscribe_run(run_id, queue)
