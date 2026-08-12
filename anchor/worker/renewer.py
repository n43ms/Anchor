"""The background renewer task (plan.md P3.4, constitution Principle VII).

Runs on its own timer, entirely independent of step progress — coupling
renewal to step completion is the mistake that makes a long step unrunnable,
since a step that legitimately takes longer than one lease would then lose
ownership mid-step for no reason other than not having finished yet. This
is what makes two configuration profiles (a 4s demo lease and a 20s
production lease) both viable against the *same* step-execution code: the
renewer's cadence is a property of the profile, not of any step.

**A stalled process is still fenced correctly.** If the event loop blocks,
this task cannot run either — there is no separate thread or watchdog
keeping it alive — so the lease lapses on schedule and the run is reclaimed.
The renewer is not capable of signalling liveness that outlives a stalled
process, which is the entire point: a second, more-resilient liveness
channel would disagree with the lease during exactly the failure this
system exists to detect.

**On a rejected renewal, this task raises rather than swallowing or
retrying.** `LeaseFencedError` propagating out of `renew_forever` is what
the worker's per-run `asyncio.TaskGroup` (plan.md P3.4, `anchor/worker/loop.py`)
uses to cancel the sibling execution task — structured concurrency, not a
bookkeeping flag, so the cancellation is real even if the caller forgets to
check anything. Per `I3`, this task MUST NOT retry the write it lost.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncpg

from anchor.core.config.settings import RuntimeSettings
from anchor.core.leases.renew import renew_once

logger = logging.getLogger(__name__)


async def renew_forever(
    pool: asyncpg.Pool,
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    settings: RuntimeSettings,
) -> None:
    """Renew this run's lease every `renewal_interval_ms` until cancelled or
    fenced. Intended to run as one task inside the per-run `TaskGroup`
    alongside `execute_run`; the caller is responsible for cancelling this
    task once execution finishes normally (there is no other way for this
    loop to learn that it should stop, by design — it does not inspect run
    status itself, which would be a second path to the same decision).

    Crash behaviour: a crash between two ticks leaves the lease exactly as
    the last successful renewal set it — indistinguishable from any other
    missed renewal, and resolved identically by the next reclaim poll.
    """
    is_first = True
    while True:
        await asyncio.sleep(settings.renewal_interval_ms / 1000)
        async with pool.acquire() as conn:
            await renew_once(
                conn,
                run_id=run_id,
                epoch=epoch,
                worker_id=worker_id,
                settings=settings,
                is_first=is_first,
                force_final=False,
                max_payload_bytes=settings.max_event_payload_bytes,
            )
        is_first = False


async def final_renewal(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    settings: RuntimeSettings,
) -> None:
    """Called once by the execution path immediately before a terminal-state
    append, forcing `emit_reason: final_before_terminal` (D-48). The
    periodic renewer cannot do this itself — its timer has no way to know
    in advance which tick is the last one before completion — so the
    execution task, which does know, makes this one explicit call on the
    same connection it is about to use for the terminal append.
    """
    await renew_once(
        conn,
        run_id=run_id,
        epoch=epoch,
        worker_id=worker_id,
        settings=settings,
        is_first=False,
        force_final=True,
        max_payload_bytes=settings.max_event_payload_bytes,
    )
