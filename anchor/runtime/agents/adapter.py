"""Generator adapter for `yield` syntactic sugar (Phase 10, T628; contracts/agent-contract.md).

Adapts a `yield` generator function into Anchor's `decide_next_step(ctx: StepContext) -> Action` signature.

Under the hood:
1. Instantiates the generator with `ctx`.
2. Fast-forwards through all previously completed steps by retrieving their cached results from `ctx` (PostgreSQL log) and injecting them via `gen.send(cached_result)`.
3. Yields the current incomplete Action to Anchor's worker loop.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

from anchor.core.determinism.actions import Action, Done, ModelCall, ToolCall
from anchor.core.determinism.context import StepContext

GeneratorAgent = Callable[[StepContext], Generator[Action, Any, Any]]
DecideNextStep = Callable[[StepContext], Action]


def wrap_generator_agent(gen_fn: GeneratorAgent) -> DecideNextStep:
    """Converts a `yield` generator agent into Anchor's `decide_next_step(ctx)` signature."""

    def decide_next_step(ctx: StepContext) -> Action:
        gen = gen_fn(ctx)

        try:
            action = gen.send(None)
        except StopIteration as e:
            if isinstance(e.value, Action):
                return e.value
            return Done(e.value if isinstance(e.value, dict) else {})

        # Fast-forward generator through all completed steps stored in PostgreSQL
        for step_idx in range(ctx.step_index):
            cached_result: Any = None

            if isinstance(action, ToolCall):
                cached_result = ctx.result_of(action.name)
            elif isinstance(action, ModelCall):
                model_fn = getattr(ctx, "model_response_at", None)
                if callable(model_fn):
                    cached_result = model_fn(step_idx)

            try:
                action = gen.send(cached_result)
            except StopIteration as e:
                if isinstance(e.value, Action):
                    return e.value
                return Done(e.value if isinstance(e.value, dict) else {})

        return action

    return decide_next_step
