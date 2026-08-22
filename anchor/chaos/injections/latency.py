"""Latency injection (plan.md P8.3, T500; FR-077).

Submits a `demo_chaos_latency` run through the public API (D-36) whose one
tool call sleeps for `latency_ms` — a real, observable stretch of that
run's step latency, not a simulated number written into the report.
Recorded as its own `chaos_events` row (`latency_injected`) since, unlike a
kill, there is no existing endpoint whose job is to record this kind of
injection.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import httpx

from anchor.chaos.recorder import record_chaos_event


async def inject_latency(
    client: httpx.AsyncClient,
    conn: asyncpg.Connection[Any],
    *,
    chaos_run_id: int,
    latency_ms: int,
) -> int:
    """Submit the run and record the injection. Returns the submitted
    run's id.
    """
    response = await client.post(
        "/api/runs",
        json={"agent_type": "demo_chaos_latency", "input": {"latency_ms": latency_ms}},
    )
    response.raise_for_status()
    run_id = int(response.json()["id"])
    await record_chaos_event(
        conn,
        chaos_run_id=chaos_run_id,
        type="latency_injected",
        affected_run_ids=[run_id],
        params={"latency_ms": latency_ms},
    )
    return run_id
