"""T069 — a completed run's log is exactly:
RUN_SUBMITTED (by api) -> per step (STEP_STARTED -> TOOL_INTENT -> TOOL_RESULT
-> STEP_COMPLETED) -> RUN_COMPLETED, all at one epoch by one worker id.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.api.routers.runs import RunSubmission, submit_run
from anchor.core.config.loader import load_runtime_settings
from anchor.runtime.agents import register_all
from anchor.worker.loop import claim_one, execute_run


@pytest.mark.asyncio
async def test_full_event_sequence_for_a_completed_run(db_pool: asyncpg.Pool) -> None:
    register_all()

    run = await submit_run(
        RunSubmission(agent_type="demo_minimal", input={"query": "q", "recipient": "r"}),
        db_pool,
    )

    async with db_pool.acquire() as conn:
        settings = await load_runtime_settings(conn)
        claimed = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=settings.lease_duration_ms,
            max_payload_bytes=settings.max_event_payload_bytes,
        )
        assert claimed is not None
        run_id, agent_type, input_payload, epoch = claimed

        await execute_run(
            conn,
            run_id=run_id,
            agent_type=agent_type,
            input=input_payload,
            epoch=epoch,
            worker_id="worker-a#1",
            settings=settings,
        )

        rows = await conn.fetch(
            "SELECT type, epoch, worker_id FROM run_events WHERE run_id = $1 ORDER BY seq",
            run_id,
        )

    types = [r["type"] for r in rows]
    assert types[0] == "RUN_SUBMITTED"
    assert rows[0]["worker_id"] == "api"
    assert types[1] == "RUN_CLAIMED"

    per_step = types[2:-1]
    expected_step_pattern = ["STEP_STARTED", "TOOL_INTENT", "TOOL_RESULT", "STEP_COMPLETED"] * 3
    assert per_step == expected_step_pattern

    assert types[-1] == "RUN_COMPLETED"

    execution_worker_ids = {r["worker_id"] for r in rows[1:]}
    assert execution_worker_ids == {"worker-a#1"}
    execution_epochs = {r["epoch"] for r in rows[1:]}
    assert execution_epochs == {run.epoch + 1}

    assert run.id == run_id
