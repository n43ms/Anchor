"""T119 — `LEASE_RENEWED` contributes nothing to the reconstructed state.

Licenses D-48's conditional emission: if renewal affected replay, skipping
its emission on most renewals (the default policy) would make replay
depend on *which* renewals happened to be logged, which is exactly the
kind of hidden dependency Principle III forbids.
"""

from __future__ import annotations

from datetime import UTC, datetime

from anchor.core.events.models import RunEvent
from anchor.core.events.types import EventType
from anchor.core.replay.reconstruct import canonical_state_hash, reconstruct

_NOW = datetime.now(UTC)


def _step_completed(seq: int, step_index: int) -> RunEvent:
    return RunEvent(
        run_id=1,
        seq=seq,
        type=EventType.STEP_COMPLETED,
        payload={"step_index": step_index, "duration_ms": 1.0, "action_kind": "tool"},
        epoch=1,
        worker_id="worker-a#1",
        step_index=step_index,
        created_at=_NOW,
    )


def _lease_renewed(seq: int) -> RunEvent:
    return RunEvent(
        run_id=1,
        seq=seq,
        type=EventType.LEASE_RENEWED,
        payload={
            "lease_expires_at": _NOW.isoformat(),
            "renewal_latency_ms": 3.0,
            "emit_reason": "first_after_claim",
        },
        epoch=1,
        worker_id="worker-a#1",
        step_index=None,
        created_at=_NOW,
    )


def test_lease_renewed_present_or_absent_yields_identical_state() -> None:
    without_renewal = [_step_completed(1, 0)]
    with_renewal = [_lease_renewed(1), _step_completed(2, 0), _lease_renewed(3)]

    context_without = reconstruct(without_renewal)
    context_with = reconstruct(with_renewal)

    assert canonical_state_hash(context_without) == canonical_state_hash(context_with)
