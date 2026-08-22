"""T485 — chaos-run parameters are bounded in demonstration mode while the
capability itself remains available (FR-116, §31): cap the parameters, not
the capability.
"""

from __future__ import annotations

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from anchor.api.app import create_app
from anchor.api.routers.chaos import (
    CHAOS_MAX_DURATION_SECONDS_DEMO,
    CHAOS_MAX_WORKER_COUNT_DEMO,
    check_demo_bounds,
)


@pytest.mark.asyncio
async def test_worker_count_over_bound_is_rejected_in_demonstration_mode(
    db_pool: asyncpg.Pool,
) -> None:
    app = create_app()
    app.state.db_pool = db_pool
    app.state.deployment_mode = "demonstration"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/chaos/start",
            json={
                "worker_count": CHAOS_MAX_WORKER_COUNT_DEMO + 1,
                "duration_seconds": 10,
            },
        )
    assert response.status_code == 422
    assert response.json()["error"] == "chaos_bounds_exceeded"


@pytest.mark.asyncio
async def test_duration_over_bound_is_rejected_in_demonstration_mode(db_pool: asyncpg.Pool) -> None:
    app = create_app()
    app.state.db_pool = db_pool
    app.state.deployment_mode = "demonstration"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/chaos/start",
            json={
                "worker_count": 1,
                "duration_seconds": CHAOS_MAX_DURATION_SECONDS_DEMO + 1,
            },
        )
    assert response.status_code == 422
    assert response.json()["error"] == "chaos_bounds_exceeded"


def test_bounds_do_not_apply_in_local_mode() -> None:
    """The capability, not the parameter, is what deployment mode gates
    elsewhere in this system (§31) — local mode raises nothing for a
    worker_count and duration_seconds that demonstration mode would reject.

    Exercises `check_demo_bounds` directly rather than the live endpoint:
    a real `POST /api/chaos/start` call that passed this check would go on
    to spawn a genuine background chaos run, which is not what this test
    is about and would leave an orphaned task running past the test's own
    scope.
    """
    check_demo_bounds(
        "local",
        worker_count=CHAOS_MAX_WORKER_COUNT_DEMO + 5,
        duration_seconds=CHAOS_MAX_DURATION_SECONDS_DEMO + 5,
    )
