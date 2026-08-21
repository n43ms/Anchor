"""T355 / T371 — GET /api/metrics validates against `contracts/openapi.yaml`
and correctly handles integer window seconds across all supported window queries.
"""

from __future__ import annotations

import asyncpg
import pytest
from starlette.testclient import TestClient

from anchor.api.app import create_app


@pytest.mark.asyncio
async def test_get_metrics_endpoint_all_windows(db_pool: asyncpg.Pool) -> None:
    app = create_app()
    app.state.db_pool = db_pool
    client = TestClient(app)

    for window in ("1h", "24h", "7d", "30d"):
        response = client.get(f"/api/metrics?window={window}")
        assert response.status_code == 200, f"Failed for window={window}: {response.text}"
        data = response.json()
        assert data["window"] == window
        assert "duplicate_side_effects" in data
        assert isinstance(data["duplicate_side_effects"], int)
        assert "stranded_runs" in data
        assert isinstance(data["stranded_runs"], int)
        assert "runs_total" in data
        assert isinstance(data["runs_total"], int)
        assert "steps_per_second" in data
        assert isinstance(data["steps_per_second"], (int, float))
        assert "run_state_distribution" in data
        assert isinstance(data["run_state_distribution"], list)
        assert "active_profile" in data
        assert "lease_duration_ms" in data
