"""`demo_chaos_flaky` — the chaos harness's tool-failure workload (plan.md
P8.3, T502; FR-078).

One step, one journaled coin flip (`ctx.random()`, `I6`-legal), passed to
`flaky_call` as a plain argument. `fail_rate` comes from `ctx.input` so the
harness controls the failure rate per submission rather than this module
hardcoding one (constitution: no timing/behavioural constant belongs
outside its owner's control) — the harness passes its own configured
`tool_failure_rate` (`ChaosParams`, contracts/openapi.yaml) at submission
time.
"""

from __future__ import annotations

from anchor.core.determinism.actions import Action, Done, ToolCall
from anchor.core.determinism.context import StepContext

_DEFAULT_FAIL_RATE = 0.3


def decide_next_step(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        fail_rate = float(ctx.input.get("fail_rate", _DEFAULT_FAIL_RATE))
        should_fail = ctx.random() < fail_rate
        return ToolCall("flaky_call", {"should_fail": should_fail})
    return Done({"flaky_call_completed": True})
