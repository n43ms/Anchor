"""Fencing incident recording and counting (plan.md P4.3/P4.6).

**Where `WORKER_FENCED` may be written, and why `detected_by` is always
`"renewer"` here.** `I3`/FR-019 forbids a fenced worker from writing
anything to the run's own log, including a record of its own fencing — so
the only legitimate writer of `WORKER_FENCED` is the *surviving* writer, at
the moment it reclaims the run (`core.leases.claim.claim_one`). Structurally,
the claim statement's reclaim branch (`status = 'running' AND
lease_expires_at < now()`) is reachable **only** through lease expiry: a
cooperative/graceful kill releases the lease on its way out (plan.md P3.7's
graceful-kill variant) rather than leaving it to lapse. That means every
reclaim this module records is, by construction, a case where the previous
owner's renewer missed enough ticks for the lease to expire — so
`detected_by: "renewer"` is a fact about how reclaim became possible, not a
guess about which race fired on the stale worker's side (`I8`: uncertainty
is surfaced, never guessed).

A *different* event — a stale worker's own `append` being rejected with
`AN001` after it has already been superseded — is real and detectable, but
it happens on the fenced worker's own connection, which per `I3` must not
write to the run's log at all. That incident is recorded here only as
structured telemetry (`record_local_fencing`), never as a run-log event.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Literal

import asyncpg

from anchor.core.events.append import append
from anchor.core.events.types import EventType

logger = logging.getLogger(__name__)

DetectedBy = Literal["renewer", "append"]


class FencingCounter:
    """A process-local, thread-safe count of fencing incidents observed by
    this worker process, by detection site.

    This is telemetry only (constitution Principle II) — nothing reads it to
    make an ownership or admission decision. It exists so the fencing-rate
    metric (FR-071, phase 6/8) has history by the time its chart exists,
    without this phase inventing a new schema table or Redis key for a
    number nothing yet consumes authoritatively.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[DetectedBy, int] = {"renewer": 0, "append": 0}

    def increment(self, detected_by: DetectedBy) -> None:
        with self._lock:
            self._counts[detected_by] += 1

    def snapshot(self) -> dict[DetectedBy, int]:
        with self._lock:
            return dict(self._counts)


# One counter per process. A worker process holds exactly one fencing
# counter for its own lifetime — there is no cross-process aggregation here,
# because that is what the phase-6/8 metrics pipeline is for.
FENCING_COUNTER = FencingCounter()


def record_local_fencing(
    *, run_id: int, worker_id: str, stale_epoch: int, detected_by: DetectedBy
) -> None:
    """Record a fencing incident this worker observed on its own connection.

    Never appends to the run's log — a fenced worker must write nothing
    further through that run (`I3`, FR-019). This is the local counterpart
    to `append_worker_fenced`: it is what a worker calls about *itself*
    (both `detected_by` values are reachable here — a worker can discover
    its own fencing via a rejected renewal or via a rejected append), logged
    to structured telemetry so the incident is reconstructable from this
    worker's own log lines afterward (D-40), and counted for the
    fencing-rate metric (FR-071).
    """
    FENCING_COUNTER.increment(detected_by)
    logger.warning(
        "fencing incident detected locally",
        extra={
            "run_id": run_id,
            "worker_id": worker_id,
            "stale_epoch": stale_epoch,
            "detected_by": detected_by,
        },
    )


async def append_worker_fenced(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    surviving_worker_id: str,
    new_epoch: int,
    fenced_worker_id: str,
    stale_epoch: int,
    max_payload_bytes: int,
) -> None:
    """Append `WORKER_FENCED` from the surviving writer's own claim
    transaction (T210). Always `detected_by: "renewer"` — see module
    docstring for why that is a structural fact of reclaim, not a guess.
    """
    await append(
        conn,
        run_id=run_id,
        type=EventType.WORKER_FENCED,
        payload={
            "fenced_worker_id": fenced_worker_id,
            "stale_epoch": stale_epoch,
            "current_epoch": new_epoch,
            "detected_by": "renewer",
        },
        epoch=new_epoch,
        worker_id=surviving_worker_id,
        max_payload_bytes=max_payload_bytes,
    )
