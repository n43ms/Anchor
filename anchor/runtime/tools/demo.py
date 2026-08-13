"""The three placeholder tools used by `demo_minimal` (plan.md P1.6).

Safety categories are declared here as plain attributes for phase 1 only —
`tool_registry` (the table, the `CHECK`s, and `register_tool`'s refusal
conditions) is phase 5 (P5.5). All three are declared `retry_safe` because
they are naturally idempotent no-ops: re-running "search" or "notify" against
the stub backend has no observable side effect a duplicate could corrupt.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

_LATENCY_S = 0.05


@dataclass(frozen=True, slots=True)
class DemoTool:
    name: str
    safety: str
    fn: Callable[[dict[str, Any]], Awaitable[Any]]


async def _search(args: dict[str, Any]) -> Any:
    await asyncio.sleep(_LATENCY_S)
    return {"results": [f"result-for-{args.get('query', '')}"]}


async def _summarize(args: dict[str, Any]) -> Any:
    await asyncio.sleep(_LATENCY_S)
    return {"summary": f"summary-of-{args.get('text', '')}"}


async def _notify(args: dict[str, Any]) -> Any:
    await asyncio.sleep(_LATENCY_S)
    return {"notified": args.get("recipient", "")}


async def _slow_tool(args: dict[str, Any]) -> Any:
    duration = args.get("duration", 5.0)
    await asyncio.sleep(duration)
    return {"slept": duration}


DEMO_TOOLS: dict[str, DemoTool] = {
    "search": DemoTool(name="search", safety="retry_safe", fn=_search),
    "summarize": DemoTool(name="summarize", safety="retry_safe", fn=_summarize),
    "notify": DemoTool(name="notify", safety="retry_safe", fn=_notify),
    "slow_tool": DemoTool(name="slow_tool", safety="retry_safe", fn=_slow_tool),
}
