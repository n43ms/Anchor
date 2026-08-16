"""Step-granularity retry and dead-lettering (plan.md P6.1/P6.2, T293-T295,
T317-T321; FR-051, FR-053, D-43).

**Retry is at step granularity, never run granularity** (FR-051): a failing
step is re-attempted at the same `step_index`, never by re-running the
whole agent from the start. The attempt number is *derived from the log* —
the count of `STEP_FAILED` events already recorded for this `step_index`
(`RunContext.attempts_by_step`, P2.1) — never from `runs.attempts` and never
from an in-memory counter (D-43): an in-memory counter resets on every
handoff, and a poison step under a worker that keeps getting killed and
replaced would then retry forever, which is precisely the production
symptom `tests/failure/test_attempt_cap_survives_handoff.py` exists to
catch (T295 — "against an in-memory counter this test does not fail, it
hangs").

**`STEP_FAILED` and the dead-letter transition are one transaction, not
two** (a deliberate strengthening over stating them as separate steps):
appending `STEP_FAILED` and, when the cap is exhausted, appending
`RUN_FAILED` plus the `runs.status = 'failed'` transition are committed
together. This removes an otherwise-real crash window: without it, a
process killed between "attempts exhausted, `STEP_FAILED` committed" and
"`RUN_FAILED` committed, lease released" would leave the run `running` with
a live lease, no different from any other in-flight run, and the next
worker to claim it would see `attempts_by_step` already at the cap and
execute the step *one further time* before dead-lettering — one attempt
more than the configured cap, silently. Making the two atomic means the cap
is exact, not merely eventual.
"""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from anchor.core.config.settings import RuntimeSettings
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.worker.retry.backoff import compute_backoff_ms


class DeadLettered(Exception):
    """Raised after a run has been transitioned to `failed` and its lease
    released, atomically, inside `record_step_failure`. Mirrors
    `core.journal.policies.NeedsReviewHalted`: by the time this is raised,
    the terminal transition is already committed, so the caller's handler
    is exactly one `return` — no final renewal (there is no lease left) and
    no `RUN_COMPLETED` (the run did not complete).
    """

    def __init__(self, run_id: int, step_index: int) -> None:
        self.run_id = run_id
        self.step_index = step_index
        super().__init__(f"run {run_id} dead-lettered at step {step_index}")


@dataclass(frozen=True, slots=True)
class StepFailureOutcome:
    attempt: int
    will_retry: bool
    backoff_ms: int | None


async def record_step_failure(
    conn: asyncpg.Connection,
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    step_index: int,
    attempt: int,
    error: BaseException,
    settings: RuntimeSettings,
) -> StepFailureOutcome:
    """Append `STEP_FAILED` for this attempt and, if the attempt cap is now
    exhausted, dead-letter the run in the same transaction (T321).

    `attempt` is the attempt number that just failed — the caller's
    `StepContext.attempt`, itself derived from the log (D-43) rather than
    computed here, so this function never has to re-derive it from
    `run_events` on its own.

    Raises `DeadLettered` when the cap is exhausted; the caller must let it
    propagate rather than catching it as an ordinary step failure, exactly
    as it lets `core.journal.policies.NeedsReviewHalted` propagate.

    Crash behaviour: a crash before this transaction commits leaves no
    `STEP_FAILED`, no `RUN_FAILED`, and the run exactly as it was — the
    next attempt (this worker, if not fenced, or its successor) re-executes
    this same step at the same derived attempt number. There is no
    intermediate state in which `STEP_FAILED` is recorded but the
    consequence of it — retry or dead-letter — is not yet decided.
    """
    will_retry = attempt < settings.max_attempts_per_step
    backoff_ms = compute_backoff_ms(attempt, settings) if will_retry else None

    async with conn.transaction():
        await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_FAILED,
            payload={
                "step_index": step_index,
                "attempt": attempt,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "will_retry": will_retry,
                "backoff_ms": backoff_ms,
            },
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            max_payload_bytes=settings.max_event_payload_bytes,
        )

        if not will_retry:
            await append(
                conn,
                run_id=run_id,
                type=EventType.RUN_FAILED,
                payload={
                    "step_index": step_index,
                    "attempts": attempt,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "dead_lettered": True,
                },
                epoch=epoch,
                worker_id=worker_id,
                step_index=step_index,
                max_payload_bytes=settings.max_event_payload_bytes,
            )
            await conn.execute(
                """
                UPDATE runs
                SET status = 'failed',
                    owner_worker_id = NULL,
                    lease_expires_at = NULL,
                    finished_at = now()
                WHERE id = $1
                """,
                run_id,
            )

    outcome = StepFailureOutcome(attempt=attempt, will_retry=will_retry, backoff_ms=backoff_ms)
    if not will_retry:
        raise DeadLettered(run_id, step_index)
    return outcome
