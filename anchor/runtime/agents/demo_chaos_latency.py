"""`demo_chaos_latency` — the chaos harness's latency-injection workload
(plan.md P8.3, T500; FR-077).

One step, one tool call, whose duration is exactly `ctx.input["latency_ms"]`
— set by the harness's `latency_injection_ms` parameter (`ChaosParams`,
contracts/openapi.yaml) at submission time, never hardcoded here.
"""

from __future__ import annotations

from anchor.core.determinism.actions import Action, Done, ToolCall
from anchor.core.determinism.context import StepContext

_DEFAULT_LATENCY_MS = 2000


def decide_next_step(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        latency_ms = ctx.input.get("latency_ms", _DEFAULT_LATENCY_MS)
        return ToolCall("slow_call", {"latency_ms": latency_ms})
    return Done({"slow_call_completed": True})
