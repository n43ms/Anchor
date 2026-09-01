"""`@anchor.agent` decorator implementation (Phase 10, T629; contracts/agent-contract.md).

Allows developers to decorate agent step functions directly.
Automatically detects generator functions (`inspect.isgeneratorfunction`) and wraps them with `wrap_generator_agent` before registering into `agent_registry`.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, cast

from anchor.core.determinism.context import StepContext
from anchor.runtime.agents.adapter import wrap_generator_agent
from anchor.runtime.agents.registry import register as register_agent_in_process

DecideNextStep = Callable[[StepContext], Any]


def agent(
    name: str | None = None,
    *,
    description: str = "",
    contract_version: str = "1.0.0",
    expected_step_count: int | None = None,
    tools_used: tuple[str, ...] = (),
) -> Callable[[DecideNextStep], DecideNextStep]:
    """Decorator to declare an Anchor agent step function."""

    def decorator(fn: DecideNextStep) -> DecideNextStep:
        agent_name = name or fn.__name__
        agent_desc = description or (inspect.getdoc(fn) or "")

        adapted_fn = wrap_generator_agent(fn) if inspect.isgeneratorfunction(fn) else fn
        cast(Any, adapted_fn).__original_fn__ = fn

        register_agent_in_process(
            name=agent_name,
            fn=adapted_fn,
            description=agent_desc,
            contract_version=contract_version,
            expected_step_count=expected_step_count,
            tools_used=tools_used,
        )

        return adapted_fn

    return decorator
