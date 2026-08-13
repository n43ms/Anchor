"""The two-phase journal: tool_journal, tool_registry, demo_effects.

Revision ID: 003_journal
Revises: 002_claim_indexes
Create Date: 2026-08-13

Creates the schema phase 5's "no double execution" guarantee is built on
(plan.md P5.3, tasks.md T253-T258): the idempotency ledger, the declared
per-tool safety registry, and the demo proof surface. Every constraint here
is enforced by PostgreSQL rather than by application discipline, per the
constitution's "constraints over conventions" — in particular,
`tool_journal_result_once` is what makes "at most one recorded result per
key" true rather than merely intended, and `demo_effects`'s
`UNIQUE (idempotency_key)` is what makes a double execution a rejected write
rather than a counted anomaly.

Table creation order is load-bearing: `tool_registry` before `tool_journal`
(whose `tool_name` column references it), and both before `demo_effects`
(whose `idempotency_key` column references `tool_journal`).

This migration is forward-only: `downgrade()` is deliberately empty.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "003_journal"
down_revision: str | None = "002_claim_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SAFETY_CATEGORIES = ("retry_safe", "reconcilable", "unsafe")
_RESOLUTIONS = (
    "retry_safe",
    "reconcilable",
    "unsafe_halted",
    "operator_marked_executed",
    "operator_marked_not_executed",
)


def upgrade() -> None:
    _create_tool_registry()
    _create_tool_journal()
    _create_demo_effects()


def _create_tool_registry() -> None:
    safety_list = ", ".join(f"'{s}'" for s in _SAFETY_CATEGORIES)
    op.execute(
        f"""
        CREATE TABLE tool_registry (
            name                 text        PRIMARY KEY,
            safety               text        NOT NULL,
            naturally_idempotent boolean     NOT NULL DEFAULT false,
            provider_accepts_key boolean     NOT NULL DEFAULT false,
            has_reconcile_fn     boolean     NOT NULL DEFAULT false,
            default_policy       text        NOT NULL,
            declaration_hash     text        NOT NULL,
            declared_by_version  text        NOT NULL,
            conflict_at          timestamptz,
            conflict_version     text,
            description          text,
            registered_at        timestamptz NOT NULL DEFAULT now(),
            last_used_at         timestamptz,

            CONSTRAINT tool_registry_safety_check CHECK (safety IN ({safety_list})),
            CONSTRAINT tool_registry_default_policy_check
                CHECK (default_policy IN ({safety_list})),

            -- FR-046: a `reconcilable` tool must declare a reconciliation
            -- function. Enforced here, not only at `register_tool`'s Python
            -- refusal, so a row inserted by any path still satisfies it
            -- (data-model.md §4).
            CONSTRAINT tool_registry_reconcilable_has_fn CHECK (
                safety <> 'reconcilable' OR has_reconcile_fn
            ),

            -- A tool cannot be declared safe to re-execute without naming
            -- *why* it is safe: naturally idempotent, or the provider
            -- deduplicates on a passed-through key.
            CONSTRAINT tool_registry_retry_safe_has_reason CHECK (
                safety <> 'retry_safe' OR (naturally_idempotent OR provider_accepts_key)
            ),

            CONSTRAINT tool_registry_conflict_columns_move_together CHECK (
                (conflict_at IS NULL) = (conflict_version IS NULL)
            )
        )
        """
    )


def _create_tool_journal() -> None:
    resolutions_list = ", ".join(f"'{r}'" for r in _RESOLUTIONS)
    op.execute(
        f"""
        CREATE TABLE tool_journal (
            idempotency_key   text        PRIMARY KEY,
            run_id            bigint      NOT NULL REFERENCES runs (id),
            step_index        integer     NOT NULL,
            tool_name         text        NOT NULL REFERENCES tool_registry (name),
            args_canonical    jsonb       NOT NULL,
            args_hash         text        NOT NULL,
            intent_at         timestamptz NOT NULL DEFAULT now(),
            intent_epoch      integer     NOT NULL,
            result            jsonb,
            result_at         timestamptz,
            result_epoch      integer,
            resolution        text,
            resolved_at       timestamptz,
            attempts          integer     NOT NULL DEFAULT 1,

            -- The two result columns move together, so "result recorded" is
            -- never ambiguous (this is the CHECK the three-state lookup
            -- reads: row absent -> NeverAttempted; row present with this
            -- pair NULL -> Uncertain; non-NULL -> Completed).
            CONSTRAINT tool_journal_result_pair CHECK (
                (result IS NULL) = (result_at IS NULL)
            ),
            CONSTRAINT tool_journal_resolution_check CHECK (
                resolution IS NULL OR resolution IN ({resolutions_list})
            ),
            CONSTRAINT tool_journal_attempts_positive CHECK (attempts >= 1)
        )
        """
    )
    op.execute("CREATE INDEX tool_journal_run_step_ix ON tool_journal (run_id, step_index)")
    op.execute(
        "CREATE INDEX tool_journal_tool_result_at_ix ON tool_journal (tool_name, result_at DESC)"
    )
    # The single scan that finds every open uncertainty window at once —
    # backs both invariant checking (I1's live verification) and the Needs
    # review page. Very small in steady state: entries disappear the moment
    # a result lands.
    op.execute(
        "CREATE INDEX tool_journal_open_window_ix ON tool_journal (intent_at) WHERE result IS NULL"
    )

    # A result, once recorded, is final (I1). Without this trigger, "at most
    # one recorded result per key" would hold only for as long as every
    # write path remembered not to overwrite — precisely the class of
    # enforcement the constitution rejects. Permits NULL -> result,
    # incrementing attempts, and setting resolution/resolved_at; raises
    # AN004 on any attempt to change an already-recorded, non-null result.
    op.execute(
        """
        CREATE FUNCTION tool_journal_result_once() RETURNS trigger AS $$
        BEGIN
            IF OLD.result IS NOT NULL AND NEW.result IS DISTINCT FROM OLD.result THEN
                RAISE EXCEPTION 'tool_journal result already recorded for key %', OLD.idempotency_key
                    USING ERRCODE = 'AN004',
                          DETAIL = json_build_object(
                              'idempotency_key', OLD.idempotency_key
                          )::text;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER tool_journal_result_once_trigger "
        "BEFORE UPDATE ON tool_journal "
        "FOR EACH ROW EXECUTE FUNCTION tool_journal_result_once()"
    )

    # No DELETE, ever — same reasoning as run_events (I2's sibling for the
    # journal): the ledger is audit evidence, not working state.
    op.execute(
        """
        CREATE FUNCTION tool_journal_no_delete() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'tool_journal is immutable (DELETE)'
                USING ERRCODE = 'AN003',
                      DETAIL = json_build_object('table', 'tool_journal', 'operation', 'DELETE')::text;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER tool_journal_no_delete_trigger "
        "BEFORE DELETE ON tool_journal "
        "FOR EACH ROW EXECUTE FUNCTION tool_journal_no_delete()"
    )


def _create_demo_effects() -> None:
    op.execute(
        """
        CREATE TABLE demo_effects (
            id               bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            run_id           bigint      NOT NULL REFERENCES runs (id),
            step_index       integer     NOT NULL,
            tool_name        text        NOT NULL,
            idempotency_key  text        NOT NULL REFERENCES tool_journal (idempotency_key),
            payload          jsonb       NOT NULL DEFAULT '{}',
            executed_at      timestamptz NOT NULL DEFAULT now(),

            -- The strongest single piece of evidence in the product: a
            -- double execution is rejected by the database, not merely
            -- counted (data-model.md §9).
            CONSTRAINT demo_effects_idempotency_key_uq UNIQUE (idempotency_key)
        )
        """
    )
    op.execute("CREATE INDEX demo_effects_run_step_ix ON demo_effects (run_id, step_index)")


def downgrade() -> None:
    # Deliberately empty: migrations are forward-only (ops/migrations/README.md).
    pass
