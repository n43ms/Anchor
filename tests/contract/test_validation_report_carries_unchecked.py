"""T564 — the stated-ceiling test (FR-134).

Every `ValidationReport` — including a clean one — carries the `unchecked`
array with the four pre-registration checklist items, so the ceiling
travels with the response rather than depending on a console that might
render `valid: true` alone.
"""

from __future__ import annotations

from anchor.api.authoring.models import UNCHECKED_CHECKLIST
from anchor.api.authoring.validator import validate


def test_clean_draft_still_carries_unchecked() -> None:
    report = validate("def decide_next_step(ctx):\n    return Done({})\n")
    assert report.valid is True
    assert report.unchecked == UNCHECKED_CHECKLIST
    assert len(report.unchecked) == 4


def test_invalid_draft_still_carries_unchecked() -> None:
    report = validate("def decide_next_step(ctx):\n    return {}\n")
    assert report.valid is False
    assert report.unchecked == UNCHECKED_CHECKLIST


def test_to_dict_includes_unchecked_as_a_plain_list() -> None:
    report = validate("def decide_next_step(ctx):\n    return Done({})\n")
    body = report.to_dict()
    assert body["unchecked"] == list(UNCHECKED_CHECKLIST)
