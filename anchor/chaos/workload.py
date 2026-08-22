"""Workload generation: the deliberate mix (plan.md P8.2, T495).

Submits runs across every registered demo agent — `demo_minimal`,
`demo_short`, `demo_long`, `demo_unsafe`, plus the two chaos-only agents
(`demo_chaos_flaky`, `demo_chaos_latency`, submitted separately by their own
injection modules) — so the corpus spans every step count, every tool
safety category, and every stubbed-model duration already built into those
agents, rather than inventing a parallel set of chaos-only workloads.
"""

from __future__ import annotations

import asyncio

import httpx

_DEFAULT_AGENT_TYPES = ("demo_minimal", "demo_short", "demo_long", "demo_unsafe")

_SUBMIT_RETRY_DELAY_S = 6.0


async def submit_workload(
    client: httpx.AsyncClient, *, run_count: int, step_mix: dict[str, int] | None
) -> list[int]:
    """Submit `run_count` runs total, distributed across agent types by
    `step_mix`'s relative weights (agent_type -> weight; `None` weighs
    every one of the four base agents equally). Never fewer than `run_count`
    runs and never more than one extra per agent type from integer
    rounding. The chaos harness's two fault-injection agents
    (`demo_chaos_flaky`, `demo_chaos_latency`) are submitted separately by
    their own injection modules, not as part of this baseline mix.
    """
    weights = step_mix or dict.fromkeys(_DEFAULT_AGENT_TYPES, 1)
    total_weight = sum(weights.values())
    run_ids: list[int] = []
    for agent_type, weight in weights.items():
        count = round(run_count * weight / total_weight) if total_weight > 0 else 0
        for _ in range(count):
            run_ids.append(await _submit_one(client, agent_type))
    return run_ids


async def _submit_one(client: httpx.AsyncClient, agent_type: str) -> int:
    while True:
        response = await client.post(
            "/api/runs", json={"agent_type": agent_type, "input": {}, "is_demo": True}
        )
        if response.status_code == 429:
            await asyncio.sleep(_SUBMIT_RETRY_DELAY_S)
            continue
        response.raise_for_status()
        return int(response.json()["id"])
