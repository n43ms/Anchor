"""Single-file execution runner helper (Phase 10, T630; contracts/agent-contract.md).

Allows running an Anchor agent workflow via `anchor.run("agent_name", input={...})`.
If a live Anchor cluster is reachable (http://localhost:8000 or ANCHOR_API_URL), submits the run to PostgreSQL
so real Docker workers race to claim it and stream real-time 3D telemetry to the Console (http://localhost:3000).
Falls back to local in-memory execution if no cluster server is reachable.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from anchor.core.determinism.actions import Done, ModelCall, ToolCall
from anchor.runtime.agents.registry import resolve as resolve_agent
from anchor.runtime.tools.registry import resolve as resolve_tool


class MockSingleFileContext:
    """A light in-memory StepContext for local offline runner execution."""

    def __init__(self, run_input: dict[str, Any] | None = None) -> None:
        self.step_index = 0
        self.input = run_input or {}
        self._tool_results: dict[str, Any] = {}
        self._step_tool_results: dict[int, Any] = {}
        self._model_responses: dict[int, Any] = {}
        self._last_model_response: dict[str, Any] | None = None
        self.tool_registry: dict[str, Any] = {}

    def has_result(self, name: str) -> bool:
        return name in self._tool_results

    def result_of(self, name: str, step_index: int | None = None) -> Any:
        if step_index is not None and step_index in self._step_tool_results:
            return self._step_tool_results[step_index]
        if name not in self._tool_results:
            raise KeyError(f"Tool {name!r} has no result recorded.")
        return self._tool_results[name]

    def model_response_at(self, index: int) -> Any:
        if index in self._model_responses:
            return self._model_responses[index]
        return getattr(self, "_last_model_response", None)

    def now(self) -> str:
        return "2026-08-26T12:00:00Z"

    def new_id(self) -> str:
        return "single-file-run-uuid-101"


def _check_api_health(api_url: str) -> bool:
    """Check if live Anchor API server is reachable."""
    health_url = f"{api_url.rstrip('/')}/api/health"
    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return bool(resp.status == 200)
    except Exception:
        return False


def _register_agent_with_api(api_url: str, agent: str, step_fn: Any) -> bool:
    """Attempts to register local script's source text with live cluster via POST /api/authoring/register."""
    register_url = f"{api_url.rstrip('/')}/api/authoring/register"
    try:
        target_fn = getattr(step_fn, "__original_fn__", step_fn)
        module = inspect.getmodule(target_fn)
        if module is not None and hasattr(module, "__file__"):
            source = inspect.getsource(module)
        else:
            source = inspect.getsource(target_fn)

        payload_bytes = json.dumps({"source": source, "agent_type": agent}).encode("utf-8")
        req = urllib.request.Request(
            register_url,
            data=payload_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return bool(resp.status == 201)
    except Exception as e:
        print(f"[Anchor Client] Registration details: {e}")
        if hasattr(e, "read"):
            with contextlib.suppress(Exception):
                print("Registration response body:", e.read().decode("utf-8"))
        return False


def _submit_api_run(api_url: str, agent: str, input_payload: dict[str, Any]) -> int:
    """POST /api/runs to register job in PostgreSQL for live worker fleet."""
    submit_url = f"{api_url.rstrip('/')}/api/runs"
    payload_bytes = json.dumps({"agent_type": agent, "input": input_payload}).encode("utf-8")
    req = urllib.request.Request(
        submit_url,
        data=payload_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return int(data["id"])


def _poll_api_run_result(
    api_url: str, run_id: int, max_wait_seconds: float = 60.0
) -> dict[str, Any]:
    """Poll GET /api/runs/{id} until terminal state and return output."""
    get_url = f"{api_url.rstrip('/')}/api/runs/{run_id}"
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        req = urllib.request.Request(get_url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                status = data.get("status")
                if status in ("completed", "failed", "cancelled", "needs_review"):
                    events_url = f"{api_url.rstrip('/')}/api/runs/{run_id}/events"
                    try:
                        req_ev = urllib.request.Request(events_url, method="GET")
                        with urllib.request.urlopen(req_ev, timeout=5.0) as resp_ev:
                            ev_data = json.loads(resp_ev.read().decode("utf-8"))
                            items = ev_data.get("items", ev_data.get("events", []))
                            for ev in reversed(items):
                                if ev.get("type") in ("RUN_COMPLETED", "RUN_FAILED"):
                                    out = ev.get("payload", {}).get("output")
                                    if isinstance(out, dict):
                                        return out
                    except Exception:
                        pass
                    return {"status": status, "output": data.get("output")}
        except Exception:
            pass
        time.sleep(0.5)

    raise TimeoutError(f"Run {run_id} did not reach terminal state within {max_wait_seconds}s")


async def execute_run_async(
    agent: str,
    input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute run: routes to live cluster if reachable, else runs locally in-memory."""
    api_url = os.getenv("ANCHOR_API_URL", "http://localhost:8000").strip()
    input_payload = input or {}
    step_fn = resolve_agent(agent)

    # Check if live cluster API is available
    if await asyncio.to_thread(_check_api_health, api_url):
        if step_fn is not None:
            await asyncio.to_thread(_register_agent_with_api, api_url, agent, step_fn)
        try:
            run_id = await asyncio.to_thread(_submit_api_run, api_url, agent, input_payload)
            print(
                f"[Anchor Client] Submitted Run #{run_id} to live cluster ({api_url}). Streaming to console..."
            )
            return await asyncio.to_thread(_poll_api_run_result, api_url, run_id)
        except Exception as e:
            print(f"[Anchor Client] API submission warning: {e}. Falling back to local runner...")

    # Fallback to local in-memory step execution
    if step_fn is None:
        raise ValueError(f"Agent {agent!r} is not registered in agent_registry.")

    ctx = MockSingleFileContext(run_input=input_payload)
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
            ctx._step_tool_results[step] = res
            continue

        if isinstance(action, ModelCall):
            from anchor.runtime.tools.model import get_model_adapter

            adapter = get_model_adapter()
            resp = await adapter.complete(action.messages, action.model)
            model_dict = {"text": resp.text, "model": resp.model, "stubbed": resp.stubbed}
            ctx._last_model_response = model_dict
            ctx._model_responses[step] = model_dict
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
