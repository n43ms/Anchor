"""Test-only zombie-worker injection (plan.md P4.4, FR-077).

Suspends the *calling* worker's event loop synchronously for a duration,
simulating a fully blocked process: no task on that loop — including the
lease renewer — can run until the stall ends. This is what makes the zombie
scenario reproducible on demand rather than something a test can only wait
to happen to intermittently: a worker holding a stale epoch, unable to renew
or notice anything, is exactly `blocked_event_loop` from the failure matrix
(T196) and the precondition for the zombie-fencing tests (T191-T195).

**Unreachable outside tests and the chaos harness** (T213). This function
uses a synchronous `time.sleep`, which is never an acceptable thing for
production code to do to an event loop — it exists solely to construct a
failure condition on demand, and `tests/boundary/test_stall_injection_not_reachable.py`
asserts no production import path (`anchor.api`, `anchor.worker.__main__`,
`anchor.runtime`) reaches this module.
"""

from __future__ import annotations

import time

# Import-time guard: this module is intended to be reachable only from
# `tests/` and `anchor/chaos/`. It does not attempt runtime enforcement
# (e.g. inspecting the call stack) because that would be exactly the kind
# of "clever" indirection the constitution prefers over explicit checks —
# the boundary test walking import paths (T213) is the enforcement
# mechanism, not a runtime guard here.


def block_event_loop(duration_s: float) -> None:
    """Block the current thread's event loop for `duration_s` seconds.

    Crash behaviour: this call does not raise, and it does not touch the
    database or any run state directly. The observable effect is entirely
    indirect — every task sharing this event loop (execution, renewal,
    heartbeat) stops making progress for the duration, which is what a real
    stalled process looks like to the rest of the system (`I5`: only the
    database clock, evaluated by another worker's reclaim poll, notices).
    """
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    time.sleep(duration_s)
