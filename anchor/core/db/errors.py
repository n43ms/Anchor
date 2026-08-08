"""The typed error hierarchy and the SQLSTATE-to-error map (FR-018).

Each error is a distinct type so a caller can never catch one intending
another — in particular, `LeaseFencedError` must never be caught by a
generic retry handler, because retrying a fenced write is exactly the
split-brain the epoch exists to prevent.

SQLSTATE allocation (data-model.md §10):
    AN001  fenced write               -> LeaseFencedError
    AN002  configuration relationship -> ConfigAssertionError
    AN003  immutable row              -> ImmutableRecordError
    AN004  result overwrite           -> ResultOverwriteError
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class AnchorError(Exception):
    """Base for every typed error this package raises."""


class LeaseFencedError(AnchorError):
    """Raised when the database rejects a write from a stale epoch (AN001).

    The only correct response is to discard in-memory state, write nothing
    further through the affected run, retry nothing, and return to the idle
    pool (FR-019). It must never be treated as a generic, retryable failure.
    """

    def __init__(self, run_id: int, stale_epoch: int, current_epoch: int | None = None) -> None:
        self.run_id = run_id
        self.stale_epoch = stale_epoch
        self.current_epoch = current_epoch
        message = f"run {run_id}: epoch {stale_epoch} is stale"
        if current_epoch is not None:
            message += f" (current: {current_epoch})"
        super().__init__(message)


class ConfigAssertionError(AnchorError):
    """Raised when a configuration change or startup value violates the
    lease/renewal/timeout relationship (AN002). Names the violated
    relationship and every offending value — never a bare "invalid
    configuration".
    """

    def __init__(self, relationship: str, offending_values: dict[str, Any]) -> None:
        self.relationship = relationship
        self.offending_values = offending_values
        rendered = ", ".join(f"{k}={v}" for k, v in offending_values.items())
        super().__init__(f"configuration assertion failed: {relationship} ({rendered})")


class ImmutableRecordError(AnchorError):
    """Raised on any UPDATE or DELETE against an append-only or immutable
    table (AN003): run_events, tool_journal, chaos_events, chaos_reports.
    """

    def __init__(self, table: str, operation: str) -> None:
        self.table = table
        self.operation = operation
        super().__init__(f"{operation} rejected: {table} is immutable")


class ResultOverwriteError(AnchorError):
    """Raised when an UPDATE attempts to overwrite a non-null
    `tool_journal.result` with a different value (AN004). A result, once
    recorded, is final.
    """

    def __init__(self, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(f"result already recorded for key {idempotency_key}")


class PayloadTooLargeError(AnchorError):
    """Raised when an event payload exceeds `max_event_payload_bytes` (D-51).

    The payload is never truncated to fit: a truncated payload would replay
    to different messages than the original execution, which is replay
    divergence introduced by a size optimization.
    """

    def __init__(self, event_type: str, measured_bytes: int, ceiling_bytes: int) -> None:
        self.event_type = event_type
        self.measured_bytes = measured_bytes
        self.ceiling_bytes = ceiling_bytes
        super().__init__(
            f"{event_type} payload is {measured_bytes} bytes, exceeding the "
            f"{ceiling_bytes}-byte ceiling"
        )


# SQLSTATE codes raised by anchor's own triggers and functions (never PostgreSQL's
# own built-in codes, which are left to propagate as generic database errors).
SQLSTATE_FENCED_WRITE = "AN001"
SQLSTATE_CONFIG_ASSERTION = "AN002"
SQLSTATE_IMMUTABLE_RECORD = "AN003"
SQLSTATE_RESULT_OVERWRITE = "AN004"

KNOWN_SQLSTATES = frozenset(
    {
        SQLSTATE_FENCED_WRITE,
        SQLSTATE_CONFIG_ASSERTION,
        SQLSTATE_IMMUTABLE_RECORD,
        SQLSTATE_RESULT_OVERWRITE,
    }
)


class _PostgresErrorLike(Protocol):
    """Structural type for asyncpg.PostgresError, so this module never has
    to import asyncpg directly — it only needs `.sqlstate` and `.detail`.
    """

    sqlstate: str | None
    detail: str | None


def translate_postgres_error(exc: _PostgresErrorLike) -> AnchorError | None:
    """Translate a raised-by-anchor SQLSTATE into its typed error.

    Every anchor trigger and function that raises AN001-AN004 does so with
    `USING ERRCODE = '<code>', DETAIL = '<json>'` (see migration 001, 003),
    where the JSON payload's keys match the corresponding error's
    constructor arguments exactly. This is what makes the mapping total and
    mechanical rather than a per-call-site parsing exercise.

    Returns `None` for any SQLSTATE this module does not own — callers
    should let those propagate as the driver's own exception type, per
    FR-018's "raise the generic database error for anything unmapped rather
    than swallowing it."
    """
    code = exc.sqlstate
    if code not in KNOWN_SQLSTATES:
        return None

    payload: dict[str, Any] = json.loads(exc.detail) if exc.detail else {}

    if code == SQLSTATE_FENCED_WRITE:
        return LeaseFencedError(
            run_id=payload["run_id"],
            stale_epoch=payload["stale_epoch"],
            current_epoch=payload.get("current_epoch"),
        )
    if code == SQLSTATE_CONFIG_ASSERTION:
        return ConfigAssertionError(
            relationship=payload["relationship"],
            offending_values=payload.get("offending_values", {}),
        )
    if code == SQLSTATE_IMMUTABLE_RECORD:
        return ImmutableRecordError(table=payload["table"], operation=payload["operation"])
    if code == SQLSTATE_RESULT_OVERWRITE:
        return ResultOverwriteError(idempotency_key=payload["idempotency_key"])

    # Unreachable: every member of KNOWN_SQLSTATES is handled above. Kept as
    # an explicit else rather than falling through, so a fifth code added to
    # KNOWN_SQLSTATES without a branch here fails loudly in the round-trip
    # test instead of silently returning None.
    raise AssertionError(f"SQLSTATE {code} is in KNOWN_SQLSTATES but has no translation branch")
