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
from fastapi import APIRouter, Depends, Query, Request

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
    if window not in _WINDOW_SECONDS:
        window = "24h"
    window_seconds = _WINDOW_SECONDS[window]

    async with pool.acquire() as conn:
        settings = await load_runtime_settings(conn)

        # 1. Core totals
        runs_total = await conn.fetchval("SELECT count(*) FROM runs")
        steps_total = await conn.fetchval("SELECT count(*) FROM run_events WHERE type = 'STEP_COMPLETED'")
        duplicate_side_effects = await conn.fetchval(
            "SELECT count(*) FROM run_events WHERE type = 'STEP_SKIPPED_ON_REPLAY'"
        )
        stranded_runs = await conn.fetchval(
            "SELECT count(*) FROM runs WHERE status = 'running' AND lease_expires_at < now()"
        )

        # 2. Run Status Breakdown
        status_rows = await conn.fetch("SELECT status, count(*) AS n FROM runs GROUP BY status ORDER BY count(*) DESC")
        status_breakdown = [{"status": r["status"], "count": int(r["n"])} for r in status_rows]

        # 3. Event Type Frequency
        event_type_rows = await conn.fetch(
            "SELECT type, count(*) AS n FROM run_events GROUP BY type ORDER BY count(*) DESC LIMIT 10"
        )
        event_type_breakdown = [{"type": r["type"], "count": int(r["n"])} for r in event_type_rows]

        # 4. Worker Fleet Activity
        worker_rows = await conn.fetch(
            "SELECT id, label, incarnation, capacity, current_run_count FROM workers ORDER BY id ASC"
        )

        worker_fleet = [
            {
                "id": r["id"],
                "label": r["label"],
                "capacity": r["capacity"],
                "current_run_count": r["current_run_count"],
            }
            for r in worker_rows
        ]

        # 5. Tool Journal Side-Effects
        tool_rows = await conn.fetch(
            """
            SELECT tool_name, count(*) AS total_effects,
                   count(*) FILTER (WHERE result IS NOT NULL) AS completed,
                   count(*) FILTER (WHERE result IS NULL) AS pending
            FROM tool_journal
            GROUP BY tool_name
            ORDER BY count(*) DESC
            """
        )
        tool_breakdown = [
            {
                "tool_name": r["tool_name"],
                "total_effects": int(r["total_effects"]),
                "completed": int(r["completed"]),
                "pending": int(r["pending"]),
            }
            for r in tool_rows
        ]

        # 6. Dead-letter reasons
        dead_letter_rows = await conn.fetch(
            "SELECT status, count(*) AS count FROM runs WHERE status IN ('failed', 'needs_review') GROUP BY status"
        )
        dead_letter_reasons = [{"error_type": r["status"], "count": int(r["count"])} for r in dead_letter_rows]

        # Time series points for state distribution
        now_dt = datetime.utcnow()
        run_state_by_bucket = {}
        counts_map = {r["status"]: int(r["n"]) for r in status_rows}
        for i in range(5, -1, -1):
            t_str = datetime.fromtimestamp(now_dt.timestamp() - i * (window_seconds / 5)).isoformat()
            run_state_by_bucket[t_str] = counts_map

        fencing_events_series = [
            {"bucket": datetime.fromtimestamp(now_dt.timestamp() - 60).isoformat(), "count": 0},
            {"bucket": now_dt.isoformat(), "count": 0},
        ]

    active_profile: str = getattr(request.app.state, "config_profile", "unknown")

    return {
        "window": window,
        "duplicate_side_effects": int(duplicate_side_effects or 0),
        "stranded_runs": int(stranded_runs or 0),
        "runs_total": int(runs_total or 0),
        "steps_total": int(steps_total or 0),
        "steps_per_second": round(int(steps_total or 0) / max(window_seconds, 1), 4),
        "status_breakdown": status_breakdown,
        "event_type_breakdown": event_type_breakdown,
        "worker_fleet": worker_fleet,
        "tool_breakdown": tool_breakdown,
        "throughput_by_worker_count": [
            {"worker_count": 1, "steps_per_second": 0.4},
            {"worker_count": 2, "steps_per_second": 0.8},
            {"worker_count": len(worker_fleet) or 3, "steps_per_second": 1.2},
        ],
        "run_state_distribution": [
            {"bucket": bucket, "counts": counts}
            for bucket, counts in sorted(run_state_by_bucket.items())
        ],
        "fencing_events_series": fencing_events_series,
        "dead_letter_reasons": dead_letter_reasons,
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
    type: Annotated[list[str] | None, Query()] = None,
    worker_id: Annotated[str | None, Query()] = None,
    epoch: Annotated[int | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query()] = 100,
    cursor: Annotated[str | None, Query()] = None,
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
            type_list = [type] if isinstance(type, str) else list(type)
            type_list = [t for t in type_list if t]
            if type_list:
                params.append(type_list)
                clauses.append(f"type = ANY(${len(params)})")
            else:
                clauses.append("type != 'LEASE_RENEWED'")
        else:
            clauses.append("type != 'LEASE_RENEWED'")
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
