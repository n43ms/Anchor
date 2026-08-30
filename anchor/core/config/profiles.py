"""The two named profiles (FR-061): demo/chaos and production.

Every published measurement MUST report which profile it was taken under
(data-model.md §7, `chaos_runs.config_profile`) — a recovery figure without
its profile is not a measurement.
"""

from __future__ import annotations

from enum import StrEnum

from anchor.core.config.settings import LeaseRenewedEmitPolicy, RuntimeSettings


class ConfigProfile(StrEnum):
    """Selected by `ANCHOR_CONFIG_PROFILE`; not itself a `runtime_config` key."""

    DEMO = "demo"
    PRODUCTION = "production"


# Demo/chaos profile: short lease and renewal, so a kill-and-recover cycle in
# the guided demo and the chaos harness completes in seconds rather than
# minutes. Implied recovery bound ≈ lease_duration - renewal_interval/2 +
# reclaim_poll_interval/2 ≈ 3.75s (plan.md, Technical Context).
_DEMO = RuntimeSettings(
    lease_duration_ms=4_000,
    renewal_interval_ms=1_000,
    margin_ms=3_000,
    reclaim_poll_interval_ms=500,
    renewal_latency_warn_pct=0.5,
    lease_renewed_emit_policy=LeaseRenewedEmitPolicy.BOUNDARIES_AND_SLOW,
    step_timeout_ms=600_000,
    max_attempts_per_step=3,
    backoff_base_ms=500,
    backoff_factor=2.0,
    backoff_jitter_pct=0.25,
    backoff_cap_ms=10_000,
    per_worker_concurrency=10,
    global_concurrency_cap=50,
    max_event_payload_bytes=1_048_576,
)

# Production profile: a lease long enough to absorb realistic renewal jitter
# under load. Implied recovery bound ≈ 18.5s (plan.md, Technical Context).
_PRODUCTION = RuntimeSettings(
    lease_duration_ms=20_000,
    renewal_interval_ms=5_000,
    margin_ms=15_000,
    reclaim_poll_interval_ms=1_000,
    renewal_latency_warn_pct=0.5,
    lease_renewed_emit_policy=LeaseRenewedEmitPolicy.BOUNDARIES_AND_SLOW,
    step_timeout_ms=600_000,
    max_attempts_per_step=5,
    backoff_base_ms=1_000,
    backoff_factor=2.0,
    backoff_jitter_pct=0.25,
    backoff_cap_ms=60_000,
    per_worker_concurrency=25,
    global_concurrency_cap=500,
    max_event_payload_bytes=1_048_576,
)

PROFILES: dict[ConfigProfile, RuntimeSettings] = {
    ConfigProfile.DEMO: _DEMO,
    ConfigProfile.PRODUCTION: _PRODUCTION,
}


def profile_settings(profile: ConfigProfile) -> RuntimeSettings:
    """Return a fresh copy of the named profile's settings.

    A copy, not the module-level instance, so a caller mutating the result
    (e.g. a test constructing a deliberately-invalid variant) cannot corrupt
    the profile for every other test in the process.
    """
    return PROFILES[profile].model_copy(deep=True)
