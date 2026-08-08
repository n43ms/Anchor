"""The three-part startup assertion (FR-060), and its refusal path.

This is deliberately duplicated in SQL as the `runtime_config_assert`
trigger (migration 001) — the trigger is the backstop that makes the
property true even when this module is bypassed by a direct write; this
module exists to produce a message worth reading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from anchor.core.db.errors import ConfigAssertionError

if TYPE_CHECKING:
    from anchor.core.config.settings import RuntimeSettings


def assert_relationships(settings: RuntimeSettings) -> None:
    """Raise `ConfigAssertionError` naming the violated relationship and both
    offending values if any of the following do not hold:

    1. `lease_duration_ms >= 4 * renewal_interval_ms`
       Below this, ordinary renewal latency variance starts fencing healthy
       workers — see anchor-spec.md Addendum C §25.5.
    2. `margin_ms == lease_duration_ms - renewal_interval_ms`
       The margin is asserted rather than derived so a hand-edited
       `runtime_config` row cannot silently violate the relationship.
    3. `step_timeout_ms > 0`
       A zero timeout would mean no external call is ever bounded.
    """
    required_multiple = 4
    if settings.lease_duration_ms < required_multiple * settings.renewal_interval_ms:
        raise ConfigAssertionError(
            relationship="lease_duration_ms >= 4 * renewal_interval_ms",
            offending_values={
                "lease_duration_ms": settings.lease_duration_ms,
                "renewal_interval_ms": settings.renewal_interval_ms,
                "required_minimum_lease_duration_ms": (
                    required_multiple * settings.renewal_interval_ms
                ),
            },
        )

    expected_margin = settings.lease_duration_ms - settings.renewal_interval_ms
    if settings.margin_ms != expected_margin:
        raise ConfigAssertionError(
            relationship="margin_ms == lease_duration_ms - renewal_interval_ms",
            offending_values={
                "margin_ms": settings.margin_ms,
                "lease_duration_ms": settings.lease_duration_ms,
                "renewal_interval_ms": settings.renewal_interval_ms,
                "expected_margin_ms": expected_margin,
            },
        )

    if settings.step_timeout_ms <= 0:
        raise ConfigAssertionError(
            relationship="step_timeout_ms > 0",
            offending_values={"step_timeout_ms": settings.step_timeout_ms},
        )
