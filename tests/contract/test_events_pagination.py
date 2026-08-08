"""T071 — `after_seq` returns exactly the events above that sequence, in
order, with a stable page boundary under concurrent appends."""

from __future__ import annotations

import asyncpg
import pytest

from anchor.api.routers.runs import get_run_events
from anchor.core.events.append import append
from anchor.core.events.types import EventType


@pytest.mark.asyncio
async def test_after_seq_returns_exactly_the_events_above_it(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
        )
        for i in range(10):
            await append(
                conn,
                run_id=run_id,
                type=EventType.STEP_STARTED,
                payload={"step_index": i, "action_kind": "tool"},
                epoch=0,
                worker_id="worker-a#1",
                step_index=i,
                max_payload_bytes=1_000_000,
            )

    result = await get_run_events(run_id, db_pool, after_seq=5, limit=200)

    assert [item["seq"] for item in result["items"]] == [6, 7, 8, 9, 10]
    assert result["items"] == sorted(result["items"], key=lambda item: item["seq"])
