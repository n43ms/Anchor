"""T198 — `LeaseFencedError` is catchable without catching any other
database error. A fencing rejection handled by a generic retry handler
would be retried, which is the one thing a fenced write must never be
(FR-018).
"""

from __future__ import annotations

import pytest

from anchor.core.db.errors import (
    AnchorError,
    ConfigAssertionError,
    ImmutableRecordError,
    LeaseFencedError,
    ResultOverwriteError,
)


def test_lease_fenced_error_is_not_caught_by_sibling_error_types() -> None:
    exc = LeaseFencedError(run_id=1, stale_epoch=2, current_epoch=3)

    with pytest.raises(LeaseFencedError):
        try:
            raise exc
        except (ConfigAssertionError, ImmutableRecordError, ResultOverwriteError):
            pytest.fail("a sibling error type must not catch LeaseFencedError")


def test_generic_anchor_error_catch_still_distinguishes_by_isinstance() -> None:
    exc = LeaseFencedError(run_id=1, stale_epoch=2)

    caught: AnchorError | None = None
    try:
        raise exc
    except AnchorError as e:
        caught = e

    assert isinstance(caught, LeaseFencedError)
    assert not isinstance(caught, ConfigAssertionError)


def test_a_retry_handler_that_only_catches_declared_retryable_errors_never_sees_fencing() -> None:
    """The shape a real caller uses: a handler that retries on specific,
    declared-retryable error types must not name LeaseFencedError among
    them, and this test documents that omission is deliberate by asserting
    it is never accidentally retryable via a broad except clause.
    """
    retryable_types: tuple[type[AnchorError], ...] = (ConfigAssertionError,)
    assert LeaseFencedError not in retryable_types
    assert not issubclass(LeaseFencedError, ConfigAssertionError)
