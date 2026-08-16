"""T109 — the phase-2 hard gate's integration test.

A worker completes step 0, then "dies" (no further renewal — simulated by
letting the short lease it claimed under simply elapse). A different
worker reclaims: `RUN_CLAIMED` carries `reason: reclaimed_after_lease_expiry`
and an epoch one higher; `REPLAY_COMPLETED.steps_replayed` matches the one
step that had completed; and execution resumes at
`last_completed_step_index + 1`, never at step 0.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping

import asyncpg
import pytest

import anchor.runtime.agents  # noqa: F401 - registers "demo_minimal" as a side effect
from anchor.core.config.profiles import ConfigProfile, profile_settings
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one
from anchor.core.replay.load import load_run_events
from anchor.worker.loop import execute_run

MAX_PAYLOAD = 1_000_000


async def _insert_run(
    conn: asyncpg.Connection, agent_type: str, input_payload: Mapping[str, object]
) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
        agent_type,
        json.dumps(input_payload),
    )
    return run_id


@pytest.mark.asyncio
async def test_different_worker_resumes_after_reclaim(db_pool: asyncpg.Pool) -> None:
    input_payload = {"query": "durable execution", "recipient": "ops@example.com"}

    async with db_pool.acquire() as conn:
        from anchor.runtime.tools.demo import register_demo_tools

        await register_demo_tools(conn, code_version="dev")
        run_id = await _insert_run(conn, "demo_minimal", input_payload)
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_SUBMITTED,
            payload={
                "agent_type": "demo_minimal",
                "input": input_payload,
                "is_demo": True,
                "client_request_key": None,
                "chaos_run_id": None,
            },
            epoch=0,
            worker_id="api",
            max_payload_bytes=MAX_PAYLOAD,
        )

        await conn.execute(
            """
            INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version)
            VALUES
                ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev'),
                ('worker-b#1', 'worker-b', 1, 'test', 2, 10, 'dev')
            ON CONFLICT DO NOTHING
            """
        )
        claimed = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=50,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert claimed is not None
        epoch_a = claimed.epoch
        assert epoch_a == 1

        # worker-a#1 completes exactly step 0 ("search"), then dies — no
        # STEP_STARTED for step 1 is ever appended by it.
        await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_STARTED,
            payload={"step_index": 0, "action_kind": "tool"},
            epoch=epoch_a,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=MAX_PAYLOAD,
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.TOOL_INTENT,
            payload={
                "step_index": 0,
                "tool_name": "search",
                "args_canonical": {"query": input_payload["query"]},
                "idempotency_key": "key-search-0",
                "args_hash": "hash-search-0",
                "safety": "retry_safe",
            },
            epoch=epoch_a,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=MAX_PAYLOAD,
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.TOOL_RESULT,
            payload={
                "step_index": 0,
                "tool_name": "search",
                "idempotency_key": "key-search-0",
                "result": {"results": [f"result-for-{input_payload['query']}"]},
                "latency_ms": 5.0,
                "resolution": None,
            },
            epoch=epoch_a,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=MAX_PAYLOAD,
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_COMPLETED,
            payload={"step_index": 0, "duration_ms": 5.0, "action_kind": "tool"},
            epoch=epoch_a,
            worker_id="worker-a#1",
            step_index=0,
            max_payload_bytes=MAX_PAYLOAD,
        )

        # Let the 50ms lease elapse — modelling a hard kill, not a
        # cooperative shutdown: no further renewal ever happens.
        await asyncio.sleep(0.2)

        claimed_2 = await claim_one(
            conn,
            worker_id="worker-b#1",
            lease_duration_ms=5_000,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert claimed_2 is not None
        run_id_2 = claimed_2.run_id
        agent_type = claimed_2.agent_type
        resumed_input = claimed_2.input
        epoch_b = claimed_2.epoch
        assert run_id_2 == run_id
        assert epoch_b == 2

        pre_execution_events = await load_run_events(conn, run_id)
        reclaim_events = [e for e in pre_execution_events if e.type == EventType.RUN_CLAIMED]
        assert len(reclaim_events) == 2
        assert reclaim_events[1].payload["reason"] == "reclaimed_after_lease_expiry"
        assert reclaim_events[1].payload["worker_id"] == "worker-b#1"
        assert reclaim_events[1].payload["previous_worker_id"] == "worker-a#1"
        assert reclaim_events[1].epoch == 2

        settings = profile_settings(ConfigProfile.DEMO)
        await execute_run(
            conn,
            run_id=run_id,
            agent_type=agent_type,
            input=resumed_input,
            epoch=epoch_b,
            worker_id="worker-b#1",
            settings=settings,
        )

        final_events = await load_run_events(conn, run_id)

        replay_completed = [e for e in final_events if e.type == EventType.REPLAY_COMPLETED]
        assert len(replay_completed) == 1
        assert replay_completed[0].payload["steps_replayed"] == 1
        assert replay_completed[0].payload["last_completed_step_index"] == 0

        step_started_indices = [
            e.payload["step_index"] for e in final_events if e.type == EventType.STEP_STARTED
        ]
        assert step_started_indices.count(0) == 1, "step 0 must never be re-executed"
        assert 1 in step_started_indices
        assert 2 in step_started_indices

        run_row = await conn.fetchrow(
            "SELECT status, owner_worker_id, lease_expires_at FROM runs WHERE id = $1", run_id
        )
        assert run_row is not None
        assert run_row["status"] == "completed"
        assert run_row["owner_worker_id"] is None
        assert run_row["lease_expires_at"] is None
