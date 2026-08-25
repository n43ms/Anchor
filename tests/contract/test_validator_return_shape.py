"""T553 — the return-shape test.

Anything a `decide_next_step` returns that is not `ToolCall(...)`,
`ModelCall(...)` or `Done(...)` is rejected with its own specific message.
"""

from __future__ import annotations

from anchor.api.authoring.validator import validate


def test_dict_literal_return_is_rejected() -> None:
    draft = """
def decide_next_step(ctx):
    return {"output": 1}
"""
    report = validate(draft)
    assert report.valid is False
    findings = [f for f in report.findings if f.check == "return_shape"]
    assert findings
    assert "ToolCall" in findings[0].message and "ModelCall" in findings[0].message


def test_bare_return_is_rejected() -> None:
    draft = """
def decide_next_step(ctx):
    return
"""
    report = validate(draft)
    findings = [f for f in report.findings if f.check == "return_shape"]
    assert findings
    assert "returns nothing" in findings[0].message


def test_valid_action_return_passes() -> None:
    draft = """
def decide_next_step(ctx):
    return Done({"ok": True})
"""
    report = validate(draft)
    assert not [f for f in report.findings if f.check == "return_shape"]
