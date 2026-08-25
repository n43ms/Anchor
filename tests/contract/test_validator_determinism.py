"""T552 — the determinism-rejection test (FR-123, FR-124).

A draft referencing `datetime`, `time`, `random` or `uuid` directly must be
rejected by `anchor.api.authoring.validator.validate`, with the finding
naming the line number and the `ctx` call that replaces it.
"""

from __future__ import annotations

from anchor.api.authoring.validator import validate

_DRAFT = """
import datetime

def decide_next_step(ctx):
    now = datetime.datetime.now()
    return Done({"now": str(now)})
"""


def test_direct_datetime_reference_is_rejected() -> None:
    report = validate(_DRAFT)
    assert report.valid is False
    findings = [f for f in report.findings if f.check == "determinism_imports"]
    assert findings, "expected a determinism_imports finding"
    finding = findings[0]
    assert finding.line == 5 or finding.line == 2
    assert "ctx.now()" in finding.message
    assert str(finding.line) in finding.message


def test_clean_draft_has_no_determinism_finding() -> None:
    draft = """
def decide_next_step(ctx):
    return Done({"ok": True})
"""
    report = validate(draft)
    assert not [f for f in report.findings if f.check == "determinism_imports"]
