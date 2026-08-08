"""T066 — a payload above `max_event_payload_bytes` raises `PayloadTooLargeError`
carrying the event type and the measured size, and nothing is truncated (D-51)."""

from __future__ import annotations

import asyncpg
import pytest

from anchor.core.db.errors import PayloadTooLargeError
from anchor.core.events.append import append
from anchor.core.events.types import EventType


@pytest.mark.asyncio
async def test_oversized_payload_raises_and_is_not_truncated(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
        )

        oversized_result = {"data": "x" * 100}

        with pytest.raises(PayloadTooLargeError) as exc_info:
            await append(
                conn,
                run_id=run_id,
                type=EventType.TOOL_RESULT,
                payload={
                    "step_index": 0,
                    "tool_name": "search",
                    "idempotency_key": "k",
                    "result": oversized_result,
                    "latency_ms": 1.0,
                },
                epoch=0,
                worker_id="worker-a#1",
                step_index=0,
                max_payload_bytes=50,
            )

        assert exc_info.value.event_type == "TOOL_RESULT"
        assert exc_info.value.measured_bytes > 50
        assert exc_info.value.ceiling_bytes == 50

        count = await conn.fetchval("SELECT count(*) FROM run_events WHERE run_id = $1", run_id)
        assert count == 0
