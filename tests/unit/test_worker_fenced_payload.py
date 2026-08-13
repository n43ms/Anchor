"""T199 — `WORKER_FENCED` requires both `stale_epoch` and `current_epoch`,
because §22.4 requires the console marker to display both. A payload
missing either fails at construction (P1.1's rule: malformed payloads never
reach replay).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anchor.core.events.payloads import WorkerFencedPayload

_VALID = {
    "fenced_worker_id": "worker-zombie#1",
    "stale_epoch": 2,
    "current_epoch": 3,
    "detected_by": "renewer",
}


def test_valid_payload_constructs() -> None:
    payload = WorkerFencedPayload.model_validate(_VALID)
    assert payload.stale_epoch == 2
    assert payload.current_epoch == 3


@pytest.mark.parametrize(
    "missing_field", ["fenced_worker_id", "stale_epoch", "current_epoch", "detected_by"]
)
def test_missing_required_field_fails_at_construction(missing_field: str) -> None:
    incomplete = {k: v for k, v in _VALID.items() if k != missing_field}
    with pytest.raises(ValidationError):
        WorkerFencedPayload.model_validate(incomplete)


def test_detected_by_is_constrained_to_the_two_known_races() -> None:
    with pytest.raises(ValidationError):
        WorkerFencedPayload.model_validate({**_VALID, "detected_by": "guessed"})
