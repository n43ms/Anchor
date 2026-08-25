"""T557 — the self-recursion test.

A step that can only return itself is rejected, catching the trivial
infinite-run case.
"""

from __future__ import annotations

from anchor.api.authoring.validator import validate


def test_pure_self_recursion_is_rejected() -> None:
    draft = """
def decide_next_step(ctx):
    return decide_next_step(ctx)
"""
    report = validate(draft)
    assert report.valid is False
    findings = [f for f in report.findings if f.check == "unbounded_self_recursion"]
    assert findings
    assert "decide_next_step" in findings[0].message


def test_recursion_with_a_terminal_branch_passes() -> None:
    draft = """
def decide_next_step(ctx):
    if ctx.has_result("search"):
        return Done({"ok": True})
    return ToolCall("search", {})
"""
    report = validate(draft)
    assert not [f for f in report.findings if f.check == "unbounded_self_recursion"]
