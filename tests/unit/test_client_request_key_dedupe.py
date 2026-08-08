"""T067 — a second submission with the same `client_request_key` returns the
existing run rather than creating a second (FR-002).

Calls the route handler directly rather than through an HTTP client: the
frozen dependency set (plan.md Technical Context, D-04) does not include an
HTTP test client, and FastAPI's routing itself is not what this test is
about — the dedupe transaction in `anchor.api.routers.runs` is.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.api.routers.runs import RunSubmission, submit_run
from anchor.runtime.agents import register_all


@pytest.mark.asyncio
async def test_duplicate_client_request_key_returns_existing_run(db_pool: asyncpg.Pool) -> None:
    register_all()
    submission = RunSubmission(agent_type="demo_minimal", input={}, client_request_key="dedupe-1")

    first = await submit_run(submission, db_pool)
    second = await submit_run(submission, db_pool)

    assert first.id == second.id

    async with db_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM runs WHERE client_request_key = 'dedupe-1'"
        )
    assert count == 1
