"""T560 — the route-not-mounted test (FR-112, SC-015).

With `ANCHOR_AUTHORING_EXECUTE` unset, `POST /api/authoring/register`
returns 404, not 401 or 403 — the response must not imply that a
credential would help.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from anchor.api.routers import authoring


def _bare_app() -> FastAPI:
    """A minimal app carrying only the authoring routers, mirroring
    exactly how `anchor.api.app.create_app` conditionally mounts
    `authoring.admin_router` — without booting the real lifespan (a
    database pool, Redis, background tasks), none of which this boundary
    question needs.
    """
    app = FastAPI()
    app.include_router(authoring.router)
    return app


def test_register_returns_404_when_flag_unset() -> None:
    app = _bare_app()
    client = TestClient(app)
    response = client.post(
        "/api/authoring/register",
        json={"source": "def decide_next_step(ctx):\n    return Done({})\n", "agent_type": "x"},
    )
    assert response.status_code == 404


def test_register_is_reachable_once_mounted() -> None:
    app = _bare_app()
    app.include_router(authoring.admin_router)
    client = TestClient(app)
    response = client.post(
        "/api/authoring/register",
        json={
            "source": "def decide_next_step(ctx):\n    return Done({})\n",
            "agent_type": "x_registered_ok",
        },
    )
    assert response.status_code != 404
