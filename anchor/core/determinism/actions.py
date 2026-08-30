"""The three action types `decide_next_step` may return (agent-contract.md).

Anything else is a runtime rejection naming what was actually returned —
the worker loop stalls otherwise, so the check happens as early as possible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    args: dict[str, Any]
    timeout_ms: int | None = None


@dataclass(frozen=True, slots=True)
class ModelCall:
    messages: list[dict[str, Any]]
    model: str | None = None
    timeout_ms: int | None = None


@dataclass(frozen=True, slots=True)
class Done:
    output: dict[str, Any]


Action = ToolCall | ModelCall | Done


def require_action(value: Any) -> Action:
    """Raise a message naming what was returned, if it is not one of the
    three action types (agent-contract.md rule 5).
    """
    if isinstance(value, (ToolCall, ModelCall, Done)):
        return value
    raise TypeError(f"decide_next_step must return ToolCall, ModelCall, or Done — got {value!r}")
