"""Foundation: runs, run_events, workers, runtime_config, and the invariant DDL.

Revision ID: 001_foundation
Revises: None
Create Date: 2026-08-08

Creates the schema that must exist before any protocol code can be written
honestly (plan.md Phase 0): the append-only log and its epoch write gate,
the worker fleet registry with a never-reused identity, and the
configuration table with its cross-row assertion trigger.

**The epoch trigger is deliberately created here, in phase 0, rather than
in phase 4 where fencing becomes behaviourally exercised.** Creating a
constraint is cheap now and expensive to retrofit after four phases of
writes exist; the trigger is inert until epochs advance in phase 3 and
exercised in phase 4. This is a documented pull-forward, sanctioned by
"constraints over conventions" (plan.md Phase 0 note).

Every constraint, trigger, and function below is raw SQL. This migration
is forward-only: `downgrade()` is deliberately empty.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EVENT_TYPES = (
    "RUN_SUBMITTED",
    "RUN_CLAIMED",
    "REPLAY_COMPLETED",
    "STEP_STARTED",
    "LLM_CALLED",
    "TOOL_INTENT",
    "TOOL_RESULT",
    "NONDET_RECORDED",
    "STEP_COMPLETED",
    "STEP_SKIPPED_ON_REPLAY",
    "STEP_FAILED",
    "LEASE_RENEWED",
    "WORKER_FENCED",
    "RUN_COMPLETED",
    "RUN_FAILED",
    "RUN_CANCELLED",
    "RUN_NEEDS_REVIEW",
)


def upgrade() -> None:
    _create_runs()
    _create_workers()
    _create_run_events()
    _create_runtime_config()
    _seed_runtime_config()
    _create_worker_label_incarnations()


def _create_runs() -> None:
    event_types_sql = ", ".join(f"'{t}'" for t in _EVENT_TYPES)  # noqa: F841 (documented for readers)
    op.execute(
        """
        CREATE TABLE runs (
            id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            agent_type            text        NOT NULL,
            input                 jsonb       NOT NULL DEFAULT '{}',
            client_request_key    text,
            status                text        NOT NULL DEFAULT 'pending',
            epoch                 integer     NOT NULL DEFAULT 0,
            last_seq              bigint      NOT NULL DEFAULT 0,
            lease_expires_at      timestamptz,
            owner_worker_id       text,
            priority              smallint    NOT NULL DEFAULT 0,
            attempts              integer     NOT NULL DEFAULT 0,
            cancel_requested_at   timestamptz,
            is_demo               boolean     NOT NULL DEFAULT false,
            chaos_run_id          bigint,
            created_at            timestamptz NOT NULL DEFAULT now(),
            claimed_at            timestamptz,
            finished_at           timestamptz,

            CONSTRAINT runs_status_check CHECK (
                status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'needs_review')
            ),
            CONSTRAINT runs_epoch_nonneg CHECK (epoch >= 0),
            CONSTRAINT runs_last_seq_nonneg CHECK (last_seq >= 0),
            CONSTRAINT runs_attempts_nonneg CHECK (attempts >= 0),

            -- "Illegal states unrepresentable" (data-model.md §1, D-23): a run
            -- cannot be completed and still hold a lease, and a halted
            -- needs_review run cannot block reclaim while looking healthy.
            CONSTRAINT runs_terminal_holds_no_lease CHECK (
                status NOT IN ('completed', 'failed', 'cancelled', 'needs_review')
                OR (
                    owner_worker_id IS NULL
                    AND lease_expires_at IS NULL
                    AND finished_at IS NOT NULL
                )
            ),
            CONSTRAINT runs_running_implies_ownership CHECK (
                status <> 'running'
                OR (owner_worker_id IS NOT NULL AND lease_expires_at IS NOT NULL)
            )
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX runs_client_request_key_uq "
        "ON runs (client_request_key) WHERE client_request_key IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX runs_claim_pending_ix "
        "ON runs (priority, created_at) WHERE status = 'pending'"
    )
    op.execute(
        "CREATE INDEX runs_claim_expired_lease_ix "
        "ON runs (lease_expires_at) WHERE status = 'running'"
    )
    op.execute("CREATE INDEX runs_status_created_ix ON runs (status, created_at DESC)")
    op.execute(
        "CREATE INDEX runs_is_demo_status_ix ON runs (is_demo, status) WHERE is_demo"
    )
    op.execute(
        "CREATE INDEX runs_chaos_run_id_ix ON runs (chaos_run_id) WHERE chaos_run_id IS NOT NULL"
    )


def _create_workers() -> None:
    op.execute(
        """
        CREATE TABLE workers (
            id                 text        PRIMARY KEY,
            label              text        NOT NULL,
            incarnation        integer     NOT NULL,
            hostname           text        NOT NULL,
            pid                integer     NOT NULL,
            started_at         timestamptz NOT NULL DEFAULT now(),
            last_seen_at       timestamptz NOT NULL DEFAULT now(),
            current_run_count  integer     NOT NULL DEFAULT 0,
            capacity           integer     NOT NULL,
            code_version       text        NOT NULL,
            role               text        NOT NULL DEFAULT 'runner',
            stopped_at         timestamptz,

            CONSTRAINT workers_id_matches_label_incarnation
                CHECK (id = label || '#' || incarnation),
            CONSTRAINT workers_label_incarnation_uq UNIQUE (label, incarnation),
            CONSTRAINT workers_role_check CHECK (role IN ('runner', 'chaos')),
            CONSTRAINT workers_run_count_bounds
                CHECK (current_run_count >= 0 AND current_run_count <= capacity),
            CONSTRAINT workers_incarnation_positive CHECK (incarnation >= 1)
        )
        """
    )
    op.execute("CREATE INDEX workers_last_seen_ix ON workers (last_seen_at DESC)")
    op.execute(
        "CREATE INDEX workers_label_incarnation_desc_ix ON workers (label, incarnation DESC)"
    )
    # Now that `workers` exists, add the deferred FK from runs.owner_worker_id.
    # ON DELETE SET NULL is deliberately NOT used: worker rows are never
    # deleted, only aged out of the fleet view (data-model.md §1).
    op.execute(
        "ALTER TABLE runs ADD CONSTRAINT runs_owner_worker_id_fkey "
        "FOREIGN KEY (owner_worker_id) REFERENCES workers (id)"
    )


def _create_run_events() -> None:
    types_list = ", ".join(f"'{t}'" for t in _EVENT_TYPES)
    op.execute(
        f"""
        CREATE TABLE run_events (
            run_id       bigint      NOT NULL REFERENCES runs (id),
            seq          bigint      NOT NULL,
            type         text        NOT NULL,
            payload      jsonb       NOT NULL DEFAULT '{{}}',
            epoch        integer     NOT NULL,
            worker_id    text        NOT NULL,
            step_index   integer,
            created_at   timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (run_id, seq),
            CONSTRAINT run_events_type_check CHECK (type IN ({types_list})),
            CONSTRAINT run_events_seq_positive CHECK (seq > 0),
            CONSTRAINT run_events_epoch_nonneg CHECK (epoch >= 0)
        )
        """
    )
    op.execute("CREATE INDEX run_events_type_created_ix ON run_events (type, created_at DESC)")
    op.execute(
        "CREATE INDEX run_events_worker_created_ix ON run_events (worker_id, created_at DESC)"
    )
    op.execute("CREATE INDEX run_events_run_epoch_ix ON run_events (run_id, epoch)")

    # The epoch write gate (I3): the single database mechanism that makes
    # split-brain structurally impossible. Takes FOR UPDATE on the run row
    # itself, so the guarantee does not depend on the caller having already
    # locked anything (research.md D-08).
    op.execute(
        """
        CREATE FUNCTION run_events_epoch_gate() RETURNS trigger AS $$
        DECLARE
            current_epoch integer;
        BEGIN
            SELECT epoch INTO current_epoch FROM runs WHERE id = NEW.run_id FOR UPDATE;

            IF current_epoch IS NULL THEN
                RAISE EXCEPTION 'run % does not exist', NEW.run_id;
            END IF;

            IF NEW.epoch <> current_epoch THEN
                -- Rejects a stale writer (NEW.epoch < current) AND a writer
                -- inventing an epoch (NEW.epoch > current) — both are the
                -- same failure: an event claiming an epoch it did not win.
                RAISE EXCEPTION 'fenced write: run % epoch % is stale (current %)',
                    NEW.run_id, NEW.epoch, current_epoch
                    USING ERRCODE = 'AN001',
                          DETAIL = json_build_object(
                              'run_id', NEW.run_id,
                              'stale_epoch', NEW.epoch,
                              'current_epoch', current_epoch
                          )::text;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER run_events_epoch_gate_trigger "
        "BEFORE INSERT ON run_events "
        "FOR EACH ROW EXECUTE FUNCTION run_events_epoch_gate()"
    )

    # Append-only as a database property (I2), not a coding convention.
    op.execute(
        """
        CREATE FUNCTION run_events_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'run_events is immutable (%)', TG_OP
                USING ERRCODE = 'AN003',
                      DETAIL = json_build_object('table', 'run_events', 'operation', TG_OP)::text;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER run_events_immutable_trigger "
        "BEFORE UPDATE OR DELETE ON run_events "
        "FOR EACH ROW EXECUTE FUNCTION run_events_immutable()"
    )

    # ------------------------------------------------------------------
    # WARNING (D-52) — read before ever adding partitioning to this table.
    #
    # run_events MUST NOT be range-partitioned by created_at. PostgreSQL
    # requires every unique constraint on a partitioned table to include
    # the partition key, so a time-partitioned run_events would force the
    # primary key to become (run_id, seq, created_at) — which does NOT
    # enforce uniqueness of (run_id, seq). Two events for the same run
    # carrying the same sequence number, landing in different time
    # partitions, would both be silently accepted. That deletes the single
    # most important constraint in the schema and breaks I2, while looking
    # like a routine time-series optimization in the diff.
    #
    # If this table is ever partitioned, the partition key MUST contain
    # run_id (e.g. HASH partitioning by run_id), which preserves the
    # uniqueness constraint and keeps replay reads pruned to one partition.
    # It is not being done now: partitioning one table on one host does not
    # move the single-writer ceiling this project measures and publishes.
    # ------------------------------------------------------------------


def _create_runtime_config() -> None:
    op.execute(
        """
        CREATE TABLE runtime_config (
            key          text        PRIMARY KEY,
            value        jsonb       NOT NULL,
            version      bigint      NOT NULL DEFAULT 1,
            updated_at   timestamptz NOT NULL DEFAULT now(),
            updated_by   text        NOT NULL DEFAULT 'seed',

            CONSTRAINT runtime_config_version_positive CHECK (version >= 1)
        )
        """
    )

    # The cross-row assertion backstop (FR-060, FR-063). Application code
    # (anchor.core.config.assertion) validates before writing, to produce a
    # good error message; this trigger exists to make the property true even
    # when application code is bypassed by a direct write. Statement-level
    # because the invariant spans rows and a CHECK cannot express it.
    op.execute(
        """
        CREATE FUNCTION runtime_config_assert() RETURNS trigger AS $$
        DECLARE
            lease_ms   bigint;
            renewal_ms bigint;
            margin_ms  bigint;
            timeout_ms bigint;
        BEGIN
            SELECT (value #>> '{}')::bigint INTO lease_ms
                FROM runtime_config WHERE key = 'lease_duration_ms';
            SELECT (value #>> '{}')::bigint INTO renewal_ms
                FROM runtime_config WHERE key = 'renewal_interval_ms';
            SELECT (value #>> '{}')::bigint INTO margin_ms
                FROM runtime_config WHERE key = 'margin_ms';
            SELECT (value #>> '{}')::bigint INTO timeout_ms
                FROM runtime_config WHERE key = 'step_timeout_ms';

            IF lease_ms IS NULL OR renewal_ms IS NULL
               OR margin_ms IS NULL OR timeout_ms IS NULL THEN
                RETURN NULL; -- not fully seeded yet (mid-migration); nothing to assert
            END IF;

            IF lease_ms < 4 * renewal_ms THEN
                RAISE EXCEPTION 'configuration assertion failed: lease_duration_ms >= 4 * renewal_interval_ms'
                    USING ERRCODE = 'AN002',
                          DETAIL = json_build_object(
                              'relationship', 'lease_duration_ms >= 4 * renewal_interval_ms',
                              'offending_values', json_build_object(
                                  'lease_duration_ms', lease_ms,
                                  'renewal_interval_ms', renewal_ms
                              )
                          )::text;
            END IF;

            IF margin_ms <> (lease_ms - renewal_ms) THEN
                RAISE EXCEPTION 'configuration assertion failed: margin_ms == lease_duration_ms - renewal_interval_ms'
                    USING ERRCODE = 'AN002',
                          DETAIL = json_build_object(
                              'relationship', 'margin_ms == lease_duration_ms - renewal_interval_ms',
                              'offending_values', json_build_object(
                                  'margin_ms', margin_ms,
                                  'lease_duration_ms', lease_ms,
                                  'renewal_interval_ms', renewal_ms
                              )
                          )::text;
            END IF;

            IF timeout_ms <= 0 THEN
                RAISE EXCEPTION 'configuration assertion failed: step_timeout_ms > 0'
                    USING ERRCODE = 'AN002',
                          DETAIL = json_build_object(
                              'relationship', 'step_timeout_ms > 0',
                              'offending_values', json_build_object('step_timeout_ms', timeout_ms)
                          )::text;
            END IF;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER runtime_config_assert_trigger "
        "AFTER INSERT OR UPDATE ON runtime_config "
        "FOR EACH STATEMENT EXECUTE FUNCTION runtime_config_assert()"
    )


def _seed_runtime_config() -> None:
    """Seed the fifteen keys from the active profile (`ANCHOR_CONFIG_PROFILE`,
    default `demo`). Imported lazily so `anchor.core.config` is not a
    dependency of every alembic invocation that never reaches this
    function (e.g. `alembic history`).
    """
    from anchor.core.config.profiles import ConfigProfile, profile_settings

    profile_name = os.environ.get("ANCHOR_CONFIG_PROFILE", "demo")
    settings = profile_settings(ConfigProfile(profile_name))

    bind = op.get_bind()
    insert_stmt = sa.text(
        "INSERT INTO runtime_config (key, value, updated_by) "
        "VALUES (:key, CAST(:value AS jsonb), 'seed')"
    )
    for key, value in settings.model_dump(mode="json").items():
        bind.execute(insert_stmt, {"key": key, "value": json.dumps(value)})


def _create_worker_label_incarnations() -> None:
    """Incarnation allocation, one row per fleet-slot label.

    data-model.md §5 describes "one PostgreSQL sequence per fleet-slot
    label." Fleet-slot labels are operator-configurable
    (`ANCHOR_WORKER_LABEL_POOL`) and therefore not known at migration time,
    so a literal per-label `CREATE SEQUENCE` is not expressible here without
    dynamic DDL at worker startup — which would make schema state depend on
    deployment configuration, the exact anti-pattern migrations exist to
    prevent.

    This table is the equivalent primitive generalized over an unknown label
    set: a single atomic UPSERT increments exactly one row under its own
    lock, giving the same guarantee a per-label sequence would (no two
    concurrent registrations can be issued the same incarnation for the same
    label) without requiring the labels in advance.
    """
    op.execute(
        """
        CREATE TABLE worker_label_incarnations (
            label              text    PRIMARY KEY,
            next_incarnation   integer NOT NULL DEFAULT 1,

            CONSTRAINT worker_label_incarnations_positive CHECK (next_incarnation >= 1)
        )
        """
    )


def downgrade() -> None:
    # Deliberately empty: migrations are forward-only (ops/migrations/README.md).
    pass
