"""Payload models for the 17 event types (data-model.md §11).

Every ● (required) field from the data model is a required field here, so a
malformed payload fails at construction time rather than at replay — the
difference between a loud error now and a silent divergence discovered days
later (plan.md P1.1).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunSubmittedPayload(_Payload):
    agent_type: str
    input: dict[str, Any]
    is_demo: bool
    client_request_key: str | None = None
    chaos_run_id: int | None = None


class RunClaimedPayload(_Payload):
    worker_id: str
    epoch: int
    reason: Literal["initial", "reclaimed_after_lease_expiry"]
    lease_expires_at: str
    previous_worker_id: str | None = None


class ReplayCompletedPayload(_Payload):
    steps_replayed: int
    replay_ms: float
    last_completed_step_index: int
    journal_entries_loaded: int
    nondet_values_loaded: int


class StepStartedPayload(_Payload):
    step_index: int
    action_kind: Literal["tool", "model", "nondet", "done"]


class LlmCalledPayload(_Payload):
    step_index: int
    prompt_hash: str
    response: Any
    model: str
    latency_ms: float
    stubbed: bool


class ToolIntentPayload(_Payload):
    step_index: int
    tool_name: str
    args_canonical: dict[str, Any]
    idempotency_key: str
    args_hash: str
    safety: Literal["retry_safe", "reconcilable", "unsafe"]


class ToolResultPayload(_Payload):
    step_index: int
    tool_name: str
    idempotency_key: str
    result: Any
    latency_ms: float
    resolution: str | None = None


class NondetEntry(_Payload):
    kind: Literal["time", "random", "id"]
    value: Any
    call_ordinal: int


class NondetRecordedPayload(_Payload):
    step_index: int
    entries: list[NondetEntry]


class StepCompletedPayload(_Payload):
    step_index: int
    duration_ms: float
    action_kind: Literal["tool", "model", "nondet", "done"]


class StepSkippedOnReplayPayload(_Payload):
    step_index: int
    idempotency_key: str
    tool_name: str
    original_result_at: str
    original_epoch: int


class StepFailedPayload(_Payload):
    step_index: int
    attempt: int
    error_type: str
    error_message: str
    will_retry: bool
    backoff_ms: int | None = None


class LeaseRenewedPayload(_Payload):
    lease_expires_at: str
    renewal_latency_ms: float
    emit_reason: Literal[
        "first_after_claim", "latency_threshold_exceeded", "final_before_terminal", "always_mode"
    ]


class WorkerFencedPayload(_Payload):
    fenced_worker_id: str
    stale_epoch: int
    current_epoch: int
    detected_by: Literal["renewer", "append"]


class RunCompletedPayload(_Payload):
    output: dict[str, Any]
    total_steps: int
    total_duration_ms: float
    handoff_count: int


class RunFailedPayload(_Payload):
    step_index: int
    attempts: int
    error_type: str
    error_message: str
    dead_lettered: bool


class RunCancelledPayload(_Payload):
    requested_at: str
    step_index: int | None
    cancelled_by: str


class RunNeedsReviewPayload(_Payload):
    step_index: int
    idempotency_key: str
    tool_name: str
    reason: str
    available_resolutions: list[str]


# Maps EventType -> payload model, so a caller can validate construction
# generically (used by append.py and by the payload-model test).
PAYLOAD_MODELS: dict[str, type[_Payload]] = {
    "RUN_SUBMITTED": RunSubmittedPayload,
    "RUN_CLAIMED": RunClaimedPayload,
    "REPLAY_COMPLETED": ReplayCompletedPayload,
    "STEP_STARTED": StepStartedPayload,
    "LLM_CALLED": LlmCalledPayload,
    "TOOL_INTENT": ToolIntentPayload,
    "TOOL_RESULT": ToolResultPayload,
    "NONDET_RECORDED": NondetRecordedPayload,
    "STEP_COMPLETED": StepCompletedPayload,
    "STEP_SKIPPED_ON_REPLAY": StepSkippedOnReplayPayload,
    "STEP_FAILED": StepFailedPayload,
    "LEASE_RENEWED": LeaseRenewedPayload,
    "WORKER_FENCED": WorkerFencedPayload,
    "RUN_COMPLETED": RunCompletedPayload,
    "RUN_FAILED": RunFailedPayload,
    "RUN_CANCELLED": RunCancelledPayload,
    "RUN_NEEDS_REVIEW": RunNeedsReviewPayload,
}
