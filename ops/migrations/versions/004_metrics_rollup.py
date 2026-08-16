"""Metrics rollup: the display-only derived time series (plan.md P6.10,
tasks.md T350; data-model.md §9, research.md D-49).

Revision ID: 004_metrics_rollup
Revises: 003_journal
Create Date: 2026-08-17

**This table is derived and rebuildable, never authoritative.** Truncating
it and replaying `run_events` through `anchor.api.serializers.rollup`'s
`REBUILD` path reconstructs every bucket exactly. It is maintained by a
periodic job (`anchor.api.app`'s background task), never by a trigger on
`run_events` — an `AFTER INSERT` trigger upserting the current bucket would
make every worker contend on the *same* bucket row, serializing appends
across runs that currently never contend at all, in service of a
sparkline (D-49). No trigger is created here for that reason; its absence
is load-bearing, not an oversight, and `tests/boundary/test_rollup_not_maintained_by_trigger.py`
asserts it.

**What must never be read from this table**: the duplicate-effect count,
the stranded-run count, the `needs_review` list, effect counts, and every
chaos-report figure. Those are correctness reads, always computed from
`tool_journal` and `run_events` at read time
(`anchor.api.serializers.timeline`, `anchor.api.routers.observability`). A
stale zero on the duplicate counter would be the single most damaging
thing this product could display.

This migration is forward-only: `downgrade()` is deliberately empty.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "004_metrics_rollup"
down_revision: str | None = "003_journal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_METRICS = (
    "steps_completed",
    "runs_by_status",
    "recovery_ms",
    "lease_renewal_ms",
    "replay_steps",
    "replay_ms",
    "fencing_events",
    "uncertainty_entries",
    "dead_letters",
)


def upgrade() -> None:
    metrics_list = ", ".join(f"'{m}'" for m in _METRICS)
    op.execute(
        f"""
        CREATE TABLE metrics_rollup (
            bucket_start    timestamptz NOT NULL,
            bucket_seconds  integer     NOT NULL,
            metric          text        NOT NULL,
            dimension       text        NOT NULL DEFAULT '',
            count           bigint      NOT NULL DEFAULT 0,
            sum_value       numeric,
            histogram       jsonb,

            PRIMARY KEY (bucket_start, bucket_seconds, metric, dimension),
            CONSTRAINT metrics_rollup_bucket_seconds_check CHECK (bucket_seconds IN (10, 300)),
            CONSTRAINT metrics_rollup_count_nonneg CHECK (count >= 0),
            CONSTRAINT metrics_rollup_metric_check CHECK (metric IN ({metrics_list}))
        )
        """
    )

    # A single-row watermark, not a per-metric one: the rollup job folds
    # every metric for a batch of newly-consumed run_events in one pass, so
    # one position into the log is all "how far the job has gotten" needs
    # to mean.
    op.execute(
        """
        CREATE TABLE metrics_rollup_watermark (
            id              boolean     PRIMARY KEY DEFAULT true,
            last_created_at timestamptz NOT NULL DEFAULT '-infinity',
            last_run_id     bigint      NOT NULL DEFAULT 0,
            last_seq        bigint      NOT NULL DEFAULT 0,

            CONSTRAINT metrics_rollup_watermark_singleton CHECK (id)
        )
        """
    )
    op.execute("INSERT INTO metrics_rollup_watermark DEFAULT VALUES")

    # Read pattern: "every bucket for this metric, this resolution, in this
    # window" (anchor.api.serializers.rollup, anchor.api.routers.observability).
    # bucket_start leads because every query filters by a time window first.
    op.execute(
        """
        CREATE INDEX metrics_rollup_query_ix
        ON metrics_rollup (metric, bucket_seconds, bucket_start)
        """
    )


def downgrade() -> None:
    # Deliberately empty: migrations are forward-only (ops/migrations/README.md).
    pass
