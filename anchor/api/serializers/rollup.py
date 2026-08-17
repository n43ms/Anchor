"""The metrics rollup job (plan.md P6.10, T350-T354; D-49, migration 004).

**What this is not.** Nothing here is ever read to answer a correctness
question. The duplicate-effect count, the stranded-run count, the
`needs_review` list, and every chaos-report figure are computed live from
`tool_journal`/`run_events` (`anchor.api.serializers.timeline`,
`anchor.api.routers.observability`) — never from `metrics_rollup`. This
module exists only to make the *display* time series on `GET /api/metrics`
cheap to serve on every dashboard poll without a full scan of `run_events`
each time.

**Watermarked, not triggered** (D-49): `run_rollup_once` reads strictly
above `metrics_rollup_watermark`, upserts buckets, and advances the
watermark in the same transaction. Running this as a periodic task
(`anchor.api.app`'s background loop) rather than an `AFTER INSERT` trigger
on `run_events` is a correctness decision, not a performance one — a
trigger upserting the current bucket on every append would make every
worker contend on the same bucket row, serializing appends across runs
that currently never contend at all.

**`REBUILD` is what proves this table is derived rather than
authoritative** (T353): truncating `metrics_rollup` and its watermark, then
running every event back through the same folding logic from the
beginning of the log, reproduces every bucket exactly. `tests/unit/test_rollup_rebuild_matches_live.py`
is the test that makes this a verified claim rather than an assertion.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

import asyncpg

RESOLUTIONS_SECONDS: tuple[int, int] = (10, 300)

# Shared with `anchor.api.routers.observability`, which reads these back —
# a fixed, canonical bin-edge set (ms) is what makes summing `histogram`
# across buckets in a window a plain per-key addition rather than a
# re-bucketing exercise, and it is defined once, here, so the write side
# and the read side can never quietly drift apart.
HISTOGRAM_EDGES_MS: tuple[int, ...] = (0, 100, 250, 500, 1_000, 2_000, 5_000, 10_000, 30_000)

_HISTOGRAM_METRICS = frozenset({"recovery_ms", "lease_renewal_ms"})


def _bin_edge_for(value_ms: float) -> int:
    edge = HISTOGRAM_EDGES_MS[0]
    for candidate in HISTOGRAM_EDGES_MS:
        if value_ms >= candidate:
            edge = candidate
        else:
            break
    return edge


Metric = Literal[
    "steps_completed",
    "runs_by_status",
    "recovery_ms",
    "lease_renewal_ms",
    "replay_steps",
    "replay_ms",
    "fencing_events",
    "uncertainty_entries",
    "dead_letters",
]

_TERMINAL_STATUS_BY_EVENT: dict[str, str] = {
    "RUN_COMPLETED": "completed",
    "RUN_FAILED": "failed",
    "RUN_CANCELLED": "cancelled",
    "RUN_NEEDS_REVIEW": "needs_review",
}

_UPSERT_SQL = """
INSERT INTO metrics_rollup (bucket_start, bucket_seconds, metric, dimension, count, sum_value)
VALUES (
    to_timestamp(floor(extract(epoch FROM $1::timestamptz) / $2) * $2),
    $2, $3, $4, $5, $6
)
ON CONFLICT (bucket_start, bucket_seconds, metric, dimension) DO UPDATE
SET count = metrics_rollup.count + EXCLUDED.count,
    sum_value = coalesce(metrics_rollup.sum_value, 0) + coalesce(EXCLUDED.sum_value, 0)
"""

# The histogram variant additionally increments one key of the `histogram`
# jsonb *object* (bin lower-edge, as text, -> count) atomically with the
# same statement — safe as a read-modify-write here specifically because
# this job is the table's only writer and runs as one un-parallelized
# periodic task (never a trigger, D-49), so there is no concurrent bumper
# to race against the `coalesce(...) + 1` it reads back from its own prior
# write.
_UPSERT_WITH_HISTOGRAM_SQL = """
INSERT INTO metrics_rollup (bucket_start, bucket_seconds, metric, dimension, count, sum_value, histogram)
VALUES (
    to_timestamp(floor(extract(epoch FROM $1::timestamptz) / $2) * $2),
    $2, $3, $4, $5, $6, jsonb_build_object($7::text, $5::bigint)
)
ON CONFLICT (bucket_start, bucket_seconds, metric, dimension) DO UPDATE
SET count = metrics_rollup.count + EXCLUDED.count,
    sum_value = coalesce(metrics_rollup.sum_value, 0) + coalesce(EXCLUDED.sum_value, 0),
    histogram = jsonb_set(
        coalesce(metrics_rollup.histogram, '{}'::jsonb),
        ARRAY[$7::text],
        to_jsonb(coalesce((metrics_rollup.histogram ->> $7::text)::int, 0) + $5::bigint)
    )
"""


async def _bump(
    conn: asyncpg.Connection[Any],
    *,
    created_at: Any,
    metric: Metric,
    dimension: str = "",
    count: int = 1,
    sum_value: float | None = None,
) -> None:
    if metric in _HISTOGRAM_METRICS and sum_value is not None:
        # For these two metrics `sum_value` is always one latency
        # observation (one renewal, one recovery), never a pre-aggregated
        # sum — see the two call sites in `_fold_event` — so it doubles as
        # the value to bin.
        bin_edge = str(_bin_edge_for(sum_value))
        for bucket_seconds in RESOLUTIONS_SECONDS:
            await conn.execute(
                _UPSERT_WITH_HISTOGRAM_SQL,
                created_at,
                bucket_seconds,
                metric,
                dimension,
                count,
                sum_value,
                bin_edge,
            )
        return

    for bucket_seconds in RESOLUTIONS_SECONDS:
        await conn.execute(
            _UPSERT_SQL, created_at, bucket_seconds, metric, dimension, count, sum_value
        )


async def _fold_event(conn: asyncpg.Connection[Any], row: asyncpg.Record) -> None:
    event_type = row["type"]
    payload = json.loads(row["payload"])
    created_at = row["created_at"]

    if event_type == "STEP_COMPLETED":
        await _bump(
            conn, created_at=created_at, metric="steps_completed", dimension=row["worker_id"]
        )
    elif event_type in _TERMINAL_STATUS_BY_EVENT:
        await _bump(
            conn,
            created_at=created_at,
            metric="runs_by_status",
            dimension=_TERMINAL_STATUS_BY_EVENT[event_type],
        )
        if event_type == "RUN_FAILED" and payload.get("dead_lettered"):
            await _bump(
                conn,
                created_at=created_at,
                metric="dead_letters",
                dimension=payload["error_type"],
            )
        if event_type == "RUN_NEEDS_REVIEW":
            # Dimensioned by the tool's *declared* safety policy — looked
            # up once, here, at ingestion time, rather than joined at every
            # `GET /api/metrics` call. `Metrics.uncertainty_by_policy`
            # (contracts/openapi.yaml) means "how many halts came from each
            # policy", not "how many are currently needs_review" (that
            # count is `runs_by_status`'s `needs_review` dimension, a
            # different question answered live in observability.py).
            policy_row = await conn.fetchrow(
                "SELECT safety FROM tool_registry WHERE name = $1", payload["tool_name"]
            )
            policy = policy_row["safety"] if policy_row is not None else "unknown"
            await _bump(conn, created_at=created_at, metric="uncertainty_entries", dimension=policy)
    elif event_type == "LEASE_RENEWED":
        await _bump(
            conn,
            created_at=created_at,
            metric="lease_renewal_ms",
            sum_value=float(payload["renewal_latency_ms"]),
        )
    elif event_type == "REPLAY_COMPLETED":
        await _bump(
            conn,
            created_at=created_at,
            metric="replay_steps",
            count=int(payload["steps_replayed"]),
        )
        await _bump(
            conn, created_at=created_at, metric="replay_ms", sum_value=float(payload["replay_ms"])
        )
    elif event_type == "WORKER_FENCED":
        await _bump(conn, created_at=created_at, metric="fencing_events")
    elif event_type == "RUN_CLAIMED" and payload.get("reason") == "reclaimed_after_lease_expiry":
        prior = await conn.fetchrow(
            """
            SELECT payload
            FROM run_events
            WHERE run_id = $1 AND type = 'RUN_CLAIMED' AND seq < $2
            ORDER BY seq DESC
            LIMIT 1
            """,
            row["run_id"],
            row["seq"],
        )
        if prior is not None:
            prior_payload = json.loads(prior["payload"])
            prior_expiry = datetime.fromisoformat(prior_payload["lease_expires_at"])
            recovery_ms = (created_at - prior_expiry).total_seconds() * 1000
            await _bump(
                conn, created_at=created_at, metric="recovery_ms", sum_value=max(0.0, recovery_ms)
            )


async def run_rollup_once(conn: asyncpg.Connection[Any], *, batch_size: int = 5000) -> int:
    """Fold up to `batch_size` newly-appended events into `metrics_rollup`,
    advance the watermark in the same transaction, and return how many were
    consumed (0 means caught up).
    """
    async with conn.transaction():
        watermark = await conn.fetchrow(
            "SELECT last_created_at, last_run_id, last_seq FROM metrics_rollup_watermark"
        )
        assert watermark is not None  # seeded by migration 004

        rows = await conn.fetch(
            """
            SELECT run_id, seq, type, payload, epoch, worker_id, step_index, created_at
            FROM run_events
            WHERE (created_at, run_id, seq) > ($1, $2, $3)
            ORDER BY created_at ASC, run_id ASC, seq ASC
            LIMIT $4
            """,
            watermark["last_created_at"],
            watermark["last_run_id"],
            watermark["last_seq"],
            batch_size,
        )
        for row in rows:
            await _fold_event(conn, row)

        if rows:
            last = rows[-1]
            await conn.execute(
                """
                UPDATE metrics_rollup_watermark
                SET last_created_at = $1, last_run_id = $2, last_seq = $3
                """,
                last["created_at"],
                last["run_id"],
                last["seq"],
            )
        return len(rows)


async def rebuild(conn: asyncpg.Connection[Any]) -> None:
    """Truncate the rollup and its watermark, then fold the entire log back
    through from the beginning (T353) — the test that proves this table is
    derived rather than authoritative runs this and compares against the
    live aggregation.
    """
    async with conn.transaction():
        await conn.execute("TRUNCATE metrics_rollup")
        await conn.execute(
            "UPDATE metrics_rollup_watermark SET last_created_at = '-infinity', last_run_id = 0, last_seq = 0"
        )
    while await run_rollup_once(conn) > 0:
        pass
