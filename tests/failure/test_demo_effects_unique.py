"""T242 — `demo_effects`'s `UNIQUE (idempotency_key)` rejects a forced
double execution outright; it is not merely counted. This is the strongest
single piece of evidence in the product (data-model.md §9): the row count is
ground truth for "it ran once," verifiable without trusting the log.
"""

from __future__ import annotations

import json

import asyncpg
import pytest


@pytest.mark.asyncio
async def test_forced_duplicate_effect_is_rejected_by_the_database(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_short') RETURNING id"
        )
        await conn.execute(
            """
            INSERT INTO tool_registry
                (name, safety, naturally_idempotent, provider_accepts_key, has_reconcile_fn,
                 default_policy, declaration_hash, declared_by_version)
            VALUES ('send_email', 'unsafe', false, false, false, 'unsafe', 'h', 'test')
            ON CONFLICT DO NOTHING
            """
        )
        await conn.execute(
            """
            INSERT INTO tool_journal
                (idempotency_key, run_id, step_index, tool_name, args_canonical, args_hash,
                 intent_epoch, result, result_at, result_epoch)
            VALUES ('effect-key-1', $1, 0, 'send_email', '{}'::jsonb, 'h', 0, '{}'::jsonb, now(), 0)
            """,
            run_id,
        )

        await conn.execute(
            """
            INSERT INTO demo_effects (run_id, step_index, tool_name, idempotency_key, payload)
            VALUES ($1, 0, 'send_email', 'effect-key-1', $2::jsonb)
            """,
            run_id,
            json.dumps({"recipient": "a@example.com"}),
        )

        with pytest.raises(asyncpg.UniqueViolationError):
            # A second, independent attempt to record the *same* effect — the
            # scenario the constraint exists to catch loudly rather than
            # silently double-count.
            await conn.execute(
                """
                INSERT INTO demo_effects (run_id, step_index, tool_name, idempotency_key, payload)
                VALUES ($1, 0, 'send_email', 'effect-key-1', $2::jsonb)
                """,
                run_id,
                json.dumps({"recipient": "a@example.com"}),
            )


@pytest.mark.asyncio
async def test_demo_tools_deduplicate_a_legitimate_retry_via_the_same_mechanism(
    db_pool: asyncpg.Pool,
) -> None:
    """A *legitimate* retry_safe re-execution (`runtime.tools.demo._record_effect`)
    must not raise: the fake provider recognizes the key and returns the
    prior payload instead of writing a second row, which is what "the
    provider deduplicates on their side" means concretely in this
    simulation.
    """
    from anchor.runtime.tools.demo import _record_effect

    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_short') RETURNING id"
        )
        first = await _record_effect(
            conn,
            run_id=run_id,
            step_index=0,
            tool_name="charge_card",
            idempotency_key="effect-key-2",
            payload={"amount_cents": 500},
        )
        second = await _record_effect(
            conn,
            run_id=run_id,
            step_index=0,
            tool_name="charge_card",
            idempotency_key="effect-key-2",
            payload={"amount_cents": 500},
        )
        count = await conn.fetchval(
            "SELECT count(*) FROM demo_effects WHERE idempotency_key = $1", "effect-key-2"
        )

    assert first == second == {"amount_cents": 500}
    assert count == 1, "exactly one row must exist regardless of how many times fn() is invoked"
