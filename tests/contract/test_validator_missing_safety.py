"""T556 — the missing-safety test.

A registered tool declared with `@tool(...)` and no `safety=` keyword is
rejected — there is no default to fall back to.
"""

from __future__ import annotations

from anchor.api.authoring.validator import validate


def test_tool_decorator_without_safety_kwarg_is_rejected() -> None:
    draft = """
@tool(description="does a thing")
async def my_tool(x: int) -> int:
    return x

def decide_next_step(ctx):
    return Done({"ok": True})
"""
    report = validate(draft)
    assert report.valid is False
    findings = [f for f in report.findings if f.check == "missing_safety_declaration"]
    assert findings
    assert "my_tool" in findings[0].message


def test_tool_decorator_with_safety_kwarg_passes() -> None:
    draft = """
@tool(safety="retry_safe")
async def my_tool(x: int) -> int:
    return x

def decide_next_step(ctx):
    return Done({"ok": True})
"""
    report = validate(draft)
    assert not [f for f in report.findings if f.check == "missing_safety_declaration"]
