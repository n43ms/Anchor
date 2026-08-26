"""Unit tests for @anchor.tool decorator and safety validation (Phase 10, T623 / T627)."""

from __future__ import annotations

import pytest

import anchor
from anchor.core.journal.reconcile import NotExecuted
from anchor.runtime.tools.registry import (
    ToolRegistrationError,
    resolve,
)


@pytest.mark.unit
def test_tool_decorator_retry_safe_registration() -> None:
    @anchor.tool(safety="retry_safe", naturally_idempotent=True)
    async def sample_read_tool(query: str) -> dict[str, str]:
        """A sample read-only tool for testing."""
        return {"result": query}

    decl = resolve("sample_read_tool")
    assert decl is not None
    assert decl.name == "sample_read_tool"
    assert decl.safety == "retry_safe"
    assert decl.naturally_idempotent is True
    assert decl.description == "A sample read-only tool for testing."


@pytest.mark.unit
def test_tool_decorator_reconcilable_requires_reconcile_fn() -> None:
    with pytest.raises(ToolRegistrationError, match="requires a reconcile_fn"):

        @anchor.tool(safety="reconcilable")
        async def unlinked_reconcilable_tool(data: str) -> dict[str, str]:
            return {"data": data}


@pytest.mark.unit
def test_tool_decorator_reconcilable_valid_registration() -> None:
    async def dummy_reconcile(args: dict[str, str], idempotency_key: str) -> NotExecuted:
        del args, idempotency_key
        return NotExecuted()

    @anchor.tool(safety="reconcilable", reconcile_fn=dummy_reconcile)
    async def valid_reconcilable_tool(data: str) -> dict[str, str]:
        return {"data": data}

    decl = resolve("valid_reconcilable_tool")
    assert decl is not None
    assert decl.safety == "reconcilable"
    assert decl.has_reconcile_fn is True


@pytest.mark.unit
def test_tool_decorator_retry_safe_requires_idempotency_reason() -> None:
    with pytest.raises(ToolRegistrationError, match="requires naturally_idempotent=True"):

        @anchor.tool(safety="retry_safe")
        async def invalid_retry_safe_tool(data: str) -> dict[str, str]:
            return {"data": data}
