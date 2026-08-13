"""T238 — `register_tool`'s three refusal conditions (FR-045, FR-046): an
absent or invalid `safety`, `reconcilable` without `reconcile_fn`, and
`retry_safe` with neither `naturally_idempotent` nor `provider_accepts_key`.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from anchor.core.journal.reconcile import NotExecuted
from anchor.runtime.tools.registry import ToolDeclaration, ToolRegistrationError, register


async def _noop(args: dict[str, Any], **_: Any) -> Any:
    return {}


async def _reconcile(args: dict[str, Any], key: str) -> Any:
    return NotExecuted()


def test_invalid_safety_is_refused() -> None:
    decl = ToolDeclaration(name="bad_safety_tool", fn=_noop, safety=cast(Any, "not_a_category"))
    with pytest.raises(ToolRegistrationError, match="safety must be one of"):
        register(decl)


def test_reconcilable_without_reconcile_fn_is_refused() -> None:
    decl = ToolDeclaration(name="missing_reconciler", fn=_noop, safety="reconcilable")
    with pytest.raises(ToolRegistrationError, match="requires reconcile_fn"):
        register(decl)


def test_retry_safe_without_a_stated_reason_is_refused() -> None:
    decl = ToolDeclaration(
        name="unjustified_retry_safe",
        fn=_noop,
        safety="retry_safe",
        naturally_idempotent=False,
        provider_accepts_key=False,
    )
    with pytest.raises(ToolRegistrationError, match="requires naturally_idempotent"):
        register(decl)


def test_retry_safe_with_naturally_idempotent_is_accepted() -> None:
    decl = ToolDeclaration(
        name="ok_retry_safe_a", fn=_noop, safety="retry_safe", naturally_idempotent=True
    )
    register(decl)  # must not raise


def test_retry_safe_with_provider_accepts_key_is_accepted() -> None:
    decl = ToolDeclaration(
        name="ok_retry_safe_b", fn=_noop, safety="retry_safe", provider_accepts_key=True
    )
    register(decl)  # must not raise


def test_reconcilable_with_reconcile_fn_is_accepted() -> None:
    decl = ToolDeclaration(
        name="ok_reconcilable", fn=_noop, safety="reconcilable", reconcile_fn=_reconcile
    )
    register(decl)  # must not raise


def test_unsafe_requires_no_additional_fields() -> None:
    decl = ToolDeclaration(name="ok_unsafe", fn=_noop, safety="unsafe")
    register(decl)  # must not raise
