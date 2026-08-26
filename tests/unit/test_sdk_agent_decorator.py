"""Unit tests for @anchor.agent decorator (Phase 10, T625 / T629)."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

import anchor
from anchor.core.determinism.actions import Action, Done, ToolCall
from anchor.core.determinism.context import StepContext
from anchor.runtime.agents.registry import is_registered, resolve


@pytest.mark.unit
def test_agent_decorator_standard_step_function() -> None:
    @anchor.agent(name="test_standard_agent", description="Standard agent")
    def decide_next_step(ctx: StepContext) -> Action:
        return Done({"input": ctx.input})

    assert is_registered("test_standard_agent")
    resolved_fn = resolve("test_standard_agent")
    assert resolved_fn is not None


@pytest.mark.unit
def test_agent_decorator_generator_function_auto_wrapped() -> None:
    @anchor.agent(name="test_generator_agent")
    def generator_step(ctx: StepContext) -> Generator[Action, Any, None]:
        res = yield ToolCall("db_search", {"query": ctx.input["query"]})
        yield Done({"output": res})

    assert is_registered("test_generator_agent")
    resolved_fn = resolve("test_generator_agent")
    assert resolved_fn is not None

    class MockContext:
        def __init__(self) -> None:
            self.step_index = 0
            self.input = {"query": "test"}
            self.tool_registry: dict[str, Any] = {}

    action = resolved_fn(MockContext())  # type: ignore[arg-type]
    assert isinstance(action, ToolCall)
    assert action.name == "db_search"
