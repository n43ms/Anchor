"""T111 — the per-step attempt count equals the number of `STEP_FAILED`
events for that step_index, derived purely from the fold (D-43).

The retry path itself does not exist until phase 6, so the second half of
D-43's claim — "runs.attempts is never read by the retry path" — has no
retry path to test against yet; this test covers what phase 2 owns: the
derivation is correct and sourced from the log, not from any in-memory or
`runs` column counter.
"""

from __future__ import annotations

from datetime import UTC, datetime

from anchor.core.events.models import RunEvent
from anchor.core.events.types import EventType
from anchor.core.replay.reconstruct import reconstruct

_NOW = datetime.now(UTC)


def _event(
    seq: int, event_type: EventType, step_index: int, payload: dict[str, object]
) -> RunEvent:
    return RunEvent(
        run_id=1,
        seq=seq,
        type=event_type,
        payload=payload,
        epoch=1,
        worker_id="worker-a#1",
        step_index=step_index,
        created_at=_NOW,
    )


def test_attempt_count_equals_step_failed_count() -> None:
    events = [
        _event(1, EventType.STEP_STARTED, 2, {"step_index": 2, "action_kind": "tool"}),
        _event(
            2,
            EventType.STEP_FAILED,
            2,
            {
                "step_index": 2,
                "attempt": 1,
                "error_type": "ToolExecutionTimeout",
                "error_message": "timed out",
                "will_retry": True,
                "backoff_ms": 500,
            },
        ),
        _event(3, EventType.STEP_STARTED, 2, {"step_index": 2, "action_kind": "tool"}),
        _event(
            4,
            EventType.STEP_FAILED,
            2,
            {
                "step_index": 2,
                "attempt": 2,
                "error_type": "ToolExecutionTimeout",
                "error_message": "timed out",
                "will_retry": True,
                "backoff_ms": 1000,
            },
        ),
    ]

    context = reconstruct(events)

    assert context.attempts_by_step[2] == 2


def test_a_step_that_never_failed_has_no_entry() -> None:
    events = [_event(1, EventType.STEP_STARTED, 0, {"step_index": 0, "action_kind": "tool"})]
    context = reconstruct(events)
    assert 0 not in context.attempts_by_step
