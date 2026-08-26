"""Unit tests for wrap_generator_agent adapter (Phase 10, T624 / T628)."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

from anchor.core.determinism.actions import Action, Done, ToolCall
from anchor.core.determinism.context import StepContext
from anchor.runtime.agents.adapter import wrap_generator_agent


def dummy_reconstruct_context(
    step_index: int,
    tool_results: dict[str, Any] | None = None,
) -> StepContext:
    """Helper to construct a mock StepContext for testing replay fast-forwarding."""

    class MockContext:
        def __init__(self) -> None:
            self.step_index = step_index
            self.input = {"query": "Distributed Systems"}
            self._tool_results = tool_results or {}
            self.tool_registry = {}

        def has_result(self, name: str) -> bool:
            return name in self._tool_results

        def result_of(self, name: str) -> Any:
            if name not in self._tool_results:
                raise KeyError(name)
            return self._tool_results[name]

        def model_response_at(self, index: int) -> Any:
            del index
            return None

        def now(self) -> str:
            return "2026-08-26T12:00:00Z"

        def new_id(self) -> str:
            return "test-uuid-123"

    return MockContext()  # type: ignore[return-value]


@pytest.mark.unit
def test_generator_adapter_fresh_run_step_0() -> None:
    def sample_agent(ctx: StepContext) -> Generator[Action, Any, None]:
        res = yield ToolCall("search_database", {"query": ctx.input["query"]})
        yield Done({"output": res})

    adapted = wrap_generator_agent(sample_agent)
    ctx = dummy_reconstruct_context(step_index=0)

    action = adapted(ctx)
    assert isinstance(action, ToolCall)
    assert action.name == "search_database"
    assert action.args == {"query": "Distributed Systems"}


@pytest.mark.unit
def test_generator_adapter_replay_fast_forward_step_1() -> None:
    execution_trace: list[str] = []

    def sample_agent(ctx: StepContext) -> Generator[Action, Any, None]:
        execution_trace.append("step_0_start")
        search_res = yield ToolCall("search_database", {"query": ctx.input["query"]})
        execution_trace.append(f"step_1_start_with_{search_res['count']}")
        email_res = yield ToolCall("send_email", {"to": "user@example.com"})
        yield Done({"status": "completed", "email": email_res})

    adapted = wrap_generator_agent(sample_agent)
    # Simulate step_index = 1 with search_database result already in PostgreSQL log
    ctx = dummy_reconstruct_context(
        step_index=1,
        tool_results={"search_database": {"count": 42}},
    )

    action = adapted(ctx)

    # Must return the Step 1 ToolCall ("send_email")
    assert isinstance(action, ToolCall)
    assert action.name == "send_email"

    # Verify execution trace: generator was fast-forwarded with search_res = {"count": 42}
    assert execution_trace == ["step_0_start", "step_1_start_with_42"]


@pytest.mark.unit
def test_generator_adapter_final_done() -> None:
    def sample_agent(ctx: StepContext) -> Generator[Action, Any, None]:
        search_res = yield ToolCall("search_database", {"query": ctx.input["query"]})
        email_res = yield ToolCall("send_email", {"to": "user@example.com"})
        yield Done({"status": "completed", "res": search_res, "email": email_res})

    adapted = wrap_generator_agent(sample_agent)
    # Simulate step_index = 2 with both tools finished
    ctx = dummy_reconstruct_context(
        step_index=2,
        tool_results={
            "search_database": {"count": 42},
            "send_email": {"status": "delivered"},
        },
    )

    action = adapted(ctx)

    assert isinstance(action, Done)
    assert action.output == {
        "status": "completed",
        "res": {"count": 42},
        "email": {"status": "delivered"},
    }
