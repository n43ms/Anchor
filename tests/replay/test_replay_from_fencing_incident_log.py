"""T225 — replaying a log captured from a real fencing incident. A
`RunContext` bug that only surfaces on a log containing `WORKER_FENCED` and
a `reclaimed_after_lease_expiry` `RUN_CLAIMED` — as opposed to every other
fixture's single-owner happy path — is the highest-value risk this phase
introduces into replay, since `_handle_worker_fenced` and the reclaim
branch of `_handle_run_claimed` are new territory for the fold.

**Deviation, noted per T135's precedent**: `tests/fixtures/logs/fencing_incident.json`
is hand-authored to the exact event shape `core.leases.claim.claim_one`
produces (same transaction, same epoch, immediately after `RUN_CLAIMED`) —
no Docker was available in this environment to capture one from a live
`docker compose` run. `tests/fixtures/capture.py` exists so a future capture
can replace this file with a genuinely captured one without changing its
shape.
"""

from __future__ import annotations

from anchor.core.replay.reconstruct import reconstruct
from tests.fixtures import load


def test_fencing_incident_log_replays_without_error_and_resumes_after_the_reclaim() -> None:
    events = load("fencing_incident")
    context = reconstruct(events)

    # Two STEP_COMPLETED events landed — one under each epoch — so replay
    # must resume after the highest, not restart from the reclaimed worker's
    # first step.
    assert context.last_completed_step_index == 1
    assert context.steps_replayed == 2


def test_fencing_incident_log_replays_deterministically() -> None:
    events = load("fencing_incident")
    first = reconstruct(events)
    second = reconstruct(events)
    assert first.last_completed_step_index == second.last_completed_step_index
    assert first.steps_replayed == second.steps_replayed
