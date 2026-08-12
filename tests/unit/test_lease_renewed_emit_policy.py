"""T154 — `LEASE_RENEWED` is emitted on `first_after_claim`, on
`latency_threshold_exceeded`, and on `final_before_terminal` — and NOT on
every renewal under the default (`boundaries_and_slow`) policy (D-48).
"""

from __future__ import annotations

from anchor.core.config.profiles import ConfigProfile, profile_settings
from anchor.core.config.settings import LeaseRenewedEmitPolicy
from anchor.core.leases.renew import _decide_emit_reason


def test_first_after_claim_always_emits() -> None:
    settings = profile_settings(ConfigProfile.DEMO)
    reason = _decide_emit_reason(
        is_first=True, force_final=False, latency_ms=0.1, settings=settings
    )
    assert reason == "first_after_claim"


def test_final_before_terminal_always_emits_even_if_also_first() -> None:
    settings = profile_settings(ConfigProfile.DEMO)
    # force_final takes priority over is_first — the caller only ever sets
    # force_final on the one call immediately preceding a terminal append.
    reason = _decide_emit_reason(is_first=True, force_final=True, latency_ms=0.1, settings=settings)
    assert reason == "final_before_terminal"


def test_latency_above_threshold_emits() -> None:
    settings = profile_settings(ConfigProfile.DEMO)
    warn_ms = settings.renewal_latency_warn_pct * settings.lease_duration_ms
    reason = _decide_emit_reason(
        is_first=False, force_final=False, latency_ms=warn_ms + 1, settings=settings
    )
    assert reason == "latency_threshold_exceeded"


def test_ordinary_renewal_under_default_policy_emits_nothing() -> None:
    settings = profile_settings(ConfigProfile.DEMO)
    warn_ms = settings.renewal_latency_warn_pct * settings.lease_duration_ms
    reason = _decide_emit_reason(
        is_first=False, force_final=False, latency_ms=warn_ms - 1, settings=settings
    )
    assert reason is None


def test_always_mode_emits_every_ordinary_renewal() -> None:
    settings = profile_settings(ConfigProfile.DEMO).model_copy(
        update={"lease_renewed_emit_policy": LeaseRenewedEmitPolicy.ALWAYS}
    )
    reason = _decide_emit_reason(
        is_first=False, force_final=False, latency_ms=0.1, settings=settings
    )
    assert reason == "always_mode"
