"""T002 — SQLSTATE round-trips to its typed error (FR-018).

Pure: `translate_postgres_error` only needs `.sqlstate` and `.detail`
attributes (structurally typed via `_PostgresErrorLike`), so this test
constructs a minimal fake rather than raising a real exception against a
live database.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from anchor.core.db.errors import (
    SQLSTATE_CONFIG_ASSERTION,
    SQLSTATE_FENCED_WRITE,
    SQLSTATE_IMMUTABLE_RECORD,
    SQLSTATE_RESULT_OVERWRITE,
    ConfigAssertionError,
    ImmutableRecordError,
    LeaseFencedError,
    ResultOverwriteError,
    translate_postgres_error,
)


@dataclass
class _FakePostgresError:
    sqlstate: str | None
    detail: str | None


def test_an001_maps_to_lease_fenced_error() -> None:
    fake = _FakePostgresError(
        sqlstate=SQLSTATE_FENCED_WRITE,
        detail=json.dumps({"run_id": 47, "stale_epoch": 3, "current_epoch": 5}),
    )
    translated = translate_postgres_error(fake)
    assert isinstance(translated, LeaseFencedError)
    assert translated.run_id == 47
    assert translated.stale_epoch == 3
    assert translated.current_epoch == 5


def test_an002_maps_to_config_assertion_error() -> None:
    fake = _FakePostgresError(
        sqlstate=SQLSTATE_CONFIG_ASSERTION,
        detail=json.dumps(
            {
                "relationship": "lease_duration_ms >= 4 * renewal_interval_ms",
                "offending_values": {"lease_duration_ms": 100, "renewal_interval_ms": 1000},
            }
        ),
    )
    translated = translate_postgres_error(fake)
    assert isinstance(translated, ConfigAssertionError)
    assert translated.relationship == "lease_duration_ms >= 4 * renewal_interval_ms"
    assert translated.offending_values["lease_duration_ms"] == 100


def test_an003_maps_to_immutable_record_error() -> None:
    fake = _FakePostgresError(
        sqlstate=SQLSTATE_IMMUTABLE_RECORD,
        detail=json.dumps({"table": "run_events", "operation": "DELETE"}),
    )
    translated = translate_postgres_error(fake)
    assert isinstance(translated, ImmutableRecordError)
    assert translated.table == "run_events"
    assert translated.operation == "DELETE"


def test_an004_maps_to_result_overwrite_error() -> None:
    fake = _FakePostgresError(
        sqlstate=SQLSTATE_RESULT_OVERWRITE, detail=json.dumps({"idempotency_key": "abc123"})
    )
    translated = translate_postgres_error(fake)
    assert isinstance(translated, ResultOverwriteError)
    assert translated.idempotency_key == "abc123"


@pytest.mark.parametrize("sqlstate", ["23505", "40001", "57014", None])
def test_unmapped_sqlstate_returns_none_rather_than_swallowing_it(sqlstate: str | None) -> None:
    """An unmapped SQLSTATE (a real PostgreSQL error, or none at all) must
    propagate as the driver's own exception type — this function's job is
    only to translate the codes it owns, never to silently absorb anything
    else (FR-018: "raise the generic database error for anything unmapped
    rather than swallowing it").
    """
    fake = _FakePostgresError(sqlstate=sqlstate, detail=None)
    assert translate_postgres_error(fake) is None
