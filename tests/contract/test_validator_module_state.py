"""T554 — the module-state test.

Globals mutated across invocations are rejected — state held outside `ctx`
does not survive a handoff and is the most likely authoring mistake.
"""

from __future__ import annotations

from anchor.api.authoring.validator import validate


def test_global_statement_is_rejected() -> None:
    draft = """
_seen = []

def decide_next_step(ctx):
    global _seen
    _seen.append(ctx.step_index)
    return Done({"seen": _seen})
"""
    report = validate(draft)
    assert report.valid is False
    findings = [f for f in report.findings if f.check == "module_level_mutable_state"]
    assert findings
    assert "_seen" in findings[0].message


def test_in_place_mutation_of_module_level_container_is_rejected() -> None:
    draft = """
_cache = {}

def decide_next_step(ctx):
    _cache.update({"x": 1})
    return Done({"cache": _cache})
"""
    report = validate(draft)
    findings = [f for f in report.findings if f.check == "module_level_mutable_state"]
    assert findings
    assert "_cache" in findings[0].message


def test_ctx_only_state_passes() -> None:
    draft = """
def decide_next_step(ctx):
    if not ctx.has_result("search"):
        return ToolCall("search", {})
    return Done({"ok": True})
"""
    report = validate(draft)
    assert not [f for f in report.findings if f.check == "module_level_mutable_state"]
