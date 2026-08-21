"""T380 — CORS middleware is mounted and permits frontend access from browser origins.

Browser requests from the React Vite console (e.g. http://localhost:3000) or other
origins require proper CORS preflight and response headers.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from anchor.api.app import create_app


def test_cors_preflight_options_response() -> None:
    """Preflight OPTIONS requests must return 200 OK with allowed origins,
    methods, and headers so browser cross-origin fetch/XHR calls succeed.
    """
    app = create_app()
    client = TestClient(app)

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "POST" in response.headers.get("access-control-allow-methods", "")
    assert "content-type" in response.headers.get("access-control-allow-headers", "").lower()


def test_cors_get_attaches_allow_origin() -> None:
    """Standard GET requests from a web origin must include Access-Control-Allow-Origin."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/agents", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
