"""T478 — invariant 5 detects a log whose replayed final state differs
from a second, mutated copy of itself. `logs_reconstruct_identically` is
the pure comparison `check_replay_determinism` uses against two
independent fetches of the *same* run in real operation (equal by
construction, since `reconstruct` has no I/O); this test supplies a
deliberately mutated second log to prove the comparison can fail.
"""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg
import pytest

from anchor.chaos.invariants import check_replay_determinism, logs_reconstruct_identically
from anchor.core.events.append import append
from anchor.core.events.models import RunEvent
from anchor.core.events.types import EventType


def _event(seq: int, type_: EventType, payload: dict[str, object]) -> RunEvent:
    return RunEvent(
        run_id=1,
        seq=seq,
        type=type_,
        payload=payload,
        epoch=0,
        worker_id="worker-a#1",
        step_index=0,
        created_at=datetime.now(UTC),
    )


def test_identical_logs_match() -> None:
    events = [
        _event(1, EventType.RUN_SUBMITTED, {"agent_type": "demo_minimal", "input": {}}),
        _event(2, EventType.STEP_STARTED, {"step_index": 0, "action_kind": "model"}),
    ]
    assert logs_reconstruct_identically(events, list(events))


def test_mutated_log_is_detected() -> None:
    events_a = [
        _event(1, EventType.RUN_SUBMITTED, {"agent_type": "demo_minimal", "input": {}}),
        _event(
            2,
            EventType.LLM_CALLED,
            {"step_index": 0, "prompt_hash": "h", "response": "A", "model": "stub", "stubbed": True},
        ),
    ]
    events_b = [
        events_a[0],
        _event(
            2,
            EventType.LLM_CALLED,
            {"step_index": 0, "prompt_hash": "h", "response": "B", "model": "stub", "stubbed": True},
        ),
    ]
    assert not logs_reconstruct_identically(events_a, events_b)


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
    )
    return run_id


@pytest.mark.asyncio
async def test_run_all_reconstructs_completed_runs_consistently(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_SUBMITTED,
            payload={"agent_type": "demo_minimal", "input": {}},
            epoch=0,
            worker_id="api",
            max_payload_bytes=1_000_000,
        )
        await conn.execute(
            "UPDATE runs SET status = 'completed', finished_at = now() WHERE id = $1", run_id
        )
        result = await check_replay_determinism(conn, run_ids=[run_id])
        assert result.passed
