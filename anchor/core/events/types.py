"""The 17 event types (data-model.md §11), as a `StrEnum`.

Must match `ops/migrations/versions/001_foundation.py`'s `_EVENT_TYPES`
exactly (FR-025) — `tests/unit/test_event_types_match_migration.py` asserts
the two lists cannot drift.
"""

from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    RUN_SUBMITTED = "RUN_SUBMITTED"
    RUN_CLAIMED = "RUN_CLAIMED"
    REPLAY_COMPLETED = "REPLAY_COMPLETED"
    STEP_STARTED = "STEP_STARTED"
    LLM_CALLED = "LLM_CALLED"
    TOOL_INTENT = "TOOL_INTENT"
    TOOL_RESULT = "TOOL_RESULT"
    NONDET_RECORDED = "NONDET_RECORDED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_SKIPPED_ON_REPLAY = "STEP_SKIPPED_ON_REPLAY"
    STEP_FAILED = "STEP_FAILED"
    LEASE_RENEWED = "LEASE_RENEWED"
    WORKER_FENCED = "WORKER_FENCED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"
    RUN_CANCELLED = "RUN_CANCELLED"
    RUN_NEEDS_REVIEW = "RUN_NEEDS_REVIEW"
