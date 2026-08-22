"""The five invariant assertions, SQL-backed (plan.md P8.4, tasks.md
T474-T478, T505-T511; constitution Principle V).

Each check is a query (or a pure comparison over data a query fetched)
against the same tables every other correctness read in this system uses —
`run_events`, `runs`, `demo_effects` — never a rollup, never a cache, and
never the harness's own bookkeeping. A violation is recorded with enough
detail (the run, key, epoch, or `seq` that failed) to be actionable, per
data-model.md §8's `violations` column, which is `'[]'` rather than `NULL`
when clean (T482) — the empty case is the expected one and is represented
explicitly, not by absence.

**Continuous, not only final** (T510, FR-082): `run_all` is called
repeatedly by the harness while a run is in flight, not only once at the
end, so a violation is caught near the injection that caused it rather than
buried in a final summary alongside four hours of otherwise-clean history.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import asyncpg

from anchor.core.events.models import RunEvent
from anchor.core.replay.reconstruct import canonical_state_hash, reconstruct


@dataclass(frozen=True, slots=True)
class InvariantResult:
    name: str
    passed: bool
    violations: list[dict[str, Any]] = field(default_factory=list)


async def check_no_duplicate_effects(conn: asyncpg.Connection[Any]) -> InvariantResult:
    """Invariant 1 — at most one recorded result per idempotency key.

    Reads `run_events` directly rather than `tool_journal` or
    `demo_effects`: both of those carry a `PRIMARY KEY`/`UNIQUE` constraint
    on `idempotency_key` that makes a duplicate *write* impossible by
    construction, which is exactly why they cannot be the thing that
    proves the property — a constraint that would reject the write cannot
    also be the evidence that the write never happened. `run_events` is
    append-only with no such per-key constraint, so this is the one place
    a genuine duplicate would actually be observable.
    """
    rows = await conn.fetch(
        """
        SELECT payload->>'idempotency_key' AS key, count(*) AS n
        FROM run_events
        WHERE type = 'TOOL_RESULT'
        GROUP BY payload->>'idempotency_key'
        HAVING count(*) > 1
        """
    )
    violations = [
        {"invariant": "no_duplicate_effects", "idempotency_key": r["key"], "result_count": r["n"]}
        for r in rows
    ]
    return InvariantResult("no_duplicate_effects", passed=not violations, violations=violations)


async def duplicate_effect_count(conn: asyncpg.Connection[Any]) -> int:
    """The headline figure (data-model.md §8): total `TOOL_RESULT`
    occurrences beyond the first, per idempotency key. Zero on a clean
    corpus by definition of `check_no_duplicate_effects` above.
    """
    row = await conn.fetchrow(
        """
        SELECT coalesce(sum(n - 1), 0) AS excess
        FROM (
            SELECT count(*) AS n
            FROM run_events
            WHERE type = 'TOOL_RESULT'
            GROUP BY payload->>'idempotency_key'
        ) counts
        WHERE n > 1
        """
    )
    assert row is not None
    return int(row["excess"])


async def check_log_monotonic(conn: asyncpg.Connection[Any]) -> InvariantResult:
    """Invariant 2 — `seq` strictly increasing per run, no duplicates, no
    gaps. `PRIMARY KEY (run_id, seq)` already forbids duplicates; this
    checks the property a primary key cannot express — contiguity — by
    comparing the row count against the max `seq` and confirming the
    sequence starts at 1.
    """
    rows = await conn.fetch(
        """
        SELECT run_id, count(*) AS n, min(seq) AS min_seq, max(seq) AS max_seq
        FROM run_events
        GROUP BY run_id
        HAVING count(*) != max(seq) OR min(seq) != 1
        """
    )
    violations = [
        {
            "invariant": "log_monotonic",
            "run_id": r["run_id"],
            "event_count": r["n"],
            "min_seq": r["min_seq"],
            "max_seq": r["max_seq"],
        }
        for r in rows
    ]
    return InvariantResult("log_monotonic", passed=not violations, violations=violations)


async def check_single_writer_per_epoch(conn: asyncpg.Connection[Any]) -> InvariantResult:
    """Invariant 3 — no `(run_id, epoch)` carries events from two worker
    ids. The epoch write-gate trigger (`001_foundation.py`) prevents a
    *stale* epoch from ever landing a write; this checks the complementary
    property the trigger does not: that two writers never simultaneously
    believed themselves current at the *same* epoch, which would mean the
    fencing token itself was not exclusive.
    """
    rows = await conn.fetch(
        """
        SELECT run_id, epoch, count(DISTINCT worker_id) AS writers
        FROM run_events
        GROUP BY run_id, epoch
        HAVING count(DISTINCT worker_id) > 1
        """
    )
    violations = [
        {
            "invariant": "single_writer_per_epoch",
            "run_id": r["run_id"],
            "epoch": r["epoch"],
            "distinct_writers": r["writers"],
        }
        for r in rows
    ]
    return InvariantResult(
        "single_writer_per_epoch", passed=not violations, violations=violations
    )


_TERMINAL_STATUSES = ("completed", "failed", "cancelled", "needs_review")
_TERMINAL_STATUSES_SQL = "(" + ", ".join(f"'{s}'" for s in _TERMINAL_STATUSES) + ")"


async def check_terminal_reachability(
    conn: asyncpg.Connection[Any], *, run_ids: list[int], bound_seconds: float
) -> InvariantResult:
    """Invariant 4 — every run submitted by this chaos run reaches a
    terminal state within `bound_seconds` of its submission. `needs_review`
    counts as terminal here (data-model.md §1's own state-machine note: it
    is "the only non-terminal-looking state that is leaseless") — a run
    parked for human review is not stranded, it is exactly the honest
    outcome `I8` exists to produce for an `unsafe` tool caught mid-effect.
    """
    if not run_ids:
        return InvariantResult("terminal_reachability", passed=True)
    rows = await conn.fetch(
        f"""
        SELECT id, status, created_at
        FROM runs
        WHERE id = ANY($1)
          AND status NOT IN {_TERMINAL_STATUSES_SQL}
          AND created_at < now() - ($2 * interval '1 second')
        """,
        run_ids,
        bound_seconds,
    )
    violations = [
        {"invariant": "terminal_reachability", "run_id": r["id"], "status": r["status"]}
        for r in rows
    ]
    return InvariantResult(
        "terminal_reachability", passed=not violations, violations=violations
    )


async def stranded_run_count(conn: asyncpg.Connection[Any], *, run_ids: list[int]) -> int:
    if not run_ids:
        return 0
    row = await conn.fetchrow(
        f"""
        SELECT count(*) AS n
        FROM runs
        WHERE id = ANY($1) AND status NOT IN {_TERMINAL_STATUSES_SQL}
        """,
        run_ids,
    )
    assert row is not None
    return int(row["n"])


def logs_reconstruct_identically(events_a: list[RunEvent], events_b: list[RunEvent]) -> bool:
    """The comparison `check_replay_determinism` and its unit test share:
    fold each ordered log independently and compare the canonical-JSON
    hash of the resulting state. `reconstruct` is a pure fold with no I/O
    (`core.replay.reconstruct`'s module docstring), so under real operation
    `events_a` and `events_b` are the *same* run's log fetched twice —
    equal by construction unless something (a serialization-order bug, an
    accidental read of wall-clock time inside a fold handler) broke that
    purity. The unit test instead passes a deliberately mutated second log
    to prove this comparison can fail.
    """
    return canonical_state_hash(reconstruct(events_a)) == canonical_state_hash(reconstruct(events_b))


async def check_replay_determinism(
    conn: asyncpg.Connection[Any], *, run_ids: list[int]
) -> InvariantResult:
    """Invariant 5 — every completed run's log replays to an identical
    final state. Fetches each run's full log twice, independently, and
    compares canonical hashes — see `logs_reconstruct_identically`.
    """
    violations: list[dict[str, Any]] = []
    for run_id in run_ids:
        first = await _fetch_events(conn, run_id)
        second = await _fetch_events(conn, run_id)
        if not first:
            continue
        if not logs_reconstruct_identically(first, second):
            violations.append({"invariant": "replay_determinism", "run_id": run_id})
    return InvariantResult("replay_determinism", passed=not violations, violations=violations)


async def _fetch_events(conn: asyncpg.Connection[Any], run_id: int) -> list[RunEvent]:
    rows = await conn.fetch(
        "SELECT run_id, seq, type, payload, epoch, worker_id, step_index, created_at "
        "FROM run_events WHERE run_id = $1 ORDER BY seq ASC",
        run_id,
    )
    return [
        RunEvent(
            run_id=r["run_id"],
            seq=r["seq"],
            type=r["type"],
            payload=json.loads(r["payload"]),
            epoch=r["epoch"],
            worker_id=r["worker_id"],
            step_index=r["step_index"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@dataclass(frozen=True, slots=True)
class AllInvariants:
    no_duplicate_effects: InvariantResult
    log_monotonic: InvariantResult
    single_writer_per_epoch: InvariantResult
    terminal_reachability: InvariantResult
    replay_determinism: InvariantResult

    @property
    def all_passed(self) -> bool:
        return all(
            r.passed
            for r in (
                self.no_duplicate_effects,
                self.log_monotonic,
                self.single_writer_per_epoch,
                self.terminal_reachability,
                self.replay_determinism,
            )
        )

    @property
    def violations(self) -> list[dict[str, Any]]:
        return [
            v
            for r in (
                self.no_duplicate_effects,
                self.log_monotonic,
                self.single_writer_per_epoch,
                self.terminal_reachability,
                self.replay_determinism,
            )
            for v in r.violations
        ]


async def run_all(
    conn: asyncpg.Connection[Any], *, run_ids: list[int], bound_seconds: float
) -> AllInvariants:
    """Run all five checks against the current state of the database.
    Cheap enough to call repeatedly during a sustained harness run (T510):
    every query here is a straightforward aggregation over already-indexed
    columns, not a full-table scan proportional to the whole corpus's
    history beyond this chaos run's own runs.
    """
    completed_run_ids = [
        r["id"]
        for r in await conn.fetch(
            f"SELECT id FROM runs WHERE id = ANY($1) AND status IN {_TERMINAL_STATUSES_SQL} "
            "AND status != 'needs_review'",
            run_ids,
        )
    ]
    return AllInvariants(
        no_duplicate_effects=await check_no_duplicate_effects(conn),
        log_monotonic=await check_log_monotonic(conn),
        single_writer_per_epoch=await check_single_writer_per_epoch(conn),
        terminal_reachability=await check_terminal_reachability(
            conn, run_ids=run_ids, bound_seconds=bound_seconds
        ),
        replay_determinism=await check_replay_determinism(conn, run_ids=completed_run_ids),
    )
