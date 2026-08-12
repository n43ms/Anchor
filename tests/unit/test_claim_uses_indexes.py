"""T164 — `EXPLAIN` proves both claim branches, and the global-cap count,
use their intended partial index rather than a sequential scan.

On an empty or near-empty test table the planner may prefer a sequential
scan purely because the table is tiny, regardless of index availability —
that would pass trivially and prove nothing. `enable_seqscan = off` inside
the test's own transaction removes that escape hatch: if the plan still has
nowhere to go but a sequential scan (no matching index exists), `EXPLAIN`
reports it plainly, and if a matching partial index exists the planner uses
it instead. This is what migration 002's docstring claims — this test is
what makes that claim verified rather than argued (plan.md P3.2, T163).
"""

from __future__ import annotations

import asyncpg
import pytest

_PENDING_BRANCH_SQL = """
EXPLAIN (FORMAT TEXT)
SELECT id FROM runs
WHERE status = 'pending'
ORDER BY priority ASC, created_at ASC
LIMIT 1
"""

_EXPIRED_LEASE_BRANCH_SQL = """
EXPLAIN (FORMAT TEXT)
SELECT id FROM runs
WHERE status = 'running' AND lease_expires_at < now()
"""

_GLOBAL_CAP_COUNT_SQL = """
EXPLAIN (FORMAT TEXT)
SELECT count(*) FROM runs WHERE status = 'running'
"""


async def _explain_lines(conn: asyncpg.Connection, sql: str) -> list[str]:
    rows = await conn.fetch(sql)
    return [row["QUERY PLAN"] for row in rows]


@pytest.mark.asyncio
async def test_pending_branch_uses_its_partial_index(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn, conn.transaction():
        await conn.execute("SET LOCAL enable_seqscan = off")
        lines = await _explain_lines(conn, _PENDING_BRANCH_SQL)
    plan = "\n".join(lines)
    assert "Seq Scan" not in plan
    assert "runs_claim_pending_ix" in plan


@pytest.mark.asyncio
async def test_expired_lease_branch_uses_its_partial_index(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn, conn.transaction():
        await conn.execute("SET LOCAL enable_seqscan = off")
        lines = await _explain_lines(conn, _EXPIRED_LEASE_BRANCH_SQL)
    plan = "\n".join(lines)
    assert "Seq Scan" not in plan
    assert "runs_claim_expired_lease_ix" in plan


@pytest.mark.asyncio
async def test_global_cap_count_uses_the_running_partial_index(db_pool: asyncpg.Pool) -> None:
    """The cap count in `core.leases.claim._CLAIM_SQL` matches the exact
    partial predicate of `runs_claim_expired_lease_ix` — migration
    002's documented reason no dedicated cap-count index was added.
    """
    async with db_pool.acquire() as conn, conn.transaction():
        await conn.execute("SET LOCAL enable_seqscan = off")
        lines = await _explain_lines(conn, _GLOBAL_CAP_COUNT_SQL)
    plan = "\n".join(lines)
    assert "Seq Scan" not in plan
    assert "runs_claim_expired_lease_ix" in plan
