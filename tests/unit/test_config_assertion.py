"""T001 — the three-part startup assertion (FR-060).

Pure: constructs `RuntimeSettings` in memory and calls
`assert_relationships()` directly. No database needed.
"""

from __future__ import annotations

import pytest

from anchor.core.config.profiles import ConfigProfile, profile_settings
from anchor.core.config.settings import RuntimeSettings
from anchor.core.db.errors import ConfigAssertionError


def test_both_named_profiles_are_accepted() -> None:
    profile_settings(ConfigProfile.DEMO).assert_relationships()
    profile_settings(ConfigProfile.PRODUCTION).assert_relationships()


def test_lease_equal_to_renewal_interval_is_rejected() -> None:
    settings = profile_settings(ConfigProfile.DEMO).model_copy(
        update={"lease_duration_ms": 1_000, "renewal_interval_ms": 1_000, "margin_ms": 0}
    )
    with pytest.raises(ConfigAssertionError) as exc_info:
        settings.assert_relationships()
    assert "lease_duration_ms >= 4 * renewal_interval_ms" in exc_info.value.relationship
    assert exc_info.value.offending_values["lease_duration_ms"] == 1_000
    assert exc_info.value.offending_values["renewal_interval_ms"] == 1_000


def test_lease_below_four_times_renewal_is_rejected() -> None:
    settings = profile_settings(ConfigProfile.DEMO).model_copy(
        update={"lease_duration_ms": 3_000, "renewal_interval_ms": 1_000, "margin_ms": 2_000}
    )
    with pytest.raises(ConfigAssertionError) as exc_info:
        settings.assert_relationships()
    assert exc_info.value.relationship == "lease_duration_ms >= 4 * renewal_interval_ms"


def test_margin_not_matching_the_derived_value_is_rejected() -> None:
    settings = profile_settings(ConfigProfile.DEMO).model_copy(update={"margin_ms": 1})
    with pytest.raises(ConfigAssertionError) as exc_info:
        settings.assert_relationships()
    assert exc_info.value.relationship == "margin_ms == lease_duration_ms - renewal_interval_ms"
    assert "margin_ms" in exc_info.value.offending_values
    assert "expected_margin_ms" in exc_info.value.offending_values


def test_zero_step_timeout_is_rejected() -> None:
    with pytest.raises(ValueError):
        # step_timeout_ms carries `gt=0` at the pydantic field level, so a
        # zero value never reaches assert_relationships() at all — this
        # documents that the field constraint is the first line of defence,
        # and assert_relationships()'s own step_timeout_ms > 0 check is the
        # backstop for a value that bypassed field validation (e.g. one
        # read back from a JSONB column via model_construct()).
        RuntimeSettings.model_validate(
            profile_settings(ConfigProfile.DEMO).model_dump() | {"step_timeout_ms": 0}
        )


def test_zero_step_timeout_bypassing_field_validation_is_rejected() -> None:
    settings = RuntimeSettings.model_construct(
        **(profile_settings(ConfigProfile.DEMO).model_dump() | {"step_timeout_ms": 0})
    )
    with pytest.raises(ConfigAssertionError) as exc_info:
        settings.assert_relationships()
    assert exc_info.value.relationship == "step_timeout_ms > 0"


def test_rejection_names_the_relationship_and_both_offending_values() -> None:
    """The message must never be a bare 'invalid configuration' — it must
    name what was violated and the actual values involved, per the
    docstring on ConfigAssertionError.
    """
    settings = profile_settings(ConfigProfile.DEMO).model_copy(
        update={"lease_duration_ms": 100, "renewal_interval_ms": 1_000, "margin_ms": -900}
    )
    with pytest.raises(ConfigAssertionError) as exc_info:
        settings.assert_relationships()
    message = str(exc_info.value)
    assert "lease_duration_ms=100" in message
    assert "renewal_interval_ms=1000" in message
