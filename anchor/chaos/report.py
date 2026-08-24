"""Report computation (plan.md P8.5, T512-T516).

Every figure is computed live from `run_events`, `tool_journal`,
`chaos_events`, and `runs` at write time — never from `metrics_rollup`
(display-only and rebuildable, `anchor.api.serializers.rollup`'s own
docstring says as much) and never carried over from the harness's own
in-memory bookkeeping. This is the permanent, immutable evidence row; it
has to be right independent of whatever the harness process happened to
observe while it ran.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from typing import Any

import asyncpg

from anchor.chaos.invariants import (
    AllInvariants,
    duplicate_effect_count,
    run_all,
    stranded_run_count,
)


@dataclass(frozen=True, slots=True)
class RecoveryPercentiles:
    p50: int
    p95: int
    p99: int
    max: int


async def _recovery_percentiles(
    conn: asyncpg.Connection[Any], *, chaos_run_id: int
) -> RecoveryPercentiles | None:
    """Recovery latency, per kill: from a `worker_kill` `chaos_events` row's
    `created_at` to the earliest `RUN_CLAIMED` event, for any of that kill's
    `affected_run_ids`, whose `created_at` is later than the kill
    (data-model.md §6 — this table is one of the two inputs to this figure,
    not documentation of the experiment). `None` when no kill occurred —
    `chaos_reports`'s own `CHECK` requires exactly that.
    """
    rows = await conn.fetch(
        """
        SELECT ce.id, ce.created_at AS killed_at,
               (
                   SELECT min(re.created_at)
                   FROM run_events re
                   WHERE re.run_id = ANY(ce.affected_run_ids)
                     AND re.type = 'RUN_CLAIMED'
                     AND re.created_at > ce.created_at
               ) AS reclaimed_at
        FROM chaos_events ce
        WHERE ce.chaos_run_id = $1 AND ce.type = 'worker_kill'
        """,
        chaos_run_id,
    )
    samples_ms = [
        (r["reclaimed_at"] - r["killed_at"]).total_seconds() * 1000
        for r in rows
        if r["reclaimed_at"] is not None
    ]
    if not samples_ms:
        return None
    samples_ms.sort()
    return RecoveryPercentiles(
        p50=round(_percentile(samples_ms, 0.50)),
        p95=round(_percentile(samples_ms, 0.95)),
        p99=round(_percentile(samples_ms, 0.99)),
        max=round(max(samples_ms)),
    )


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = fraction * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


async def _replay_overhead(
    conn: asyncpg.Connection[Any], *, run_ids: list[int]
) -> tuple[float | None, float | None]:
    """Mean steps replayed per resumption and mean replay latency, from
    every `REPLAY_COMPLETED` event these runs produced.
    """
    if not run_ids:
        return None, None
    rows = await conn.fetch(
        """
        SELECT payload->>'steps_replayed' AS steps_replayed,
               payload->>'replay_ms' AS replay_ms
        FROM run_events
        WHERE run_id = ANY($1) AND type = 'REPLAY_COMPLETED'
        """,
        run_ids,
    )
    if not rows:
        return None, None
    steps = [float(r["steps_replayed"]) for r in rows]
    latencies = [float(r["replay_ms"]) for r in rows]
    return statistics.mean(steps), statistics.mean(latencies)


async def _throughput(
    conn: asyncpg.Connection[Any], *, run_ids: list[int], duration_seconds: int
) -> tuple[int, float | None]:
    if not run_ids:
        return 0, None
    steps_total = await conn.fetchval(
        "SELECT count(*) FROM run_events WHERE run_id = ANY($1) AND type = 'STEP_COMPLETED'",
        run_ids,
    )
    steps_total = int(steps_total)
    steps_per_second = steps_total / duration_seconds if duration_seconds > 0 else None
    return steps_total, steps_per_second


async def _fencing_events(conn: asyncpg.Connection[Any], *, run_ids: list[int]) -> int:
    if not run_ids:
        return 0
    count = await conn.fetchval(
        "SELECT count(*) FROM run_events WHERE run_id = ANY($1) AND type = 'WORKER_FENCED'",
        run_ids,
    )
    return int(count)


async def _uncertainty_entries(conn: asyncpg.Connection[Any], *, run_ids: list[int]) -> dict[str, int]:
    if not run_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT payload->>'resolution' AS resolution, count(*) AS n
        FROM run_events
        WHERE run_id = ANY($1) AND type = 'TOOL_RESULT' AND payload->>'resolution' IS NOT NULL
        GROUP BY payload->>'resolution'
        """,
        run_ids,
    )
    return {r["resolution"]: int(r["n"]) for r in rows}


async def _dead_letter_count(conn: asyncpg.Connection[Any], *, run_ids: list[int]) -> int:
    if not run_ids:
        return 0
    count = await conn.fetchval(
        "SELECT count(*) FROM runs WHERE id = ANY($1) AND status = 'failed'", run_ids
    )
    return int(count)


@dataclass(frozen=True, slots=True)
class ChaosReport:
    chaos_run_id: int
    invariants: AllInvariants
    duplicate_effect_count: int
    stranded_run_count: int
    kills_injected: int
    runs_total: int
    steps_total: int
    recovery: RecoveryPercentiles | None
    replay_steps_mean: float | None
    replay_ms_mean: float | None
    steps_per_second: float | None
    fencing_events: int
    uncertainty_entries: dict[str, int]
    dead_letter_count: int
    duration_seconds: int


async def compute_report(
    conn: asyncpg.Connection[Any],
    *,
    chaos_run_id: int,
    run_ids: list[int],
    duration_seconds: int,
) -> ChaosReport:
    invariants = await run_all(conn, run_ids=run_ids, bound_seconds=max(float(duration_seconds) * 2.0, 120.0))

    kills_injected = await conn.fetchval(
        "SELECT count(*) FROM chaos_events WHERE chaos_run_id = $1 AND type = 'worker_kill'",
        chaos_run_id,
    )
    steps_total, steps_per_second = await _throughput(
        conn, run_ids=run_ids, duration_seconds=duration_seconds
    )
    replay_steps_mean, replay_ms_mean = await _replay_overhead(conn, run_ids=run_ids)

    return ChaosReport(
        chaos_run_id=chaos_run_id,
        invariants=invariants,
        duplicate_effect_count=await duplicate_effect_count(conn),
        stranded_run_count=await stranded_run_count(conn, run_ids=run_ids),
        kills_injected=int(kills_injected),
        runs_total=len(run_ids),
        steps_total=steps_total,
        recovery=await _recovery_percentiles(conn, chaos_run_id=chaos_run_id),
        replay_steps_mean=replay_steps_mean,
        replay_ms_mean=replay_ms_mean,
        steps_per_second=steps_per_second,
        fencing_events=await _fencing_events(conn, run_ids=run_ids),
        uncertainty_entries=await _uncertainty_entries(conn, run_ids=run_ids),
        dead_letter_count=await _dead_letter_count(conn, run_ids=run_ids),
        duration_seconds=duration_seconds,
    )


async def persist_report(conn: asyncpg.Connection[Any], report: ChaosReport) -> None:
    """Write `chaos_reports` — immutable from this point on
    (`006_chaos.py`'s `chaos_reports_immutable_trigger`); this is the only
    `INSERT` this table ever receives for a given `chaos_run_id`, since a
    completed chaos run is never re-reported.
    """
    recovery = report.recovery
    await conn.execute(
        """
        INSERT INTO chaos_reports (
            chaos_run_id, inv_no_duplicate_effects, inv_log_monotonic,
            inv_single_writer_per_epoch, inv_terminal_reachability, inv_replay_determinism,
            violations, duplicate_effect_count, stranded_run_count, kills_injected,
            runs_total, steps_total, recovery_ms_p50, recovery_ms_p95, recovery_ms_p99,
            recovery_ms_max, replay_steps_mean, replay_ms_mean, steps_per_second,
            fencing_events, uncertainty_entries, dead_letter_count, duration_seconds
        )
        VALUES (
            $1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11, $12, $13, $14, $15, $16,
            $17, $18, $19, $20, $21::jsonb, $22, $23
        )
        """,
        report.chaos_run_id,
        report.invariants.no_duplicate_effects.passed,
        report.invariants.log_monotonic.passed,
        report.invariants.single_writer_per_epoch.passed,
        report.invariants.terminal_reachability.passed,
        report.invariants.replay_determinism.passed,
        json.dumps(report.invariants.violations),
        report.duplicate_effect_count,
        report.stranded_run_count,
        report.kills_injected,
        report.runs_total,
        report.steps_total,
        recovery.p50 if recovery else None,
        recovery.p95 if recovery else None,
        recovery.p99 if recovery else None,
        recovery.max if recovery else None,
        report.replay_steps_mean,
        report.replay_ms_mean,
        report.steps_per_second,
        report.fencing_events,
        json.dumps(report.uncertainty_entries),
        report.dead_letter_count,
        report.duration_seconds,
    )
