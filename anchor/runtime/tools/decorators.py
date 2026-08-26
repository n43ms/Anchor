"""`@anchor.tool` decorator implementation (Phase 10, T627; contracts/tool-contract.md).

Allows developers to decorate functions directly with safety policies (`retry_safe`, `reconcilable`, `unsafe`).
Parses function metadata (docstrings, signatures) and registers the tool declaration in `_REGISTRY`.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from anchor.core.journal.reconcile import ReconcileFn
from anchor.runtime.tools.registry import (
    Safety,
    ToolDeclaration,
    ToolRegistrationError,
)
from anchor.runtime.tools.registry import (
    register as register_tool_in_process,
)

ToolFn = Callable[..., Awaitable[Any]] | Callable[..., Any]


def tool(
    safety: Safety,
    *,
    name: str | None = None,
    naturally_idempotent: bool = False,
    provider_accepts_key: bool = False,
    reconcile_fn: ReconcileFn | None = None,
    description: str | None = None,
) -> Callable[[ToolFn], ToolFn]:
    """Decorator to declare an Anchor tool with an explicit crash-safety policy."""

    def decorator(fn: ToolFn) -> ToolFn:
        tool_name = name or fn.__name__
        tool_desc = description or (inspect.getdoc(fn) or None)

        if safety not in ("retry_safe", "reconcilable", "unsafe"):
            raise ToolRegistrationError(
                f"tool {tool_name!r}: safety must be 'retry_safe', 'reconcilable', or 'unsafe'"
            )

        if safety == "reconcilable" and reconcile_fn is None:
            raise ToolRegistrationError(
                f"tool {tool_name!r}: safety='reconcilable' requires a reconcile_fn"
            )

        if safety == "retry_safe" and not (naturally_idempotent or provider_accepts_key):
            raise ToolRegistrationError(
                f"tool {tool_name!r}: safety='retry_safe' requires naturally_idempotent=True "
                "or provider_accepts_key=True — a tool cannot be declared safe to re-execute "
                "without naming why."
            )

        decl = ToolDeclaration(
            name=tool_name,
            fn=fn,
            safety=safety,
            naturally_idempotent=naturally_idempotent,
            provider_accepts_key=provider_accepts_key,
            reconcile_fn=reconcile_fn,
            description=tool_desc,
        )

        register_tool_in_process(decl)
        return fn

    return decorator
