"""T011 — the schema-version gate refuses to start on a mismatch (D-45,
FR-128).

`built_against_revision()` needs no I/O (it reads the migration scripts
bundled with this checkout) and is exercised on its own. The mismatch and
match paths need a live PostgreSQL with `alembic_version` present — i.e.
migrations must already have been applied once via
`alembic -c ops/migrations/alembic.ini upgrade head`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import asyncpg
import pytest

from anchor.core.db.schema_gate import (
    SchemaVersionMismatchError,
    applied_revision,
    assert_schema_matches,
    built_against_revision,
)


def test_built_against_revision_needs_no_database() -> None:
    """Pure: reads ops/migrations/versions/ directly."""
    head = built_against_revision()
    assert head == "002_claim_indexes"


@pytest.mark.asyncio
async def test_applied_revision_matches_built_against_after_a_real_migration(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        applied = await applied_revision(conn)
    assert applied == built_against_revision(), (
        "the test database's alembic_version does not match this checkout's HEAD — "
        "run `alembic -c ops/migrations/alembic.ini upgrade head` against it first"
    )


@pytest.mark.asyncio
async def test_assert_schema_matches_succeeds_on_a_correctly_migrated_database(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        matched = await assert_schema_matches(conn)
    assert matched == built_against_revision()


@pytest.fixture
async def _corrupted_alembic_version(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """Temporarily point `alembic_version` at a revision that does not
    exist in this checkout, to exercise the refusal path, then restore the
    real value so no other test observes a "migrated" database that
    disagrees with its own code.
    """
    async with db_pool.acquire() as conn:
        original = await conn.fetchval("SELECT version_num FROM alembic_version")
        await conn.execute("UPDATE alembic_version SET version_num = 'not_a_real_revision'")
    try:
        yield
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE alembic_version SET version_num = $1", original)


@pytest.mark.asyncio
async def test_a_mismatched_revision_refuses_to_start_naming_both(
    db_pool: asyncpg.Pool, _corrupted_alembic_version: None
) -> None:
    with pytest.raises(SchemaVersionMismatchError) as exc_info:
        async with db_pool.acquire() as conn:
            await assert_schema_matches(conn)

    assert exc_info.value.applied == "not_a_real_revision"
    assert exc_info.value.built_against == "002_claim_indexes"
    message = str(exc_info.value)
    assert "not_a_real_revision" in message
    assert "002_claim_indexes" in message
