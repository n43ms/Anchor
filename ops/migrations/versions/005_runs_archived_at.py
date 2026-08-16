"""`runs.archived_at` — the reset affordance, without touching I2 (plan.md
P6.13, tasks.md T361-T362; FR-108, §21.6).

Revision ID: 005_runs_archived_at
Revises: 004_metrics_rollup
Create Date: 2026-08-17

**Why this is a soft-hide column and not a `DELETE`.** "Clear demo runs"
(§21.6: "prunes completed demo runs so the runs list stays legible") reads,
at first glance, like it wants a `DELETE FROM runs`. It cannot be one:
`run_events_immutable` (migration 001) raises `AN003` on **any** `UPDATE OR
DELETE` against `run_events`, unconditionally, with no carve-out for an
administrative reset — append-only is `I2`, a database property, not an
application-level policy an admin action is allowed to override. A `DELETE
FROM runs` would therefore fail on the foreign key from `run_events` (and
`tool_journal`, `demo_effects`) the moment any targeted run had ever
appended a single event, which every real run has.

The reset affordance instead sets `archived_at`, and `GET /api/runs`
excludes archived runs by default (an `include_archived=true` query
parameter remains an escape hatch, so nothing is actually unreachable). The
log stays literally append-only with zero exceptions; the runs list gets
visually clean, which is the actual, stated requirement.

**Structurally unable to touch chaos history** (FR-108): this column lives
on `runs`, which chaos-harness rows are not required to have an entry
in in the way `chaos_events`/`chaos_reports` are their own tables entirely
— archiving a `runs` row never reaches either.

This migration is forward-only: `downgrade()` is deliberately empty.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "005_runs_archived_at"
down_revision: str | None = "004_metrics_rollup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE runs ADD COLUMN archived_at timestamptz")
    # Serves "the default runs list excludes archived rows" (GET /api/runs)
    # without slowing the claim path: a partial index, present only for the
    # (small, steady-state) set of non-archived rows, which is every row
    # that matters to claiming or to the default list view.
    op.execute(
        """
        CREATE INDEX runs_not_archived_ix
        ON runs (created_at DESC)
        WHERE archived_at IS NULL
        """
    )


def downgrade() -> None:
    # Deliberately empty: migrations are forward-only (ops/migrations/README.md).
    pass
