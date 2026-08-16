"""T279 — a `needs_review` run satisfies the terminal-state-style `CHECK`
from migration 001 (`runs_terminal_holds_no_lease`): it cannot hold a lease
or an owner, and it cannot block reclaim while looking healthy, because
nothing is claiming a run nobody owns.
"""

from __future__ import annotations

import asyncpg
import pytest


@pytest.mark.asyncio
async def test_needs_review_cannot_hold_owner_or_lease(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_short') RETURNING id"
        )
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                "UPDATE runs SET status = 'needs_review', "
                "owner_worker_id = 'worker-a#1', lease_expires_at = now() + interval '1 minute' "
                "WHERE id = $1",
                run_id,
            )


@pytest.mark.asyncio
async def test_needs_review_requires_finished_at(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_short') RETURNING id"
        )
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute("UPDATE runs SET status = 'needs_review' WHERE id = $1", run_id)


@pytest.mark.asyncio
async def test_needs_review_transition_matching_halt_needs_review_is_valid(
    db_pool: asyncpg.Pool,
) -> None:
    """The exact column set `core.journal.policies.halt_needs_review` writes
    — leaseless, ownerless, `finished_at` set — is the one the CHECK
    accepts, so a real halt never trips the constraint it must satisfy.
    """
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, status, owner_worker_id, lease_expires_at) "
            "VALUES ('demo_short', 'running', 'worker-a#1', now() + interval '1 minute') "
            "RETURNING id"
        )
        await conn.execute(
            "UPDATE runs SET status = 'needs_review', owner_worker_id = NULL, "
            "lease_expires_at = NULL, finished_at = now() WHERE id = $1",
            run_id,
        )
        row = await conn.fetchrow(
            "SELECT status, owner_worker_id, lease_expires_at FROM runs WHERE id = $1", run_id
        )
    assert row is not None
    assert row["status"] == "needs_review"
    assert row["owner_worker_id"] is None
    assert row["lease_expires_at"] is None
