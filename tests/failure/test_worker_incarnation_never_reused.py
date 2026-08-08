"""T010 — a restarted worker gets a new incarnation, never a reused id (D-42,
FR-129).

Hostname and pid are reused by the platform across a container restart, so
this test deliberately registers twice **from the same process** (identical
real hostname and pid, since `register()` reads them via `socket.gethostname()`
/ `os.getpid()`) — which is exactly the scenario D-42 exists for: identity
must not be derivable from hostname+pid alone.

Requires a live PostgreSQL with migration 001 applied.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.worker.registry.register import mark_stopped, register


@pytest.mark.asyncio
async def test_restart_after_graceful_stop_gets_a_higher_incarnation(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        first = await register(conn, label_pool=["test-restart"], capacity=10, code_version="v1")
        await mark_stopped(conn, first.identity.id)

        second = await register(conn, label_pool=["test-restart"], capacity=10, code_version="v2")

    assert second.identity.label == first.identity.label == "test-restart"
    assert second.identity.incarnation == first.identity.incarnation + 1
    assert second.identity.id != first.identity.id
    # The defining property: same real hostname and pid (same test process),
    # yet a distinct id — proving identity does not alias to (hostname, pid).
    assert second.hostname == first.hostname
    assert second.pid == first.pid


@pytest.mark.asyncio
async def test_the_prior_row_survives_unmodified_after_a_restart(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        first = await register(conn, label_pool=["test-restart-2"], capacity=10, code_version="v1")
        await mark_stopped(conn, first.identity.id)
        first_started_at = await conn.fetchval(
            "SELECT started_at FROM workers WHERE id = $1", first.identity.id
        )

        await register(conn, label_pool=["test-restart-2"], capacity=10, code_version="v2")

        # The old row must still exist, with its own started_at untouched —
        # a new incarnation inserts a new row rather than updating the old
        # one in place, so the fleet's history stays append-only.
        replayed_first = await conn.fetchrow(
            "SELECT * FROM workers WHERE id = $1", first.identity.id
        )

    assert replayed_first is not None
    assert replayed_first["started_at"] == first_started_at
    assert replayed_first["stopped_at"] is not None
    assert replayed_first["code_version"] == "v1"


@pytest.mark.asyncio
async def test_three_restarts_produce_three_distinct_ids_and_rows(
    db_pool: asyncpg.Pool,
) -> None:
    ids: list[str] = []
    async with db_pool.acquire() as conn:
        for i in range(3):
            registered = await register(
                conn, label_pool=["test-restart-3"], capacity=10, code_version=f"v{i}"
            )
            ids.append(registered.identity.id)
            await mark_stopped(conn, registered.identity.id)

        rows = await conn.fetch(
            "SELECT id FROM workers WHERE label = 'test-restart-3' ORDER BY incarnation"
        )

    assert ids == ["test-restart-3#1", "test-restart-3#2", "test-restart-3#3"]
    assert [r["id"] for r in rows] == ids
