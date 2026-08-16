"""Exponential backoff with jitter (plan.md P6.1, T317, FR-052).

Every constant this module reads comes from `RuntimeSettings` — no timing
constant is legal anywhere else in the codebase (FR-059,
`tests/boundary/test_no_hardcoded_constants.py`).
"""

from __future__ import annotations

import random

from anchor.core.config.settings import RuntimeSettings


def compute_backoff_ms(attempt: int, settings: RuntimeSettings) -> int:
    """The delay before retrying the attempt that just failed, given
    `attempt` (1-indexed: the attempt number that failed).

    `backoff_base_ms * backoff_factor ** (attempt - 1)`, jittered by
    `+/- backoff_jitter_pct` and then clamped into `[0, backoff_cap_ms]` —
    clamped *after* jitter, so `backoff_cap_ms` is a hard ceiling on the
    interval a caller ever actually waits, not merely on the pre-jitter
    midpoint.
    """
    raw_ms = settings.backoff_base_ms * (settings.backoff_factor ** (attempt - 1))
    spread = raw_ms * settings.backoff_jitter_pct
    jittered_ms = raw_ms + random.uniform(-spread, spread)
    return int(min(max(0.0, jittered_ms), settings.backoff_cap_ms))
