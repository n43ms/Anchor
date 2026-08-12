"""T007 — the worker identity `CHECK` and its uniqueness constraint (D-42).

`workers.id` must equal `label || '#' || incarnation`, and `(label,
incarnation)` must be unique — both enforced by the database, not by
application code, so a row inserted by any path still satisfies them.

Requires a live PostgreSQL with migration 001 applied.
"""

from __future__ import annotations

import asyncpg
import pytest


async def _insert_worker(conn: asyncpg.Connection, **overrides: object) -> None:
    defaults = {
        "id": "worker-a#1",
        "label": "worker-a",
        "incarnation": 1,
        "hostname": "test-host",
        "pid": 1,
        "capacity": 10,
        "code_version": "test",
    }
    values = {**defaults, **overrides}
    await conn.execute(
        """
        INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        values["id"],
        values["label"],
        values["incarnation"],
        values["hostname"],
        values["pid"],
        values["capacity"],
        values["code_version"],
    )


@pytest.mark.asyncio
async def test_id_matching_label_and_incarnation_is_accepted(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        await _insert_worker(conn, id="worker-a#1", label="worker-a", incarnation=1)
        row = await conn.fetchrow("SELECT * FROM workers WHERE id = 'worker-a#1'")
    assert row is not None


@pytest.mark.asyncio
async def test_id_mismatched_with_label_and_incarnation_is_rejected(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await _insert_worker(conn, id="worker-a#1", label="worker-a", incarnation=2)


@pytest.mark.asyncio
async def test_same_label_and_incarnation_twice_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        await _insert_worker(conn, id="worker-b#1", label="worker-b", incarnation=1)
        with pytest.raises((asyncpg.exceptions.UniqueViolationError, asyncpg.exceptions.PostgresError)):
            await _insert_worker(conn, id="worker-b#1", label="worker-b", incarnation=1)


@pytest.mark.asyncio
async def test_zero_incarnation_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await _insert_worker(conn, id="worker-c#0", label="worker-c", incarnation=0)


@pytest.mark.asyncio
async def test_invalid_role_is_rejected(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                """
                INSERT INTO workers
                    (id, label, incarnation, hostname, pid, capacity, code_version, role)
                VALUES ('worker-d#1', 'worker-d', 1, 'h', 1, 10, 'test', 'not-a-real-role')
                """
            )
