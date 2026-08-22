"""T474 — invariant 1 detects a planted duplicate `TOOL_RESULT` and
reports zero on a clean corpus (plan.md P8.4, FR-082).
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.chaos.invariants import check_no_duplicate_effects, duplicate_effect_count
from anchor.core.events.append import append
from anchor.core.events.types import EventType


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
    )
    return run_id


async def _append_tool_result(conn: asyncpg.Connection, run_id: int, idempotency_key: str) -> None:
    await append(
        conn,
        run_id=run_id,
        type=EventType.TOOL_RESULT,
        payload={
            "step_index": 0,
            "tool_name": "search",
            "idempotency_key": idempotency_key,
            "result": {"ok": True},
            "latency_ms": 1.0,
        },
        epoch=0,
        worker_id="worker-a#1",
        step_index=0,
        max_payload_bytes=1_000_000,
    )


@pytest.mark.asyncio
async def test_clean_corpus_reports_zero(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await _append_tool_result(conn, run_id, f"key-{run_id}-a")
        await _append_tool_result(conn, run_id, f"key-{run_id}-b")

        result = await check_no_duplicate_effects(conn)
        assert result.passed
        count = await duplicate_effect_count(conn)
        assert count == 0


@pytest.mark.asyncio
async def test_planted_duplicate_is_detected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        key = f"key-{run_id}-dup"
        # Two TOOL_RESULT events for the same idempotency key — unreachable
        # via the two-phase journal (tool_journal's PRIMARY KEY forbids a
        # second intent row), planted directly through the append path to
        # prove the assertion would catch it if the journal's own guard
        # were ever bypassed.
        await _append_tool_result(conn, run_id, key)
        await _append_tool_result(conn, run_id, key)

        result = await check_no_duplicate_effects(conn)
        assert not result.passed
        assert result.violations == [
            {"invariant": "no_duplicate_effects", "idempotency_key": key, "result_count": 2}
        ]
        count = await duplicate_effect_count(conn)
        assert count == 1
