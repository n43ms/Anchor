"""T012 — `GET /api/health` fails closed when PostgreSQL is unreachable (I7).

Runnable with **no live PostgreSQL at all**: points `ANCHOR_DATABASE_URL` at
a closed local port, so the connection is refused immediately rather than
timing out, and asserts the API still starts (per `anchor/api/app.py`'s
lifespan — a database outage at boot must not prevent the process from
booting, since `/api/health` is what has to report the outage) and reports
503 with `database_reachable: false`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

UNREACHABLE_DATABASE_URL = "postgresql://anchor:anchor@127.0.0.1:1/anchor"
UNUSED_REDIS_URL = "redis://127.0.0.1:1/0"


@pytest.fixture
def unreachable_db_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANCHOR_DATABASE_URL", UNREACHABLE_DATABASE_URL)
    monkeypatch.setenv("ANCHOR_REDIS_URL", UNUSED_REDIS_URL)
    monkeypatch.setenv("ANCHOR_AUTHORING_EXECUTE", "false")


def test_api_starts_and_reports_503_when_database_is_unreachable(
    unreachable_db_env: None,
) -> None:
    from anchor.api.app import app

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 503
    body = response.json()
    assert body["database_reachable"] is False
    assert body["degraded"] is True
    assert body["worker_count"] == 0
    assert body["schema_revision"] is None


def test_deployment_mode_is_still_reported_even_when_degraded(
    unreachable_db_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANCHOR_AUTHORING_EXECUTE", "true")

    from anchor.api.app import app

    with TestClient(app) as client:
        response = client.get("/api/health")

    # The deployment mode is derived from configuration at process start,
    # never from the database, so it must be present and correct even
    # while every database-backed field reports failure.
    assert response.json()["deployment_mode"] == "local"


def test_repeated_calls_never_report_a_cached_healthy_state(unreachable_db_env: None) -> None:
    from anchor.api.app import app

    with TestClient(app) as client:
        first = client.get("/api/health")
        second = client.get("/api/health")

    assert first.status_code == second.status_code == 503
    assert first.json()["database_reachable"] is False
    assert second.json()["database_reachable"] is False
