"""T477 — invariant 4 detects a run left non-terminal past the bound
(plan.md P8.4). `needs_review` counts as terminal here (data-model.md
§1) — only `pending`/`running` past the bound are stranded.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.chaos.invariants import check_terminal_reachability, stranded_run_count


async def _insert_worker(conn: asyncpg.Connection, worker_id: str) -> None:
    await conn.execute(
        "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
        "VALUES ($1, $2, 1, 'test-host', 1, 10, 'test')",
        worker_id,
        worker_id.split("#")[0],
    )


async def _insert_run(conn: asyncpg.Connection, *, status: str, age_seconds: float) -> int:
    if status == "running":
        worker_id = f"w-{age_seconds}#1"
        await _insert_worker(conn, worker_id)
        run_id = await conn.fetchval(
            "INSERT INTO runs (agent_type, status, created_at, owner_worker_id, lease_expires_at) "
            "VALUES ('demo_minimal', 'running', now() - ($1 * interval '1 second'), "
            "$2, now() + interval '1 hour') RETURNING id",
            age_seconds,
            worker_id,
        )
        return int(run_id)

    run_id = await conn.fetchval(
        "INSERT INTO runs (agent_type, status, created_at) "
        "VALUES ('demo_minimal', $1, now() - ($2 * interval '1 second')) RETURNING id",
        status,
        age_seconds,
    )
    if status in ("completed", "failed", "cancelled", "needs_review"):
        await conn.execute("UPDATE runs SET finished_at = now() WHERE id = $1", run_id)
    return int(run_id)


@pytest.mark.asyncio
async def test_completed_run_within_bound_passes(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn, status="completed", age_seconds=100)
        result = await check_terminal_reachability(conn, run_ids=[run_id], bound_seconds=10)
        assert result.passed
        assert await stranded_run_count(conn, run_ids=[run_id]) == 0


@pytest.mark.asyncio
async def test_needs_review_within_bound_passes(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn, status="needs_review", age_seconds=100)
        result = await check_terminal_reachability(conn, run_ids=[run_id], bound_seconds=10)
        assert result.passed


@pytest.mark.asyncio
async def test_stuck_running_past_bound_is_detected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn, status="running", age_seconds=100)
        result = await check_terminal_reachability(conn, run_ids=[run_id], bound_seconds=10)
        assert not result.passed
        assert result.violations == [
            {"invariant": "terminal_reachability", "run_id": run_id, "status": "running"}
        ]
        assert await stranded_run_count(conn, run_ids=[run_id]) == 1


@pytest.mark.asyncio
async def test_running_within_bound_is_not_yet_stranded(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn, status="running", age_seconds=1)
        result = await check_terminal_reachability(conn, run_ids=[run_id], bound_seconds=10)
        assert result.passed
