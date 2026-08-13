"""The structural shape `core.journal` needs from a registered tool.

A `Protocol`, not an import of `anchor.runtime.tools.registry.ToolDeclaration`
— `core/` must not depend on `runtime/` (constitution, Repository Structure
and Module Boundaries: "runtime/ ... the payload, not the system"). The same
pattern already exists for `ModelAdapter` in `core.determinism.context`; this
is its sibling for tools.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol

from anchor.core.journal.reconcile import ReconcileFn


class RegisteredToolLike(Protocol):
    """Read-only by design: every member is a `@property`, not a plain
    annotation, because `ToolDeclaration` (the real implementation) is a
    frozen dataclass. A plain-annotation `Protocol` member implies a
    *settable* attribute, which a frozen dataclass structurally is not —
    `mypy --strict` rejects the match otherwise, correctly, since nothing
    in `core.journal` ever assigns through this interface.
    """

    @property
    def name(self) -> str: ...
    @property
    def safety(self) -> Literal["retry_safe", "reconcilable", "unsafe"]: ...
    @property
    def naturally_idempotent(self) -> bool: ...
    @property
    def provider_accepts_key(self) -> bool: ...
    @property
    def reconcile_fn(self) -> ReconcileFn | None: ...
    @property
    def fn(self) -> Callable[..., Awaitable[Any]]: ...
