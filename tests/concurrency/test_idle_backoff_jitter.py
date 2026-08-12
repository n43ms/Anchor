"""T155 — idle workers' poll times spread rather than synchronize into a
polling convoy (FR-014). `_jittered_seconds` is deterministic in
distribution (bounded, centered on the nominal interval) but not in value,
so many samples must show real spread rather than collapsing to one value.
"""

from __future__ import annotations

from anchor.worker.loop import _jittered_seconds

BASE_MS = 500
JITTER_PCT = 0.25


def test_jittered_seconds_stays_within_the_configured_spread() -> None:
    lower = (BASE_MS * (1 - JITTER_PCT)) / 1000
    upper = (BASE_MS * (1 + JITTER_PCT)) / 1000
    samples = [_jittered_seconds(BASE_MS, JITTER_PCT) for _ in range(500)]
    assert all(lower - 1e-9 <= s <= upper + 1e-9 for s in samples)


def test_jittered_seconds_does_not_collapse_to_a_single_value() -> None:
    samples = {_jittered_seconds(BASE_MS, JITTER_PCT) for _ in range(200)}
    assert len(samples) > 50, (
        "many workers polling at the same nominal interval must not synchronize"
    )


def test_zero_jitter_is_exactly_the_nominal_interval() -> None:
    assert _jittered_seconds(BASE_MS, 0.0) == BASE_MS / 1000


def test_jittered_seconds_never_goes_negative() -> None:
    # Even a pathological jitter_pct > 1 must not produce a negative sleep.
    samples = [_jittered_seconds(BASE_MS, 1.5) for _ in range(200)]
    assert all(s >= 0.0 for s in samples)
