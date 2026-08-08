"""The hardcoded three-step agent: search -> summarize -> notify (plan.md P1.6).

Returns exactly one action per invocation and holds no state across calls —
every branch reads `ctx.step_index`, never a variable held in this module,
per the one constraint the whole contract exists to teach
(agent-contract.md).
"""

from __future__ import annotations

from anchor.core.determinism.actions import Action, Done, ToolCall
from anchor.core.determinism.context import StepContext


def decide_next_step(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        return ToolCall("search", {"query": ctx.input.get("query", "")})
    if ctx.step_index == 1:
        return ToolCall("summarize", {"text": ctx.input.get("query", "")})
    if ctx.step_index == 2:
        return ToolCall("notify", {"recipient": ctx.input.get("recipient", "")})
    return Done({"steps": ctx.step_index})
