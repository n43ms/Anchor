"""T562 — the both-modes test.

`/api/authoring/validate` and `/api/authoring/generate` succeed (i.e. are
reachable and behave per their contract) in both deployment modes —
`router` carries both, and `router` is mounted unconditionally regardless
of `ANCHOR_AUTHORING_EXECUTE`, unlike `admin_router`.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from anchor.api.routers import authoring


def _client(*, local_mode: bool) -> TestClient:
    app = FastAPI()
    app.include_router(authoring.router)
    if local_mode:
        app.include_router(authoring.admin_router)
    return TestClient(app)


def test_validate_succeeds_in_demonstration_mode() -> None:
    client = _client(local_mode=False)
    response = client.post(
        "/api/authoring/validate",
        json={"source": "def decide_next_step(ctx):\n    return Done({})\n"},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_succeeds_in_local_mode() -> None:
    client = _client(local_mode=True)
    response = client.post(
        "/api/authoring/validate",
        json={"source": "def decide_next_step(ctx):\n    return Done({})\n"},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_generate_reachable_in_demonstration_mode() -> None:
    client = _client(local_mode=False)
    response = client.post("/api/authoring/generate", json={"description": "x"})
    # "Succeeds" here means the endpoint exists and behaves per its
    # documented contract (honest 503 in this deployment), not that it
    # returns 200 — see anchor.api.routers.authoring.generate_draft.
    assert response.status_code == 503


def test_generate_reachable_in_local_mode() -> None:
    client = _client(local_mode=True)
    response = client.post("/api/authoring/generate", json={"description": "x"})
    assert response.status_code == 503
