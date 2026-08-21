"""`GET /api/metrics`, `GET /api/events`, and `GET /api/health`'s siblings
(plan.md P6.11, T355-T358; FR-071, FR-026, FR-072;
contracts/openapi.yaml `Metrics`, `RunEvent`).

**The line every read in this file respects** (D-49, T356): the display
time series inside `Metrics` come from `metrics_rollup`; `duplicate_side_effects`
and `stranded_runs` are computed live from `run_events`/`runs`, every call,
never from the rollup. A comment marks each query with which side of that
line it is on.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends, Request

from anchor.api.errors import ApiError
from anchor.api.serializers.rollup import HISTOGRAM_EDGES_MS
from anchor.core.config.loader import load_runtime_settings

router = APIRouter()

_WINDOW_SECONDS: dict[str, int] = {
    "1h": 3_600,
    "24h": 86_400,
    "7d": 7 * 86_400,
    "30d": 30 * 86_400,
}

# The two resolutions metrics_rollup maintains (migration 004): 10s buckets
# for the short window, where enough buckets exist to be worth the finer
# grain, 300s (5 min) for everything longer, so a 30-day window is ~8,640
# buckets rather than ~2.6 million.
_RESOLUTION_FOR_WINDOW: dict[str, int] = {"1h": 10, "24h": 300, "7d": 300, "30d": 300}


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


def _empty_histogram_bins() -> list[int]:
    return [0] * len(HISTOGRAM_EDGES_MS)


def _histogram_from_bins(bins_count: list[int]) -> dict[str, Any]:
    total = sum(bins_count)
    edges = [*list(HISTOGRAM_EDGES_MS), None]
    bins = [
        {
            "lower_ms": edges[i],
            "upper_ms": edges[i + 1],
            "count": bins_count[i],
        }
        for i in range(len(HISTOGRAM_EDGES_MS))
    ]

    def _percentile(p: float) -> int | None:
        if total == 0:
            return None
        target = p * total
        cumulative = 0
        for i, count in enumerate(bins_count):
            cumulative += count
            if cumulative >= target:
                # The bin's lower edge is a conservative, honest estimate —
                # this is a display histogram, not a correctness read, and
                # a fixed-bin rollup cannot recover exact values.
                return HISTOGRAM_EDGES_MS[i]
        return HISTOGRAM_EDGES_MS[-1]

    return {
        "bins": bins,
        "p50": _percentile(0.50),
        "p95": _percentile(0.95),
        "p99": _percentile(0.99),
    }


@router.get("/api/metrics")
async def get_metrics(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    request: Request,
    window: str = "24h",
) -> dict[str, Any]:
    """`contracts/openapi.yaml` `Metrics`. `throughput_by_worker_count` is
    omitted: it plots one measured line per distinct worker-fleet size,
    which only a deliberately varied chaos run produces (phase 8) — there
    is no live-fleet data source for it here, and the field is optional.
    """
    if window not in _WINDOW_SECONDS:
        window = "24h"
    window_seconds = _WINDOW_SECONDS[window]
    bucket_seconds = _RESOLUTION_FOR_WINDOW[window]

    async with pool.acquire() as conn:
        settings = await load_runtime_settings(conn)

        # --- Correctness reads: live, every call, never from the rollup
        # below (D-30/D-49/T356). ---
        duplicate_side_effects = await conn.fetchval(
            """
            SELECT count(*) FROM run_events
            WHERE type = 'STEP_SKIPPED_ON_REPLAY' AND created_at > now() - ($1 * interval '1 second')
            """,
            window_seconds,
        )
        stranded_runs = await conn.fetchval(
            "SELECT count(*) FROM runs WHERE status = 'running' AND lease_expires_at < now()"
        )
        runs_total = await conn.fetchval(
            """
            SELECT count(*) FROM run_events
            WHERE type = 'RUN_SUBMITTED' AND created_at > now() - ($1 * interval '1 second')
            """,
            window_seconds,
        )

        # --- Display series: from metrics_rollup only (D-49). ---
        rollup_rows = await conn.fetch(
            """
            SELECT bucket_start, metric, dimension, count, sum_value, histogram
            FROM metrics_rollup
            WHERE bucket_seconds = $1 AND bucket_start > now() - ($2 * interval '1 second')
            ORDER BY bucket_start ASC
            """,
            bucket_seconds,
            window_seconds,
        )

    steps_total = 0
    steps_per_second_by_worker: dict[str, float] = {}
    run_state_by_bucket: dict[str, dict[str, int]] = {}
    fencing_events_series: list[dict[str, Any]] = []
    uncertainty_by_policy: dict[str, int] = {}
    dead_letters_by_reason: dict[str, int] = {}
    recovery_bins = _empty_histogram_bins()
    lease_renewal_bins = _empty_histogram_bins()
    replay_steps_total = 0
    replay_steps_events = 0
    replay_ms_total = 0.0
    replay_ms_events = 0

    for row in rollup_rows:
        metric = row["metric"]
        dimension = row["dimension"]
        count = row["count"]
        bucket_key = row["bucket_start"].isoformat()

        if metric == "steps_completed":
            steps_total += count
            if dimension:
                steps_per_second_by_worker[dimension] = (
                    steps_per_second_by_worker.get(dimension, 0.0) + count
                )
        elif metric == "runs_by_status":
            run_state_by_bucket.setdefault(bucket_key, {})[dimension] = (
                run_state_by_bucket.setdefault(bucket_key, {}).get(dimension, 0) + count
            )
        elif metric == "uncertainty_entries":
            uncertainty_by_policy[dimension] = uncertainty_by_policy.get(dimension, 0) + count
        elif metric == "dead_letters":
            dead_letters_by_reason[dimension] = dead_letters_by_reason.get(dimension, 0) + count
        elif metric == "fencing_events":
            fencing_events_series.append({"bucket": bucket_key, "count": count})
        elif metric == "replay_steps":
            replay_steps_total += count
            replay_steps_events += 1
        elif metric == "replay_ms" and row["sum_value"] is not None:
            replay_ms_total += float(row["sum_value"])
            replay_ms_events += 1
        elif metric in ("recovery_ms", "lease_renewal_ms") and row["histogram"] is not None:
            target_bins = recovery_bins if metric == "recovery_ms" else lease_renewal_bins
            bucket_histogram: dict[str, int] = json.loads(row["histogram"])
            for edge_str, bin_count in bucket_histogram.items():
                edge_index = HISTOGRAM_EDGES_MS.index(int(edge_str))
                target_bins[edge_index] += bin_count

    # Live aggregation fallback for fresh local setups where rollup hasn't ticked yet
    if not rollup_rows:
        async with pool.acquire() as conn:
            live_steps = await conn.fetchval(
                "SELECT count(*) FROM run_events WHERE type = 'STEP_COMPLETED' AND created_at > now() - ($1 * interval '1 second')",
                window_seconds,
            )
            steps_total = int(live_steps or 0)
            status_rows = await conn.fetch("SELECT status, count(*) as count FROM runs GROUP BY status")
            if status_rows:
                run_state_by_bucket[datetime.utcnow().isoformat()] = {
                    row["status"]: int(row["count"]) for row in status_rows
                }
            live_fencing = await conn.fetchval(
                "SELECT count(*) FROM run_events WHERE type = 'WORKER_FENCED' AND created_at > now() - ($1 * interval '1 second')",
                window_seconds,
            )
            if live_fencing:
                fencing_events_series = [{"bucket": datetime.utcnow().isoformat(), "count": int(live_fencing)}]

    steps_per_second = steps_total / window_seconds if window_seconds else 0.0
    for worker_id in steps_per_second_by_worker:
        steps_per_second_by_worker[worker_id] = (
            steps_per_second_by_worker[worker_id] / window_seconds
        )

    active_profile: str = getattr(request.app.state, "config_profile", "unknown")

    return {
        "window": window,
        "duplicate_side_effects": int(duplicate_side_effects),
        "stranded_runs": int(stranded_runs),
        "runs_total": int(runs_total),
        "steps_total": steps_total,
        "steps_per_second": steps_per_second,
        "steps_per_second_by_worker": steps_per_second_by_worker,
        "run_state_distribution": [
            {"bucket": bucket, "counts": counts}
            for bucket, counts in sorted(run_state_by_bucket.items())
        ],
        "recovery_ms_histogram": _histogram_from_bins(recovery_bins),
        "lease_renewal_ms_histogram": _histogram_from_bins(lease_renewal_bins),
        "replay_steps_mean": (replay_steps_total / replay_steps_events)
        if replay_steps_events
        else 0.0,
        "replay_ms_mean": (replay_ms_total / replay_ms_events) if replay_ms_events else 0.0,
        "fencing_events_series": fencing_events_series,
        "uncertainty_by_policy": uncertainty_by_policy,
        "dead_letter_reasons": [
            {"error_type": error_type, "count": count}
            for error_type, count in sorted(dead_letters_by_reason.items())
        ],
        "active_profile": active_profile,
        "lease_duration_ms": settings.lease_duration_ms,
    }


def _encode_events_cursor(created_at: datetime, run_id: int, seq: int) -> str:
    raw = f"{created_at.isoformat()}|{run_id}|{seq}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_events_cursor(cursor: str) -> tuple[datetime, int, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        created_at_str, run_id_str, seq_str = raw.split("|")
        return datetime.fromisoformat(created_at_str), int(run_id_str), int(seq_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ApiError(
            status_code=422, error="malformed_cursor", message="malformed cursor"
        ) from exc


@router.get("/api/events")
async def get_events(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    type: list[str] | None = None,
    worker_id: str | None = None,
    epoch: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Global search over `run_events` (FR-026), across every run —
    distinct from `GET /api/runs/{id}/events`, which is scoped to one.

    `LEASE_RENEWED` is excluded whenever `type` is not given: at a
    1-second renewal interval across a real fleet it would be the
    majority of rows returned, and it is the one event type replay never
    even consumes (T119) — an operator searching the log is almost never
    looking for it. Passing `type=LEASE_RENEWED` explicitly still reaches
    it; nothing is hidden, only deprioritized by default.
    """
    page_size = min(limit, 500)
    async with pool.acquire() as conn:
        clauses = []
        params: list[Any] = []
        if type:
            params.append(type)
            clauses.append(f"type = ANY(${len(params)})")
        else:
            clauses.append("type <> 'LEASE_RENEWED'")
        if worker_id:
            params.append(worker_id)
            clauses.append(f"worker_id = ${len(params)}")
        if epoch is not None:
            params.append(epoch)
            clauses.append(f"epoch = ${len(params)}")
        if since is not None:
            params.append(since)
            clauses.append(f"created_at >= ${len(params)}")
        if until is not None:
            params.append(until)
            clauses.append(f"created_at <= ${len(params)}")
        if cursor is not None:
            cursor_created_at, cursor_run_id, cursor_seq = _decode_events_cursor(cursor)
            params.append(cursor_created_at)
            params.append(cursor_run_id)
            params.append(cursor_seq)
            clauses.append(
                f"(created_at, run_id, seq) < (${len(params) - 2}, ${len(params) - 1}, ${len(params)})"
            )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(page_size)
        rows = await conn.fetch(
            f"""
            SELECT run_id, seq, type, payload, epoch, worker_id, step_index, created_at
            FROM run_events
            {where}
            ORDER BY created_at DESC, run_id DESC, seq DESC
            LIMIT ${len(params)}
            """,
            *params,
        )

    items = [
        {
            "run_id": r["run_id"],
            "seq": r["seq"],
            "type": r["type"],
            "payload": json.loads(r["payload"]),
            "epoch": r["epoch"],
            "worker_id": r["worker_id"],
            "step_index": r["step_index"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
    next_cursor = (
        _encode_events_cursor(rows[-1]["created_at"], rows[-1]["run_id"], rows[-1]["seq"])
        if len(rows) == page_size
        else None
    )
    return {"items": items, "next_cursor": next_cursor}
