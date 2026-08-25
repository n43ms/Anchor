"""T555 — the unregistered-tool test.

A `ToolCall` naming a tool absent from the live registry fails in the
editor, rather than at step 3 of a live run.
"""

from __future__ import annotations

from anchor.api.authoring.validator import validate
from anchor.runtime.tools.demo import DEMO_TOOLS
from anchor.runtime.tools.registry import as_tool_registry, register


def _ensure_demo_tools_registered() -> None:
    live = as_tool_registry()
    for name, decl in DEMO_TOOLS.items():
        if name not in live:
            register(decl)


def test_unregistered_tool_name_is_rejected() -> None:
    _ensure_demo_tools_registered()
    draft = """
def decide_next_step(ctx):
    return ToolCall("this_tool_does_not_exist", {})
"""
    report = validate(draft)
    assert report.valid is False
    findings = [f for f in report.findings if f.check == "unregistered_tool"]
    assert findings
    assert "this_tool_does_not_exist" in findings[0].message


def test_registered_tool_name_passes() -> None:
    _ensure_demo_tools_registered()
    draft = """
def decide_next_step(ctx):
    return ToolCall("web_search", {"query": "x"})
"""
    report = validate(draft)
    assert not [f for f in report.findings if f.check == "unregistered_tool"]
