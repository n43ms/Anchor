"""Tool-failure injection (plan.md P8.3, T502; FR-078).

Submits a `demo_chaos_flaky` run through the public API (D-36) whose one
tool call raises with probability `fail_rate` — a real `STEP_FAILED` /
retry / dead-letter sequence when it does, not a simulated count. Recorded
as its own `chaos_events` row (`tool_failure_injected`).
"""

from __future__ import annotations

from typing import Any

import asyncpg
import httpx

from anchor.chaos.recorder import record_chaos_event


async def inject_tool_failure(
    client: httpx.AsyncClient,
    conn: asyncpg.Connection[Any],
    *,
    chaos_run_id: int,
    fail_rate: float,
) -> int:
    """Submit the run and record the injection. Returns the submitted
    run's id.
    """
    response = await client.post(
        "/api/runs",
        json={"agent_type": "demo_chaos_flaky", "input": {"fail_rate": fail_rate}},
    )
    response.raise_for_status()
    run_id = int(response.json()["id"])
    await record_chaos_event(
        conn,
        chaos_run_id=chaos_run_id,
        type="tool_failure_injected",
        affected_run_ids=[run_id],
        params={"fail_rate": fail_rate},
    )
    return run_id
