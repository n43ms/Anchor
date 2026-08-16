"""T293 — exponential backoff with jitter (plan.md P6.1, FR-052).

Pure: no I/O, no database. `compute_backoff_ms` reads every constant from
a `RuntimeSettings` instance passed in by the caller, never a
module-level literal (FR-059).
"""

from __future__ import annotations

from anchor.core.config.profiles import ConfigProfile, profile_settings
from anchor.worker.retry.backoff import compute_backoff_ms


def test_backoff_grows_exponentially_before_the_cap() -> None:
    settings = profile_settings(ConfigProfile.DEMO)
    # Demo profile: backoff_base_ms=500, backoff_factor=2.0, jitter=0.25,
    # cap_ms=10_000. Attempt 1 should center around 500ms, well under the
    # cap, so its jittered bounds are exact rather than clipped.
    samples = [compute_backoff_ms(1, settings) for _ in range(200)]
    lower = settings.backoff_base_ms * (1 - settings.backoff_jitter_pct)
    upper = settings.backoff_base_ms * (1 + settings.backoff_jitter_pct)
    assert all(lower - 1 <= s <= upper + 1 for s in samples)
    assert len(set(samples)) > 1, "jitter must vary the interval across calls"


def test_backoff_is_bounded_by_the_cap() -> None:
    settings = profile_settings(ConfigProfile.DEMO)
    # Attempt 10: base * factor**9 is far beyond backoff_cap_ms even before
    # jitter, so every sample must clip to the cap exactly.
    samples = [compute_backoff_ms(10, settings) for _ in range(200)]
    assert all(s <= settings.backoff_cap_ms for s in samples)
    assert max(samples) == settings.backoff_cap_ms


def test_backoff_never_negative() -> None:
    settings = profile_settings(ConfigProfile.DEMO)
    samples = [compute_backoff_ms(1, settings) for _ in range(500)]
    assert all(s >= 0 for s in samples)


def test_backoff_reads_every_constant_from_settings_not_a_module_default() -> None:
    """A different profile's constants produce a different bound —
    proving the function has no hardcoded fallback of its own (FR-059).
    """
    demo = profile_settings(ConfigProfile.DEMO)
    production = profile_settings(ConfigProfile.PRODUCTION)
    assert demo.backoff_base_ms != production.backoff_base_ms

    demo_samples = [compute_backoff_ms(1, demo) for _ in range(50)]
    production_samples = [compute_backoff_ms(1, production) for _ in range(50)]
    assert max(demo_samples) < min(production_samples)
