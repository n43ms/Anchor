"""Chaos schema: `chaos_runs`, `chaos_events`, `chaos_reports` (plan.md
P8.1, tasks.md T491-T493; data-model.md §6-§8).

Revision ID: 006_chaos
Revises: 005_runs_archived_at
Create Date: 2026-08-23

**Numbering note** (same convention as `002_claim_indexes.py`'s header):
plan.md and tasks.md both label this "migration 003" — tasks.md T491 even
flags the mismatch explicitly. By the time phase 8 is reached, `002`
(claim indexes, phase 3), `003` (journal, phase 5), the migration that
added the metrics rollup (phase 6) and `005` (`runs.archived_at`, phase 6)
already exist in this repository's actual migration chain, so the
next forward-only revision is `006`. Content is unaffected; only the label
shifts, exactly as it did the first time this happened.

Three tables, in dependency order: `chaos_runs` first (nothing references
it), then `chaos_events` (`chaos_run_id` FK, nullable — a kill issued
manually from the console has no owning harness run), then `chaos_reports`
(`chaos_run_id` is both its primary key and its FK — one report per
completed run).

**Both `chaos_events` and `chaos_reports` are immutable in every deployment
mode**, via the same `BEFORE UPDATE OR DELETE ... RAISE ... AN003` shape
`run_events_immutable` established in `001_foundation.py` (constitution
Principle II: constraints over conventions). This is published evidence —
`chaos_events` is one of the two inputs to the recovery-latency figure, and
`chaos_reports` is the permanent invariant record — and unlike
`runs.archived_at` (`005_runs_archived_at.py`) there is no reset affordance
that is even supposed to reach these tables, so there is no soft-hide
column to add here: an attempted `UPDATE` or `DELETE` against either table
is a bug, and the constitution's answer to a property that must hold is a
database constraint, not application-level care.

`chaos_reports.recovery_ms_p50/p95/p99/max` are all `NULL` exactly when
`kills_injected = 0`, enforced by `CHECK ((recovery_ms_p50 IS NULL) =
(kills_injected = 0))` on `recovery_ms_p50` alone (data-model.md §8): a
recovery figure on a run that never lost a worker is not a measurement,
and the schema refuses to let one exist by accident. The other three
percentiles are not separately constrained — `report.py` (P8.5) computes
all four from the same kill/reclaim pairs in one pass, so p50 being
present or absent is definitionally the same as p95/p99/max being present
or absent; a second, third, and fourth `CHECK` expressing the same fact
about the same computation would be redundant, not additionally safe.

This migration is forward-only: `downgrade()` is deliberately empty.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "006_chaos"
down_revision: str | None = "005_runs_archived_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHAOS_EVENT_TYPES = (
    "worker_kill",
    "worker_kill_graceful",
    "latency_injected",
    "stall_injected",
    "tool_failure_injected",
    "uncertainty_crash_injected",
)


def upgrade() -> None:
    _create_chaos_runs()
    _create_chaos_events()
    _create_chaos_reports()


def _create_chaos_runs() -> None:
    op.execute(
        """
        CREATE TABLE chaos_runs (
            id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            status                text NOT NULL DEFAULT 'pending',
            params                jsonb NOT NULL,
            deployment_mode       text NOT NULL,
            config_profile        text NOT NULL,
            lease_duration_ms     integer NOT NULL,
            renewal_interval_ms   integer NOT NULL,
            started_at            timestamptz NOT NULL DEFAULT now(),
            ended_at              timestamptz,
            heartbeat_at          timestamptz,
            CHECK (status IN ('pending', 'running', 'completed', 'failed', 'abandoned')),
            CHECK (deployment_mode IN ('demonstration', 'local')),
            CHECK (config_profile IN ('demo', 'production')),
            CHECK (ended_at IS NULL OR ended_at >= started_at)
        )
        """
    )
    # Serves the History page's newest-first listing (GET /api/chaos) and
    # the abandoned-detection scan at API startup (both read by started_at).
    op.execute("CREATE INDEX chaos_runs_started_at_ix ON chaos_runs (started_at DESC)")


def _create_chaos_events() -> None:
    types_sql = ", ".join(f"'{t}'" for t in _CHAOS_EVENT_TYPES)
    op.execute(
        f"""
        CREATE TABLE chaos_events (
            id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            chaos_run_id       bigint REFERENCES chaos_runs (id),
            type               text NOT NULL,
            target_worker_id   text,
            affected_run_ids   bigint[] NOT NULL DEFAULT '{{}}',
            params             jsonb NOT NULL DEFAULT '{{}}',
            created_at         timestamptz NOT NULL DEFAULT now(),
            CHECK (type IN ({types_sql}))
        )
        """
    )
    # Serves recovery-percentile computation (report.py joins a worker_kill
    # row's created_at against affected runs' reclaiming RUN_CLAIMED) and
    # the per-chaos-run event feed on the console's live invariant panel.
    op.execute("CREATE INDEX chaos_events_run_created_ix ON chaos_events (chaos_run_id, created_at)")
    # Serves the Logs-style "every injection of type X" view and CI's
    # bounded-smoke assertions, which filter by injection type.
    op.execute("CREATE INDEX chaos_events_type_created_ix ON chaos_events (type, created_at DESC)")

    op.execute(
        """
        CREATE FUNCTION chaos_events_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'chaos_events is immutable (%)', TG_OP
                USING ERRCODE = 'AN003',
                      DETAIL = json_build_object('table', 'chaos_events', 'operation', TG_OP)::text;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER chaos_events_immutable_trigger "
        "BEFORE UPDATE OR DELETE ON chaos_events "
        "FOR EACH ROW EXECUTE FUNCTION chaos_events_immutable()"
    )


def _create_chaos_reports() -> None:
    op.execute(
        """
        CREATE TABLE chaos_reports (
            chaos_run_id               bigint PRIMARY KEY REFERENCES chaos_runs (id),
            inv_no_duplicate_effects   boolean NOT NULL,
            inv_log_monotonic          boolean NOT NULL,
            inv_single_writer_per_epoch boolean NOT NULL,
            inv_terminal_reachability  boolean NOT NULL,
            inv_replay_determinism     boolean NOT NULL,
            violations                 jsonb NOT NULL DEFAULT '[]',
            duplicate_effect_count     integer NOT NULL,
            stranded_run_count         integer NOT NULL,
            kills_injected             integer NOT NULL,
            runs_total                 integer NOT NULL,
            steps_total                integer NOT NULL,
            recovery_ms_p50            integer,
            recovery_ms_p95            integer,
            recovery_ms_p99            integer,
            recovery_ms_max            integer,
            replay_steps_mean          numeric,
            replay_ms_mean             numeric,
            steps_per_second           numeric,
            fencing_events             integer NOT NULL DEFAULT 0,
            uncertainty_entries        jsonb NOT NULL DEFAULT '{}',
            dead_letter_count          integer NOT NULL DEFAULT 0,
            duration_seconds           integer NOT NULL,
            created_at                 timestamptz NOT NULL DEFAULT now(),
            CHECK (duplicate_effect_count >= 0 AND stranded_run_count >= 0),
            CHECK ((recovery_ms_p50 IS NULL) = (kills_injected = 0))
        )
        """
    )
    # Serves the landing evidence badge and GET /api/chaos/latest, both of
    # which read only the single newest row.
    op.execute("CREATE INDEX chaos_reports_created_at_ix ON chaos_reports (created_at DESC)")

    op.execute(
        """
        CREATE FUNCTION chaos_reports_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'chaos_reports is immutable (%)', TG_OP
                USING ERRCODE = 'AN003',
                      DETAIL = json_build_object('table', 'chaos_reports', 'operation', TG_OP)::text;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER chaos_reports_immutable_trigger "
        "BEFORE UPDATE OR DELETE ON chaos_reports "
        "FOR EACH ROW EXECUTE FUNCTION chaos_reports_immutable()"
    )


def downgrade() -> None:
    # Deliberately empty: migrations are forward-only (ops/migrations/README.md).
    pass
