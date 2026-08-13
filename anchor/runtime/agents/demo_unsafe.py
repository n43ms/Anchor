"""`demo_unsafe` — reaches the `needs_review` path deliberately (plan.md
P5.8, T285).

Deliberately short: its only purpose is to put an `unsafe`-declared tool
call (`send_email`) reachable within a handful of steps, so that a crash
injected between that call's `TOOL_INTENT` and its `TOOL_RESULT` — by the
chaos harness's `uncertainty_crash_injected` (Principle V), or by a
worker kill triggered from the console — demonstrably halts the run to
`needs_review` rather than guessing whether the message was sent.
"""

from __future__ import annotations

from anchor.core.determinism.actions import Action, Done, ModelCall, ToolCall
from anchor.core.determinism.context import StepContext


def decide_next_step(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        return ModelCall([{"role": "user", "content": "Draft an incident notification."}])
    if ctx.step_index == 1:
        return ToolCall("web_search", {"query": ctx.input.get("query", "incident status")})
    if ctx.step_index == 2:
        return ToolCall(
            "send_email",
            {
                "recipient": ctx.input.get("recipient", "oncall@example.invalid"),
                "subject": "Incident notification",
            },
        )
    return Done({"notified": True})
