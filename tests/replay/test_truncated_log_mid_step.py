"""T106 — a log ending between STEP_STARTED and STEP_COMPLETED folds to a
context whose `last_completed_step_index` excludes the partial step.
"""

from __future__ import annotations

from anchor.core.events.types import EventType
from anchor.core.replay.reconstruct import reconstruct
from tests.fixtures import load


def test_partial_step_excluded_from_last_completed_step_index() -> None:
    events = load("truncated_mid_step")
    # The fixture ends on a TOOL_INTENT for step 1, with no STEP_COMPLETED
    # for it — confirm the fixture itself still says what this test needs.
    assert events[-1].type == EventType.TOOL_INTENT
    assert events[-1].payload["step_index"] == 1

    context = reconstruct(events)

    assert context.last_completed_step_index == 0
    # Step 1's intent was folded in — it is the uncertainty window, not
    # invisible — but it never advanced the resume point.
    assert 1 in context.steps_with_journal_activity
