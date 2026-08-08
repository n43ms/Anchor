"""T068 — each of the 17 event types constructs from a valid payload and
fails at construction on a missing required field."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anchor.core.events.payloads import PAYLOAD_MODELS
from anchor.core.events.types import EventType

VALID_PAYLOADS: dict[str, dict] = {
    "RUN_SUBMITTED": {"agent_type": "demo_minimal", "input": {}, "is_demo": False},
    "RUN_CLAIMED": {
        "worker_id": "worker-a#1",
        "epoch": 1,
        "reason": "initial",
        "lease_expires_at": "2026-01-01T00:00:00Z",
    },
    "REPLAY_COMPLETED": {
        "steps_replayed": 0,
        "replay_ms": 1.0,
        "last_completed_step_index": -1,
        "journal_entries_loaded": 0,
        "nondet_values_loaded": 0,
    },
    "STEP_STARTED": {"step_index": 0, "action_kind": "tool"},
    "LLM_CALLED": {
        "step_index": 0,
        "prompt_hash": "h",
        "response": "r",
        "model": "stub-v1",
        "latency_ms": 1.0,
        "stubbed": True,
    },
    "TOOL_INTENT": {
        "step_index": 0,
        "tool_name": "search",
        "args_canonical": {},
        "idempotency_key": "k",
        "args_hash": "h",
        "safety": "retry_safe",
    },
    "TOOL_RESULT": {
        "step_index": 0,
        "tool_name": "search",
        "idempotency_key": "k",
        "result": {},
        "latency_ms": 1.0,
    },
    "NONDET_RECORDED": {
        "step_index": 0,
        "entries": [{"kind": "time", "value": "x", "call_ordinal": 0}],
    },
    "STEP_COMPLETED": {"step_index": 0, "duration_ms": 1.0, "action_kind": "tool"},
    "STEP_SKIPPED_ON_REPLAY": {
        "step_index": 0,
        "idempotency_key": "k",
        "tool_name": "search",
        "original_result_at": "2026-01-01T00:00:00Z",
        "original_epoch": 1,
    },
    "STEP_FAILED": {
        "step_index": 0,
        "attempt": 1,
        "error_type": "ValueError",
        "error_message": "m",
        "will_retry": True,
    },
    "LEASE_RENEWED": {
        "lease_expires_at": "2026-01-01T00:00:00Z",
        "renewal_latency_ms": 1.0,
        "emit_reason": "first_after_claim",
    },
    "WORKER_FENCED": {
        "fenced_worker_id": "worker-a#1",
        "stale_epoch": 1,
        "current_epoch": 2,
        "detected_by": "append",
    },
    "RUN_COMPLETED": {
        "output": {},
        "total_steps": 3,
        "total_duration_ms": 1.0,
        "handoff_count": 0,
    },
    "RUN_FAILED": {
        "step_index": 0,
        "attempts": 1,
        "error_type": "ValueError",
        "error_message": "m",
        "dead_lettered": True,
    },
    "RUN_CANCELLED": {
        "requested_at": "2026-01-01T00:00:00Z",
        "step_index": 0,
        "cancelled_by": "api",
    },
    "RUN_NEEDS_REVIEW": {
        "step_index": 0,
        "idempotency_key": "k",
        "tool_name": "search",
        "reason": "r",
        "available_resolutions": [],
    },
}


def test_every_event_type_has_a_payload_model() -> None:
    assert set(PAYLOAD_MODELS.keys()) == {t.value for t in EventType}


@pytest.mark.parametrize("event_type", list(EventType))
def test_valid_payload_constructs(event_type: EventType) -> None:
    model = PAYLOAD_MODELS[event_type.value]
    model.model_validate(VALID_PAYLOADS[event_type.value])


@pytest.mark.parametrize("event_type", list(EventType))
def test_missing_required_field_fails_at_construction(event_type: EventType) -> None:
    model = PAYLOAD_MODELS[event_type.value]
    valid = VALID_PAYLOADS[event_type.value]
    if not valid:
        pytest.skip(f"{event_type} has no required fields to omit")
    incomplete = dict(valid)
    incomplete.pop(next(iter(incomplete)))
    with pytest.raises(ValidationError):
        model.model_validate(incomplete)
