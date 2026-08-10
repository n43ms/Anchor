"""T107 — a step calling `ctx.now()` twice replays the two values in the
order they were originally produced. Without the ordinal, the second call
would receive the first value and the divergence would be invisible.
"""

from __future__ import annotations

from datetime import datetime

from anchor.core.determinism.context import StepContext
from anchor.core.replay.reconstruct import reconstruct
from tests.fixtures import load


def test_two_time_calls_replay_in_original_order() -> None:
    events = load("two_nondet_calls_one_step")
    context = reconstruct(events)

    ctx = StepContext(
        run_id=4,
        epoch=1,
        worker_id="worker-a#1",
        step_index=0,
        input={},
        run_context=context,
    )

    first = ctx.now()
    second = ctx.now()

    assert first == datetime.fromisoformat("2026-08-08T13:00:01.101000+00:00")
    assert second == datetime.fromisoformat("2026-08-08T13:00:01.103000+00:00")
    # Reading back recorded values must not re-buffer them for a flush —
    # nothing here should be pending to write.
    assert ctx.nondet_buffer.is_empty()


def test_random_call_replays_interleaved_kind_correctly() -> None:
    """The fixture interleaves one `random` call between the two `time`
    calls. Per-kind ordinal tracking must not be perturbed by that
    interleaving.
    """
    events = load("two_nondet_calls_one_step")
    context = reconstruct(events)

    ctx = StepContext(
        run_id=4, epoch=1, worker_id="worker-a#1", step_index=0, input={}, run_context=context
    )

    ctx.now()
    value = ctx.random()
    ctx.now()

    assert value == 0.42
