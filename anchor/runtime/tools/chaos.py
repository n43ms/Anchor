"""`flaky_call` — the one tool whose job is to fail (plan.md P8.3, T502;
FR-078).

Every other demo tool always succeeds, so nothing in the fleet's normal
workload exercises `worker.retry`'s backoff and dead-letter path end to
end. `flaky_call` closes that gap without breaking `I6`: the decision to
fail is made once, by the agent, via `ctx.random()` — a journaled,
replay-stable draw — and passed down as a plain boolean argument. The tool
itself is a pure function of that argument, exactly like every other tool
here; no randomness is read inside it.

**Why a failing draw dead-letters instead of eventually succeeding.** The
random draw is journaled per `step_index`, not per attempt (D-47): a
retried attempt re-enters the same step and replays the *same* recorded
value, since nothing about a `STEP_FAILED` retry changes which step index
is being executed. A run that draws "fail" therefore fails identically on
every attempt until `max_attempts_per_step` is exhausted and the run
dead-letters; a run that draws "succeed" completes on its first attempt.
This is still a real exercise of the retry path (every attempt before the
cap goes through the genuine backoff/attempt-count machinery), just not one
that models a transient fault clearing on its own — that would require
attempt-scoped randomness, which would mean the *number of retries*
diverged across replay attempts, which is exactly the non-determinism `I6`
forbids.

Declared `retry_safe`: the only "effect" is raising or not, so re-execution
carries no risk of a real duplicate side effect.
"""

from __future__ import annotations

import asyncio
from typing import Any

from anchor.runtime.tools.registry import ToolDeclaration

_MAX_SLOW_CALL_S = 30.0


class ChaosInjectedFailure(Exception):
    """Raised by `flaky_call` when its `should_fail` argument is `True`.
    Distinct from a bare exception so a log or a test can recognize an
    injected failure rather than a genuine tool bug.
    """


async def _flaky_call(args: dict[str, Any], **_: Any) -> Any:
    if args.get("should_fail", False):
        raise ChaosInjectedFailure("chaos harness: injected tool failure")
    return {"ok": True}


async def _slow_call(args: dict[str, Any], **_: Any) -> Any:
    """The chaos harness's latency-injection workload (T500, FR-077): sleeps
    for exactly the duration its caller asked for, so the fleet's real step
    latency is visibly stretched without touching any tool that carries a
    real proof-of-execution effect. Capped, not because a longer sleep is
    unsafe, but so a misconfigured submission cannot exceed `step_timeout`
    by an amount large enough to make every attempt time out identically —
    the point is to stretch a step's latency, not to guarantee it fails.
    """
    latency_s = min(float(args.get("latency_ms", 0)) / 1000, _MAX_SLOW_CALL_S)
    await asyncio.sleep(latency_s)
    return {"slept_ms": latency_s * 1000}


CHAOS_TOOLS: dict[str, ToolDeclaration] = {
    "flaky_call": ToolDeclaration(
        name="flaky_call",
        fn=_flaky_call,
        safety="retry_safe",
        naturally_idempotent=True,
        description="Fails when told to (chaos harness tool-failure injection, FR-078).",
    ),
    "slow_call": ToolDeclaration(
        name="slow_call",
        fn=_slow_call,
        safety="retry_safe",
        naturally_idempotent=True,
        description="Sleeps for a configured duration (chaos harness latency injection, FR-077).",
    ),
}
