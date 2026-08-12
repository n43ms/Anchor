"""Claim and global-cap indexes (plan.md P3.2, tasks.md T163).

Revision ID: 002_claim_indexes
Revises: 001_foundation
Create Date: 2026-08-12

**Numbering note** (carried over from tasks.md T163, restated here so the
migration file matches its own history without a reader needing the task
list): plan.md originally labelled phase 5's migration `002` and phase 8's
`003`. Because the global-cap count query (D-44) could not be specified
before this phase, migrations are sequentially `002` (phase 3, this file),
`003` (phase 5), `004` (phase 8). Content is unaffected; only the labels
shift by one.

**What this migration does NOT add, and why.** `core.leases.claim`'s two
claim branches and its global-cap subquery are each already served by an
index created in `001_foundation`:

- `status = 'pending'` (with `ORDER BY priority, created_at`) is served by
  `runs_claim_pending_ix ON runs (priority, created_at) WHERE status = 'pending'`.
- `status = 'running' AND lease_expires_at < now()` is served by
  `runs_claim_expired_lease_ix ON runs (lease_expires_at) WHERE status = 'running'`.
- `SELECT count(*) FROM runs WHERE status = 'running'` matches the exact
  partial predicate of `runs_claim_expired_lease_ix` — a query predicate
  that exactly matches an index's partial predicate can be satisfied by
  that index without also needing the indexed column, so the cap count
  scans the same small partial index rather than the full table.

These were pulled forward in phase 0 (001_foundation.py, T041) for the same
reason the epoch trigger was: cheap to create now, expensive to retrofit
after writes exist. Adding a second, redundant partial index on
`(status) WHERE status = 'running'` here would duplicate write cost on
every claim and every completion with no read benefit, since the planner
already has an index whose predicate is the exact query. `T164`'s `EXPLAIN`
test asserts this directly, so "no new index" is a verified claim, not an
assumption.

This migration exists — with no DDL body — only so the revision chain has
a `002` for phase 5's migration to build on, matching the numbering this
project's own task list commits to.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "002_claim_indexes"
down_revision: str | None = "001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Deliberately no DDL: see module docstring. The claim statement and the
    # global-cap count are both already served by indexes created in
    # 001_foundation, verified by tests/unit/test_claim_uses_indexes.py.
    pass


def downgrade() -> None:
    # Deliberately empty: migrations are forward-only (ops/migrations/README.md).
    pass
