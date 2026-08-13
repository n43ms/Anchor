"""T201 — the single append path checks its own task's cancellation state
before issuing SQL, so a task cancelled by the fencing `TaskGroup` (or any
other cancellation) cannot land a write already in flight (plan.md P4.2).
"""

from __future__ import annotations

import asyncio
import json

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType

MAX_PAYLOAD = 1_000_000


@pytest.mark.asyncio
async def test_append_raises_cancelled_without_issuing_sql_when_already_cancelling(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
            "demo_minimal",
            json.dumps({}),
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_SUBMITTED,
            payload={
                "agent_type": "demo_minimal",
                "input": {},
                "is_demo": True,
                "client_request_key": None,
                "chaos_run_id": None,
            },
            epoch=0,
            worker_id="api",
            max_payload_bytes=MAX_PAYLOAD,
        )
        last_seq_before = await conn.fetchval("SELECT last_seq FROM runs WHERE id = $1", run_id)

    async def _cancel_self_then_append() -> None:
        task = asyncio.current_task()
        assert task is not None
        task.cancel()  # request cancellation of this very task
        async with db_pool.acquire() as conn:
            await append(
                conn,
                run_id=run_id,
                type=EventType.STEP_STARTED,
                payload={"step_index": 0, "action_kind": "tool"},
                epoch=0,
                worker_id="api",
                step_index=0,
                max_payload_bytes=MAX_PAYLOAD,
            )

    task = asyncio.create_task(_cancel_self_then_append())
    with pytest.raises(asyncio.CancelledError):
        await task

    async with db_pool.acquire() as conn:
        last_seq_after = await conn.fetchval("SELECT last_seq FROM runs WHERE id = $1", run_id)

    assert last_seq_after == last_seq_before, (
        "append must not issue its SQL once this task's cancellation has been requested"
    )
