"""Single-file execution runner helper (Phase 10, T630; contracts/agent-contract.md).

Allows running an Anchor agent workflow in a single local call via `anchor.run("agent_name", input={...})`.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

from anchor.core.determinism.actions import Done, ToolCall
from anchor.runtime.agents.registry import resolve as resolve_agent
from anchor.runtime.tools.registry import resolve as resolve_tool


class MockSingleFileContext:
    """A light in-memory StepContext for local single-file runner execution."""

    def __init__(self, run_input: dict[str, Any] | None = None) -> None:
        self.step_index = 0
        self.input = run_input or {}
        self._tool_results: dict[str, Any] = {}
        self.tool_registry: dict[str, Any] = {}

    def has_result(self, name: str) -> bool:
        return name in self._tool_results

    def result_of(self, name: str) -> Any:
        if name not in self._tool_results:
            raise KeyError(f"Tool {name!r} has no result recorded.")
        return self._tool_results[name]

    def model_response_at(self, index: int) -> Any:
        del index
        return None

    def now(self) -> str:
        return "2026-08-26T12:00:00Z"

    def new_id(self) -> str:
        return "single-file-run-uuid-101"


async def execute_run_async(
    agent: str,
    input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Asynchronously execute a registered agent step-by-step in memory."""
    step_fn = resolve_agent(agent)
    if step_fn is None:
        raise ValueError(f"Agent {agent!r} is not registered in agent_registry.")

    ctx = MockSingleFileContext(run_input=input)
    max_steps = 100

    for step in range(max_steps):
        ctx.step_index = step
        action = step_fn(ctx)  # type: ignore[arg-type]

        if isinstance(action, Done):
            return action.output

        if isinstance(action, ToolCall):
            tool_decl = resolve_tool(action.name)
            if tool_decl is None:
                raise ValueError(f"Tool {action.name!r} is not registered in tool_registry.")

            sig = inspect.signature(tool_decl.fn)
            has_single_dict_param = (len(sig.parameters) == 1 and "args" in sig.parameters) or len(
                sig.parameters
            ) == 0

            call_args: tuple[Any, ...]
            call_kwargs: dict[str, Any]

            if has_single_dict_param:
                call_args = (action.args,)
                call_kwargs = {}
            else:
                call_args = ()
                call_kwargs = action.args

            if asyncio.iscoroutinefunction(tool_decl.fn):
                res = await tool_decl.fn(*call_args, **call_kwargs)
            else:
                res = tool_decl.fn(*call_args, **call_kwargs)

            ctx._tool_results[action.name] = res
            continue

        raise TypeError(f"Unexpected action type: {type(action).__name__}")

    raise RuntimeError(f"Agent {agent!r} exceeded maximum step count ({max_steps})")


def run(agent: str, input: dict[str, Any] | None = None) -> dict[str, Any]:
    """Synchronous single-line execution wrapper (`anchor.run("agent_name", input={...})`)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        try:
            import nest_asyncio  # type: ignore[import-not-found]

            nest_asyncio.apply()
        except ImportError:
            pass
        return loop.run_until_complete(execute_run_async(agent, input))

    return asyncio.run(execute_run_async(agent, input))
