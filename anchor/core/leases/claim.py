"""The claim statement — many identical workers, one shared queue, no
central coordinator (plan.md P3.1, research.md D-10, D-44).

**Transaction boundary.** Everything in `claim_one` — the candidate select,
the ownership/epoch/lease update, and the `RUN_CLAIMED` append — commits as
one transaction (`I4`). Nothing observes the intermediate state in which a
row is locked but not yet claimed, because the row lock taken by
`FOR UPDATE SKIP LOCKED` is held to commit. Two workers racing for the same
row therefore never both see it as available: one gets the lock and
proceeds, the other's scan skips the locked row and looks at the next
candidate instead.

**One statement, not two queries** (constitution, Principle II). The select
and the ownership update are expressed as a single `WITH ... UPDATE ...`
statement — a candidate is chosen and claimed without a round trip in
between in which another worker's scan could observe it as still eligible.
The `RUN_CLAIMED` append is a second statement in the same transaction,
deliberately reusing `core.events.append` rather than a duplicated insert,
so the claim event goes through the same counter and the same trigger as
every other event in the run's log (D-10's rationale: uniform enforcement,
not a special case).

**The global concurrency cap gates admission, not reclaim** (D-44, with a
correction to its literal pseudocode — stated here). D-44 writes the cap
check as `AND (SELECT count(*) ...) < $cap` applied to the *combined*
`pending OR expired-lease` predicate. Applied literally, that gates
reclaiming an orphaned run behind the same cap as admitting a new one — but
a reclaim does not change the running count at all: the row is already
`running` (with an expired lease) before the claim, and stays `running`
(with a new owner and epoch) after it. Gating reclaim on `count < cap` means
that at a fully saturated fleet (`count == cap`), a run whose worker died
could never be reclaimed by anyone, because the count — which already
includes the dead run's own row — never drops below `cap`. That is a
liveness bug: it strands runs permanently at exactly the load level chaos
testing exists to prove survivable. The cap predicate below therefore
applies to the `pending` branch only; the expired-lease branch is ungated,
because admitting it never grows the running count.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

import asyncpg

from anchor.core.events.append import append
from anchor.core.events.types import EventType

# One statement: choose the highest-priority eligible candidate — pending
# (under the cap), or running with an expired lease — and claim it in the
# same UPDATE. The CTE's row lock (FOR UPDATE SKIP LOCKED) is what makes
# "choose" and "claim" atomic without a second round trip: nothing can
# observe `candidate` without also being able to complete the UPDATE inside
# this one statement.
#
# The cap subquery is scalar and uncorrelated with the candidate row, so
# PostgreSQL evaluates it once (an InitPlan) rather than once per candidate.
_CLAIM_SQL = """
WITH candidate AS (
    SELECT id, agent_type, input, epoch, status, owner_worker_id
    FROM runs
    WHERE
        (
            status = 'pending'
            AND (SELECT count(*) FROM runs WHERE status = 'running') < $3
        )
        OR (status = 'running' AND lease_expires_at < now())
    ORDER BY priority ASC, created_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
UPDATE runs r
SET epoch = c.epoch + 1,
    owner_worker_id = $1,
    lease_expires_at = now() + ($2 || ' milliseconds')::interval,
    status = 'running',
    claimed_at = now()
FROM candidate c
WHERE r.id = c.id
RETURNING
    r.id AS run_id,
    r.agent_type,
    r.input,
    r.epoch AS new_epoch,
    r.lease_expires_at AS lease_expires_at,
    c.status AS previous_status,
    c.owner_worker_id AS previous_worker_id
"""


@dataclass(frozen=True, slots=True)
class ClaimedRun:
    run_id: int
    agent_type: str
    input: dict[str, Any]
    epoch: int
    reason: Literal["initial", "reclaimed_after_lease_expiry"]
    previous_worker_id: str | None


async def claim_one(
    conn: asyncpg.Connection[Any],
    *,
    worker_id: str,
    lease_duration_ms: int,
    global_concurrency_cap: int,
    max_payload_bytes: int,
) -> ClaimedRun | None:
    """Claim one eligible run — new or reclaimed — and append `RUN_CLAIMED`
    in the same transaction as the ownership change (`I4`). Returns `None`
    when nothing is eligible (nothing pending under the cap, and no expired
    lease to reclaim).

    Crash behaviour: a crash at any point before this transaction commits
    leaves the run exactly as it was — `pending`, or `running` under its
    previous owner until that owner's lease also expires. There is no
    partial claim: the UPDATE and the `RUN_CLAIMED` append are the only two
    statements in the transaction, and PostgreSQL guarantees both land or
    neither does.
    """
    async with conn.transaction():
        row = await conn.fetchrow(
            _CLAIM_SQL,
            worker_id,
            str(lease_duration_ms),
            global_concurrency_cap,
        )
        if row is None:
            return None

        reason: Literal["initial", "reclaimed_after_lease_expiry"] = (
            "reclaimed_after_lease_expiry" if row["previous_status"] == "running" else "initial"
        )

        await append(
            conn,
            run_id=row["run_id"],
            type=EventType.RUN_CLAIMED,
            payload={
                "worker_id": worker_id,
                "epoch": row["new_epoch"],
                "reason": reason,
                "lease_expires_at": row["lease_expires_at"].isoformat(),
                "previous_worker_id": row["previous_worker_id"],
            },
            epoch=row["new_epoch"],
            worker_id=worker_id,
            max_payload_bytes=max_payload_bytes,
        )

        return ClaimedRun(
            run_id=row["run_id"],
            agent_type=row["agent_type"],
            input=json.loads(row["input"]),
            epoch=row["new_epoch"],
            reason=reason,
            previous_worker_id=row["previous_worker_id"],
        )
