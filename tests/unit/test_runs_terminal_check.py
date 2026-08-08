"""T006 — "illegal states unrepresentable" on `runs` (D-23).

A terminal run cannot hold a lease; a `running` run must hold one. Both are
plain PostgreSQL `CHECK` constraints (SQLSTATE 23514, `CheckViolationError`)
— not one of anchor's own AN0xx codes — so these tests catch asyncpg's
constraint-violation type directly rather than a translated anchor error.

Requires a live PostgreSQL with migration 001 applied.
"""

from __future__ import annotations

import asyncpg
import pytest


async def _insert_worker(conn: asyncpg.Connection, worker_id: str = "test-worker#1") -> str:
    label, incarnation = worker_id.split("#")
    await conn.execute(
        """
        INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version)
        VALUES ($1, $2, $3, 'test-host', 1, 10, 'test')
        ON CONFLICT (id) DO NOTHING
        """,
        worker_id,
        label,
        int(incarnation),
    )
    return worker_id


@pytest.mark.asyncio
async def test_completed_run_cannot_hold_owner_or_lease(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        worker_id = await _insert_worker(conn)
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                """
                INSERT INTO runs (agent_type, status, owner_worker_id, lease_expires_at, finished_at)
                VALUES ('demo_minimal', 'completed', $1, now() + interval '1 minute', now())
                """,
                worker_id,
            )


@pytest.mark.asyncio
async def test_completed_run_without_finished_at_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                "INSERT INTO runs (agent_type, status) VALUES ('demo_minimal', 'completed')"
            )


@pytest.mark.asyncio
async def test_completed_run_with_no_lease_and_finished_at_set_is_accepted(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        run_id = await conn.fetchval(
            "INSERT INTO runs (agent_type, status, finished_at) "
            "VALUES ('demo_minimal', 'completed', now()) RETURNING id"
        )
    assert run_id is not None


@pytest.mark.asyncio
async def test_running_run_without_owner_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                "INSERT INTO runs (agent_type, status) VALUES ('demo_minimal', 'running')"
            )


@pytest.mark.asyncio
async def test_running_run_with_owner_and_lease_is_accepted(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        worker_id = await _insert_worker(conn)
        run_id = await conn.fetchval(
            """
            INSERT INTO runs (agent_type, status, owner_worker_id, lease_expires_at, epoch)
            VALUES ('demo_minimal', 'running', $1, now() + interval '1 minute', 1)
            RETURNING id
            """,
            worker_id,
        )
    assert run_id is not None
