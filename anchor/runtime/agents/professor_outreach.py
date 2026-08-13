"""A mock agent that requires concurrency to actually test the system.

Calls slow_tool to take 5 seconds per step, which exceeds the default 4-second
lease duration, proving that background renewal works.
"""

from __future__ import annotations

from anchor.core.determinism.actions import Action, Done, ToolCall
from anchor.core.determinism.context import StepContext


def decide_next_step(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        return ToolCall("slow_tool", {"duration": 5.0})
    if ctx.step_index == 1:
        return ToolCall("slow_tool", {"duration": 5.0})
    return Done({"status": "outreach_completed"})
