"""T008 — the `runtime_config_assert` trigger is the backstop, not the only
gate (FR-060, FR-063).

`anchor.core.config.assertion` validates before an application-level write,
to produce a good error message. This trigger exists so the property holds
even when that path is bypassed by a direct `UPDATE` — which is exactly
what this test does, deliberately going around the application layer.

Requires a live PostgreSQL with migration 001 applied (which also seeds the
fifteen keys, so they exist to be updated).
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.core.db import pool as anchor_pool
from anchor.core.db.errors import ConfigAssertionError


@pytest.mark.asyncio
async def test_direct_update_violating_the_lease_relationship_is_rejected(
    db_pool: asyncpg.Pool,
) -> None:
    with pytest.raises(ConfigAssertionError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            # 1ms cannot be >= 4x any positive renewal_interval_ms already
            # seeded, regardless of which profile the test database was
            # migrated with.
            await conn.execute(
                "UPDATE runtime_config SET value = '1'::jsonb WHERE key = 'lease_duration_ms'"
            )

    assert exc_info.value.relationship == "lease_duration_ms >= 4 * renewal_interval_ms"


@pytest.mark.asyncio
async def test_direct_update_violating_step_timeout_is_rejected(db_pool: asyncpg.Pool) -> None:
    with pytest.raises(ConfigAssertionError) as exc_info:
        async with anchor_pool.acquire(db_pool) as conn:
            await conn.execute(
                "UPDATE runtime_config SET value = '0'::jsonb WHERE key = 'step_timeout_ms'"
            )

    assert exc_info.value.relationship == "step_timeout_ms > 0"


@pytest.mark.asyncio
async def test_a_rejected_update_leaves_the_prior_value_in_place(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        before = await conn.fetchval(
            "SELECT value FROM runtime_config WHERE key = 'lease_duration_ms'"
        )

    with pytest.raises(ConfigAssertionError):
        async with anchor_pool.acquire(db_pool) as conn:
            await conn.execute(
                "UPDATE runtime_config SET value = '1'::jsonb WHERE key = 'lease_duration_ms'"
            )

    async with db_pool.acquire() as conn:
        after = await conn.fetchval(
            "SELECT value FROM runtime_config WHERE key = 'lease_duration_ms'"
        )
    assert after == before, "the statement-level trigger must roll back the whole statement"


@pytest.mark.asyncio
async def test_a_consistent_multi_row_update_is_accepted_in_one_statement(
    db_pool: asyncpg.Pool,
) -> None:
    """The trigger is statement-level (`FOR EACH STATEMENT`), firing once
    per SQL statement regardless of how many rows it touches — which is
    exactly what lets a single multi-row `UPDATE` change lease, renewal,
    and margin together and be judged only on the *resulting* state, not
    rejected the instant the first individual key looks wrong in isolation.

    This must be **one** statement. Three separate `UPDATE` calls would
    fire the trigger three times, and the first one alone (changing only
    `renewal_interval_ms` while `lease_duration_ms` is still its old,
    smaller value) would already violate the relationship — which is not
    what this test is demonstrating.
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE runtime_config SET value =
                CASE key
                    WHEN 'renewal_interval_ms' THEN '20000'::jsonb
                    WHEN 'lease_duration_ms'   THEN '80000'::jsonb
                    WHEN 'margin_ms'           THEN '60000'::jsonb
                END
            WHERE key IN ('renewal_interval_ms', 'lease_duration_ms', 'margin_ms')
            """
        )
        renewal = await conn.fetchval(
            "SELECT value FROM runtime_config WHERE key = 'renewal_interval_ms'"
        )
    assert renewal == "20000"
