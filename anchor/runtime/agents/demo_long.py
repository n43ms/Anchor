"""Multi-step or configurable delay demo agent for testing crash recovery (Phase 2).

Returns up to `steps` (default 20) tool calls, each with `delay_s` (default 2.0s)
so manual crash recovery and reclaim can be observed in real-time.
"""

from __future__ import annotations

from anchor.core.determinism.actions import Action, Done, ToolCall
from anchor.core.determinism.context import StepContext


def decide_next_step(ctx: StepContext) -> Action:
    total_steps = int(ctx.input.get("steps", 20))
    delay_s = float(ctx.input.get("delay_s", 2.0))
    if ctx.step_index < total_steps:
        return ToolCall("search", {"query": f"step_{ctx.step_index}", "delay_s": delay_s})
    return Done({"steps": ctx.step_index})
