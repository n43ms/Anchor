"""T374 — `orphaned` appears in no column of any table and is computed at
read time (data-model.md §12): storing it would require a writer at the
exact moment nobody owns the run, which is a contradiction in terms.

Pure: reads migration source directly, no database required.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "ops" / "migrations" / "versions"


def test_no_migration_declares_an_orphaned_column() -> None:
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        # A column declaration looks like `orphaned  boolean ...` inside a
        # CREATE TABLE / ALTER TABLE ADD COLUMN body — matched narrowly
        # (word boundary, followed by whitespace then a type) so this does
        # not also flag the word appearing in a comment explaining why it
        # is absent.
        assert not re.search(r"\borphaned\s+boolean\b", source, re.IGNORECASE), (
            f"{path.name} declares an `orphaned` column — it must be derived at read "
            "time, never stored (data-model.md §12)"
        )


def test_orphaned_is_computed_in_sql_at_every_read_site() -> None:
    """Every place `orphaned` appears in a response is derived by the same
    SQL expression against the database clock (`I5`), never read back from
    a stored column.
    """
    expression = "status = 'running' AND lease_expires_at < now()"
    read_sites = (
        REPO_ROOT / "anchor" / "api" / "serializers" / "runs.py",
        REPO_ROOT / "anchor" / "api" / "serializers" / "timeline.py",
    )
    for path in read_sites:
        source = path.read_text(encoding="utf-8")
        assert expression in source, f"{path} must derive orphaned via '{expression}'"
