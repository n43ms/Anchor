"""Lease renewal (plan.md P3.3, research.md D-48).

**Renewal is the only liveness signal, deliberately.** There is no separate
heartbeat that can outlive a stalled process: if the event loop blocks, the
renewer cannot run, the lease is never extended, and the run is reclaimed
once it expires. A worker that is merely slow and one that is truly dead
are indistinguishable by design, because a signal that could tell them apart
would be a second source of truth for liveness — the exact split-brain risk
`I3`'s single epoch exists to close off.

**A zero-row renewal is a fencing signal, not a retryable error.** The
`WHERE id = $1 AND epoch = $2` guard is what makes this call self-checking:
if another worker has already reclaimed the run (raising its epoch), this
statement updates nothing, and `renew_once` raises `LeaseFencedError` rather
than returning a falsy result a caller could shrug off. Per `I3`, a fenced
write is never retried. This module never attempts to record the fencing as
an event on the run's own log: `I3`/FR-019 requires a fenced worker to write
nothing further through that run, including no error event, so surfacing
the fencing is the caller's job (cancelling the sibling execution task via
the worker's `TaskGroup`, plan.md P3.4) — recording `WORKER_FENCED` itself
is phase 4's scope, exercised from the *claiming* worker's side once
fencing is behaviourally demonstrated end to end.

**Emission is deliberately sparse; measurement is not** (D-48). Every
renewal's latency is logged to structured telemetry unconditionally
(`renewal_latency_ms` in every log line this module emits), so the
distribution stays complete. Only a subset of renewals become a
`LEASE_RENEWED` *event* in the log: the first after a claim, any renewal
whose latency exceeds `renewal_latency_warn_pct` of the lease, the one
immediately preceding a terminal transition (forced by the caller, not
detected by the timer — the renewer cannot know in advance which tick is
last), and — under the `always` policy only — every renewal. `LEASE_RENEWED`
is the one event type replay never consumes (P2.1, T119), which is what
licenses this conditional emission without touching `I2`'s "the 17 event
types MUST exist": all 17 still exist, and every renewal is still counted
in telemetry even when it is not logged as an event.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

import asyncpg

from anchor.core.config.settings import LeaseRenewedEmitPolicy, RuntimeSettings
from anchor.core.db.errors import LeaseFencedError
from anchor.core.events.append import append
from anchor.core.events.types import EventType

logger = logging.getLogger(__name__)

EmitReason = Literal[
    "first_after_claim", "latency_threshold_exceeded", "final_before_terminal", "always_mode"
]

# The epoch guard IS the fencing check for this statement (I3): if another
# worker's claim has already advanced runs.epoch past what this worker
# holds, zero rows match and nothing is updated. `status = 'running'` is a
# defensive second guard — a run that has already reached a terminal state
# holds no lease (runs_terminal_holds_no_lease, migration 001) — but the
# epoch check is what actually detects a stale writer; this call never
# races against itself within one worker's own epoch.
_RENEW_SQL = """
UPDATE runs
SET lease_expires_at = now() + ($3 || ' milliseconds')::interval
WHERE id = $1 AND epoch = $2 AND status = 'running'
RETURNING lease_expires_at
"""


@dataclass(frozen=True, slots=True)
class RenewalOutcome:
    lease_expires_at: Any
    latency_ms: float
    emitted: bool
    emit_reason: EmitReason | None


async def renew_once(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    settings: RuntimeSettings,
    is_first: bool,
    force_final: bool,
    max_payload_bytes: int,
) -> RenewalOutcome:
    """Extend the lease by one `renewal_interval_ms` and decide, per D-48's
    policy, whether this renewal becomes a `LEASE_RENEWED` event.

    Raises `LeaseFencedError` when the epoch guard matches zero rows — the
    caller MUST NOT retry (`I3`) and MUST let the exception propagate so the
    worker's `TaskGroup` cancels the sibling execution task (plan.md P3.4).

    Crash behaviour: a crash before this transaction commits leaves the
    lease exactly as it was, which the next renewal tick (if still owned)
    or the reclaim poll (if not) resolves identically to any other missed
    renewal — there is no partial extension.
    """
    start = time.monotonic()
    async with conn.transaction():
        row = await conn.fetchrow(_RENEW_SQL, run_id, epoch, str(settings.lease_duration_ms))
        latency_ms = (time.monotonic() - start) * 1000

        if row is None:
            logger.warning(
                "lease renewal rejected: epoch is stale",
                extra={"run_id": run_id, "epoch": epoch, "worker_id": worker_id},
            )
            raise LeaseFencedError(run_id=run_id, stale_epoch=epoch)

        lease_expires_at = row["lease_expires_at"]

        emit_reason = _decide_emit_reason(
            is_first=is_first,
            force_final=force_final,
            latency_ms=latency_ms,
            settings=settings,
        )

        # Recorded regardless of emission (T167) — the distribution stays
        # complete in telemetry even on ticks the log stays silent about.
        logger.info(
            "lease renewed",
            extra={
                "run_id": run_id,
                "epoch": epoch,
                "worker_id": worker_id,
                "renewal_latency_ms": latency_ms,
                "emitted": emit_reason is not None,
            },
        )

        if emit_reason is not None:
            await append(
                conn,
                run_id=run_id,
                type=EventType.LEASE_RENEWED,
                payload={
                    "lease_expires_at": lease_expires_at.isoformat(),
                    "renewal_latency_ms": latency_ms,
                    "emit_reason": emit_reason,
                },
                epoch=epoch,
                worker_id=worker_id,
                max_payload_bytes=max_payload_bytes,
            )

        return RenewalOutcome(
            lease_expires_at=lease_expires_at,
            latency_ms=latency_ms,
            emitted=emit_reason is not None,
            emit_reason=emit_reason,
        )


def _decide_emit_reason(
    *, is_first: bool, force_final: bool, latency_ms: float, settings: RuntimeSettings
) -> EmitReason | None:
    """D-48's policy, applied in priority order. `force_final` is set by the
    caller immediately before a terminal-state transition, never inferred
    by the renewer itself — the renewer's own timer has no way to know
    which tick will be the last one before completion.
    """
    if force_final:
        return "final_before_terminal"
    if is_first:
        return "first_after_claim"
    if settings.lease_renewed_emit_policy is LeaseRenewedEmitPolicy.ALWAYS:
        return "always_mode"
    warn_threshold_ms = settings.renewal_latency_warn_pct * settings.lease_duration_ms
    if latency_ms > warn_threshold_ms:
        return "latency_threshold_exceeded"
    return None
