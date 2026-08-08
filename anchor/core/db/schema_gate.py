"""The schema-version gate (D-45, FR-128).

Every process compares the revision *applied* to the database against the
revision its own bundled migration scripts consider HEAD, and refuses to
start on a mismatch, naming both. No long-running process ever runs
`alembic upgrade` itself — that happens exactly once, in the one-shot
`migrate` compose service.

"The revision the code was built against" is computed directly from the
migration scripts shipped inside this image, rather than from a
separately-stamped build variable: the two are the same directory, copied
into the image at build time, so asking Alembic for its own head is asking
the question the gate needs answered without inventing a second source of
truth for it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import asyncpg
from alembic.config import Config
from alembic.script import ScriptDirectory

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "ops" / "migrations"


class SchemaVersionMismatchError(Exception):
    """Raised when the applied revision differs from the code's built-against
    revision. Carries both so the refusal message never has to be
    reconstructed by a human debugging a rollout.
    """

    def __init__(self, applied: str | None, built_against: str) -> None:
        self.applied = applied
        self.built_against = built_against
        super().__init__(
            f"schema mismatch: database has revision {applied!r}, "
            f"this process was built against {built_against!r}"
        )


def built_against_revision() -> str:
    """The HEAD of the migration scripts bundled in this image."""
    config = Config(str(_MIGRATIONS_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(_MIGRATIONS_DIR))
    script_dir = ScriptDirectory.from_config(config)
    head = script_dir.get_current_head()
    if head is None:
        raise RuntimeError("no migration scripts found; cannot determine HEAD revision")
    return head


async def applied_revision(conn: asyncpg.Connection[Any]) -> str | None:
    """The revision currently applied to the database, or `None` if the
    `alembic_version` table does not exist yet (migrations never ran).
    """
    exists = await conn.fetchval("SELECT to_regclass('public.alembic_version') IS NOT NULL")
    if not exists:
        return None
    revision: str | None = await conn.fetchval("SELECT version_num FROM alembic_version")
    return revision


async def assert_schema_matches(conn: asyncpg.Connection[Any]) -> str:
    """Raise `SchemaVersionMismatchError` on any mismatch; otherwise return
    the matched revision. Called once, at process startup, before the
    process registers itself or accepts any work.
    """
    built = built_against_revision()
    applied = await applied_revision(conn)
    if applied != built:
        raise SchemaVersionMismatchError(applied=applied, built_against=built)
    return built
