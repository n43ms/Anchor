<%!
import re

%>"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

Every constraint, trigger, and function in this migration is raw SQL,
executed via `op.execute()`. This migration is forward-only: `downgrade()`
is deliberately left empty (see ops/migrations/README.md and
tests/boundary/test_migrations_forward_only.py). Rolling back a schema this
DDL-heavy — indexes, triggers with embedded RAISE logic, cross-row
assertions — safely is not worth the maintenance burden of a downgrade path
that is exercised far less often than the schema itself.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    # Deliberately empty: migrations are forward-only.
    pass
