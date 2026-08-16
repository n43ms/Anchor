"""The worker's claim-execute loop (plan.md P1.4, extended by P2.4/P2.5/P3.4/P5.6).

**Claiming, now real.** Claiming is delegated to `core.leases.claim.claim_one`
(P3.1), the single `SKIP LOCKED` CTE that handles both a `pending` run and a
`running` run whose lease has expired, guarded by the global concurrency cap,
all in one transaction (`I4`). This module no longer contains its own claim
SQL — that was the phase-1/2 interim statement, replaced here.

**Ownership, now time-bounded and independently renewed.** Each claimed run
gets its own `asyncio.TaskGroup` (P3.4) holding two tasks: the execution
task (this module's `execute_run`) and the renewer (`worker.renewer`,
P3.3), on its own timer, entirely independent of step progress. Structured
concurrency is what makes the fencing path real code rather than an
argument: if the renewer's lease extension is rejected (another worker has
already reclaimed), it raises `LeaseFencedError`, and the `TaskGroup`
cancels the sibling execution task — including mid-step if necessary, since
a fenced worker must stop immediately rather than at the next convenient
boundary (`I3`; this is deliberately not the *cooperative*, between-steps
cancellation the constitution's Concurrency Rules describe for a
user-requested run cancellation, which is a different mechanism landing in
phase 6). The fenced worker retries nothing and returns to the idle pool.

**The execute path can also be the fencing detector, and now must say so
correctly.** Once epoch advances (this phase), an `append` call made with a
now-stale `epoch` — because *this* worker was fenced without its renewer
noticing first — is rejected by the phase-0 trigger. Fixed here: the
execute path's connection now goes through
`anchor.core.db.pool.acquire`'s translation instead of raw `pool.acquire()`,
so that rejection surfaces as `LeaseFencedError`, the same typed exception
the renewer raises, rather than a raw, untranslated `asyncpg.PostgresError`
that `run_claimed`'s `except* LeaseFencedError` would not recognize.
Previously nothing in the worker used this translation at all — a gap with
no observable consequence while every write happened at a fresh epoch, but
a real one now that a stale write is possible.

**Replay, unchanged from phase 2.** Every claim — including the first —
folds the run's complete log through `core.replay.reconstruct` before any
step executes, and resumes at `last_completed_step_index + 1`, never at 0.

Crash behaviour, restated for this phase's additions: a crash before the
claim transaction commits leaves the run exactly as it was. A crash inside
the renewer task (the connection drops, the process dies) simply stops
renewals — the lease lapses on schedule and the next poll cycle, on this
worker or another, reclaims it once it expires; there is no separate
liveness signal to fall out of sync with the lease itself (`Principle
VII`).

**P2.5's interim limitation no longer applies.** A crash between a tool's
execution and its `TOOL_RESULT` used to be lost without dedup; from phase 5
onward every `ctx.call_tool` goes through `core.journal.two_phase`, so that
window is the uncertainty window `I8` names, resolved per the tool's
declared policy on the next attempt rather than silently re-executed. The
one new control-flow path this adds here: `_run_steps` may raise
`NeedsReviewHalted` (an `unsafe` tool, or an ambiguous reconciliation, or a
fleet-wide declaration conflict) — by the time that exception reaches
`execute_run`, the run is already `needs_review` and leaseless, committed
atomically inside `core.journal.policies.halt_needs_review`, so the handler
here is exactly one `return`: no final renewal (there is no lease left) and
no `RUN_COMPLETED` (the run did not complete).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import asyncpg

from anchor.core.config.settings import RuntimeSettings
from anchor.core.db.errors import LeaseFencedError
from anchor.core.db.pool import acquire as acquire_translated
from anchor.core.determinism.actions import Done, ModelCall, ToolCall, require_action
from anchor.core.determinism.context import StepContext
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.journal.policies import NeedsReviewHalted
from anchor.core.leases.claim import ClaimedRun, claim_one
from anchor.core.leases.fencing import DetectedBy, record_local_fencing
from anchor.core.replay.load import load_run_events
from anchor.core.replay.reconstruct import reconstruct
from anchor.runtime.agents.registry import resolve
from anchor.runtime.tools.demo import DEMO_TOOLS
from anchor.runtime.tools.model import StubAdapter
from anchor.worker.renewer import final_renewal, renew_forever

logger = logging.getLogger(__name__)


class RunCounter:
    """A mutable holder for this worker's own in-process running-run count
    (T174, data-model.md §5). `workers.current_run_count` is telemetry, not
    an authority — admission control (phase 6) reads a worker's own
    in-process count before claiming, never this column, since using the
    column to decide would be a second source of truth for something the
    worker already knows. `heartbeat_loop` reads `.value` on its own timer
    to publish that telemetry; `poll_and_execute_forever` is the only thing
    that ever mutates it.
    """

    __slots__ = ("value",)

    def __init__(self) -> None:
        self.value = 0


async def execute_run(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    agent_type: str,
    input: dict[str, Any],
    epoch: int,
    worker_id: str,
    settings: RuntimeSettings,
) -> None:
    """Replay the log, then run `decide_next_step` to completion from the
    correct step (P2.4).
    """
    decide_next_step = resolve(agent_type)
    if decide_next_step is None:
        raise ValueError(f"unregistered agent_type: {agent_type}")

    replay_start = time.monotonic()
    events = await load_run_events(conn, run_id)
    run_context = reconstruct(events)
    replay_ms = (time.monotonic() - replay_start) * 1000

    await append(
        conn,
        run_id=run_id,
        type=EventType.REPLAY_COMPLETED,
        payload={
            "steps_replayed": run_context.steps_replayed,
            "replay_ms": replay_ms,
            "last_completed_step_index": run_context.last_completed_step_index,
            "journal_entries_loaded": run_context.journal_entries_loaded,
            "nondet_values_loaded": run_context.nondet_values_loaded,
        },
        epoch=epoch,
        worker_id=worker_id,
        max_payload_bytes=settings.max_event_payload_bytes,
    )

    model_adapter = StubAdapter()
    messages: list[dict[str, Any]] = list(run_context.messages)
    # Resume strictly after the highest completed step — never re-present
    # an already-completed step to decide_next_step (P2.5, T110/T133).
    step_index = run_context.last_completed_step_index + 1
    assert step_index >= 0, "resume index must never be lower than the highest completed step"
    total_start = time.monotonic()

    try:
        action, step_index = await _run_steps(
            conn,
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            agent_type=agent_type,
            input=input,
            messages=messages,
            step_index=step_index,
            run_context=run_context,
            model_adapter=model_adapter,
            settings=settings,
        )
    except NeedsReviewHalted:
        # P5.6/T277: the run is already `needs_review`, leaseless, and
        # RUN_NEEDS_REVIEW is already committed — all inside
        # `core.journal.policies.halt_needs_review`, atomically, before
        # this exception was raised. Nothing else in this function may run:
        # no final renewal (there is no lease left to renew) and no
        # RUN_COMPLETED (the run did not complete). Returning here is the
        # whole handler.
        return

    total_duration_ms = (time.monotonic() - total_start) * 1000

    # One forced renewal, emitted unconditionally as final_before_terminal
    # (D-48), immediately before the terminal append — the renewer's own
    # timer cannot know in advance which tick will be the last one, so the
    # execution path makes this one explicit call instead.
    await final_renewal(conn, run_id=run_id, epoch=epoch, worker_id=worker_id, settings=settings)

    async with conn.transaction():
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_COMPLETED,
            payload={
                "output": action.output,
                "total_steps": step_index,
                "total_duration_ms": total_duration_ms,
                "handoff_count": 0,
            },
            epoch=epoch,
            worker_id=worker_id,
            max_payload_bytes=settings.max_event_payload_bytes,
        )
        await conn.execute(
            """
            UPDATE runs
            SET status = 'completed',
                owner_worker_id = NULL,
                lease_expires_at = NULL,
                finished_at = now()
            WHERE id = $1
            """,
            run_id,
        )


async def _run_steps(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    agent_type: str,
    input: dict[str, Any],
    messages: list[dict[str, Any]],
    step_index: int,
    run_context: Any,
    model_adapter: StubAdapter,
    settings: RuntimeSettings,
) -> tuple[Done, int]:
    """The step loop, factored out of `execute_run` so the
    `NeedsReviewHalted` boundary (P5.6, T277) is a single `try/except` at
    the call site rather than spread across the loop body. Returns the
    terminal `Done` action together with the number of steps executed.

    Crash behaviour is unchanged from phases 1-4 at every point except
    `ctx.call_tool`, whose crash behaviour is now stated fully in
    `core.journal.two_phase.execute_tool_call`'s docstring — the possible
    duplicate execution on retry that phases 1-2 stated as an interim
    limitation no longer exists.
    """
    decide_next_step = resolve(agent_type)
    assert decide_next_step is not None  # already validated by execute_run, above

    while True:
        ctx = StepContext(
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            input=input,
            messages=messages,
            attempt=run_context.attempts_by_step.get(step_index, 0) + 1,
            run_context=run_context,
            conn=conn,
            model_adapter=model_adapter,
            tool_registry=DEMO_TOOLS,
            max_payload_bytes=settings.max_event_payload_bytes,
        )
        raw_action = decide_next_step(ctx)
        action = require_action(raw_action)

        if isinstance(action, Done):
            break

        action_kind = "tool" if isinstance(action, ToolCall) else "model"
        await append(
            conn,
            run_id=run_id,
            type=EventType.STEP_STARTED,
            payload={"step_index": step_index, "action_kind": action_kind},
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            max_payload_bytes=settings.max_event_payload_bytes,
        )

        step_start = time.monotonic()
        if isinstance(action, ToolCall):
            # Any buffered non-determinism is flushed inside call_tool,
            # atomically with TOOL_INTENT (D-47) — nothing left to flush
            # here.
            await ctx.call_tool(action.name, action.args)
        elif isinstance(action, ModelCall):
            await ctx.call_model(action.messages, action.model)
        step_duration_ms = (time.monotonic() - step_start) * 1000

        if isinstance(action, ToolCall):
            await append(
                conn,
                run_id=run_id,
                type=EventType.STEP_COMPLETED,
                payload={
                    "step_index": step_index,
                    "duration_ms": step_duration_ms,
                    "action_kind": action_kind,
                },
                epoch=epoch,
                worker_id=worker_id,
                step_index=step_index,
                max_payload_bytes=settings.max_event_payload_bytes,
            )
        else:
            # A model-only step has no side effect to pair the buffer with,
            # so any nondet values it consulted are flushed atomically with
            # STEP_COMPLETED instead of TOOL_INTENT (D-47, T112).
            async with conn.transaction():
                await ctx.flush_pending_nondet()
                await append(
                    conn,
                    run_id=run_id,
                    type=EventType.STEP_COMPLETED,
                    payload={
                        "step_index": step_index,
                        "duration_ms": step_duration_ms,
                        "action_kind": action_kind,
                    },
                    epoch=epoch,
                    worker_id=worker_id,
                    step_index=step_index,
                    max_payload_bytes=settings.max_event_payload_bytes,
                )

        # Per-worker step throughput (T178, plan.md P3.7): with no console
        # yet, this is how three workers genuinely competing for real work
        # is observed — each worker's own step rate, in its own log lines,
        # tagged with run_id and epoch so a fencing incident and a merely
        # slow step are distinguishable after the fact (D-40).
        logger.info(
            "step completed",
            extra={
                "run_id": run_id,
                "epoch": epoch,
                "worker_id": worker_id,
                "step_index": step_index,
                "step_duration_ms": step_duration_ms,
                "steps_per_second": (1000 / step_duration_ms) if step_duration_ms > 0 else None,
            },
        )
        step_index += 1

    assert isinstance(action, Done)  # the only way out of the loop above
    return action, step_index


async def run_claimed(
    pool: asyncpg.Pool, claimed: ClaimedRun, *, worker_id: str, settings: RuntimeSettings
) -> None:
    """Execute one claimed run under a per-run `TaskGroup` holding the
    execution task and the independent renewer (P3.4).

    Crash behaviour at the two await points this function adds: if the
    renewer's connection is lost or its renewal is rejected, the
    `TaskGroup` cancels the execution task — real cancellation, not a
    checked flag, so it reaches even a step in the middle of an `await`.
    If the execution task finishes normally, it cancels the renewer itself
    (there is no other signal the renewer could use to learn the run is
    done without inspecting run status, which would be a second path to
    the same decision it should not have).
    """
    try:
        async with asyncio.TaskGroup() as tg:
            renew_task = tg.create_task(
                renew_forever(
                    pool,
                    run_id=claimed.run_id,
                    epoch=claimed.epoch,
                    worker_id=worker_id,
                    settings=settings,
                ),
                name=f"renew-run-{claimed.run_id}",
            )

            async def _execute_and_stop_renewer() -> None:
                async with acquire_translated(pool) as conn:
                    await execute_run(
                        conn,
                        run_id=claimed.run_id,
                        agent_type=claimed.agent_type,
                        input=claimed.input,
                        epoch=claimed.epoch,
                        worker_id=worker_id,
                        settings=settings,
                    )
                renew_task.cancel()

            tg.create_task(_execute_and_stop_renewer(), name=f"execute-run-{claimed.run_id}")
    except* LeaseFencedError as eg:
        # I3/T204: a fenced worker discards in-memory state, writes nothing
        # further, retries nothing, and returns to the idle pool. This
        # `except*` block is the guard — it is a deliberate dead end that
        # calls `core.events.append` for nothing at all. The surviving
        # writer, not this one, is responsible for `WORKER_FENCED`
        # (`core.leases.claim`, T210) precisely because this worker no
        # longer owns the run and its opinion about what went wrong is the
        # corruption the epoch exists to prevent. `record_local_fencing`
        # writes only to this process's own structured log and in-process
        # counter (T205, T217) — never to the run's log.
        #
        # `detected_by` is read off the exception itself rather than
        # assumed: `core.leases.renew.renew_once` raises with
        # `current_epoch=None` (its zero-row guard has no third column to
        # read one from), while the `AN001` trigger translated by
        # `core.db.pool.acquire` always carries one (migration 001). Picking
        # a value here without that signal would be exactly the kind of
        # guess `I8` forbids.
        for exc in eg.exceptions:
            if not isinstance(exc, LeaseFencedError):
                continue
            detected_by: DetectedBy = "append" if exc.current_epoch is not None else "renewer"
            record_local_fencing(
                run_id=claimed.run_id,
                worker_id=worker_id,
                stale_epoch=claimed.epoch,
                detected_by=detected_by,
            )


def _jittered_seconds(base_ms: int, jitter_pct: float) -> float:
    """`base_ms` scaled by +/- `jitter_pct`, so many idle workers polling at
    the same nominal interval do not synchronize into a convoy (FR-014).
    Reuses the retry backoff's configured jitter fraction rather than
    introducing a second, unconfigured jitter constant — both exist to
    solve the same "many callers, one nominal interval" problem.
    """
    spread = base_ms * jitter_pct
    return max(0.0, (base_ms + random.uniform(-spread, spread)) / 1000)


async def poll_and_execute_forever(
    pool: asyncpg.Pool,
    *,
    worker_id: str,
    settings: RuntimeSettings,
    run_counter: RunCounter | None = None,
) -> None:
    """Poll for one claimable run at a time and run it to completion under
    its own `TaskGroup`. Sequential across runs — this worker looks for its
    next run only after the previous one reaches a terminal state or is
    fenced away from it; per-worker concurrency (running several runs at
    once inside one process) is admission control's job in phase 6, not
    this loop's.

    `run_counter`, when provided, is incremented for the duration of
    `run_claimed` and decremented afterward unconditionally (even on
    fencing) — this worker's own count of runs it currently holds, which
    `worker.registry.heartbeat` publishes as telemetry (T174).
    """
    if run_counter is None:
        run_counter = RunCounter()

    while True:
        async with pool.acquire() as conn:
            claimed = await claim_one(
                conn,
                worker_id=worker_id,
                lease_duration_ms=settings.lease_duration_ms,
                global_concurrency_cap=settings.global_concurrency_cap,
                max_payload_bytes=settings.max_event_payload_bytes,
            )
        if claimed is None:
            await asyncio.sleep(
                _jittered_seconds(settings.reclaim_poll_interval_ms, settings.backoff_jitter_pct)
            )
            continue

        logger.info(
            "run claimed",
            extra={"run_id": claimed.run_id, "worker_id": worker_id, "epoch": claimed.epoch},
        )
        run_counter.value += 1
        try:
            await run_claimed(pool, claimed, worker_id=worker_id, settings=settings)
        finally:
            run_counter.value -= 1
