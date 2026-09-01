"""Extensive multi-agent fault injection test suite for Two-Phase Journaling."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest

import anchor
from anchor.core.determinism.context import StepContext
from anchor.runtime.agents.adapter import wrap_generator_agent
from anchor.runtime.tools.registry import ToolRegistrationError


class DummyContext:
    def __init__(self, run_input: dict[str, Any] | None = None) -> None:
        self.step_index = 0
        self.input = run_input or {}
        self._tool_results: dict[str, Any] = {
            "search_tool": {"items": ["item1", "item2"]},
            "fetch_tool": {"details": "data"},
        }
        self.tool_registry: dict[str, Any] = {}

    def has_result(self, tool_name: str, args: dict[str, Any] | None = None) -> bool:
        return tool_name in self._tool_results

    def result_of(self, tool_name: str, args: dict[str, Any] | None = None) -> Any:
        return self._tool_results[tool_name]

    def model_response_at(self, index: int) -> Any:
        del index
        return None

    def now(self) -> datetime:
        return datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)

    def new_id(self) -> str:
        return "test-journal-uuid-999"


@pytest.mark.unit
def test_generator_agent_journal_fast_forwarding() -> None:
    """Tests that wrap_generator_agent fast-forwards through completed tool results."""

    def my_multi_step_agent(ctx: anchor.StepContext) -> Any:
        val1 = yield anchor.ToolCall("search_tool", {"query": "test"})
        val2 = yield anchor.ToolCall("fetch_tool", {"id": "123"})
        yield anchor.Done({"val1": val1, "val2": val2})

    adapted = wrap_generator_agent(my_multi_step_agent)
    ctx = DummyContext(run_input={"query": "test"})
    ctx.step_index = 2

    action = adapted(cast(StepContext, ctx))
    assert isinstance(action, anchor.Done)
    assert action.output == {
        "val1": {"items": ["item1", "item2"]},
        "val2": {"details": "data"},
    }


@pytest.mark.unit
def test_two_phase_journaling_retry_safety() -> None:
    """Verifies safety policy assertions across distinct tool safety classes."""

    # Valid retry_safe tool
    @anchor.tool(safety="retry_safe", naturally_idempotent=True)
    async def valid_tool(args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True}

    assert valid_tool is not None

    # Invalid retry_safe tool (missing reason) raises ToolRegistrationError
    with pytest.raises(ToolRegistrationError):

        @anchor.tool(safety="retry_safe")
        async def invalid_tool(args: dict[str, Any]) -> dict[str, Any]:
            return {"ok": False}
