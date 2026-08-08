"""T045 — every migration is forward-only; no `downgrade()` does anything.

Pure: parses each migration module's AST and inspects `downgrade()`'s body.
No database, no Alembic runtime needed.
"""

from __future__ import annotations

import ast
from pathlib import Path

VERSIONS_DIR = Path(__file__).resolve().parents[2] / "ops" / "migrations" / "versions"


def _downgrade_bodies() -> dict[str, ast.FunctionDef]:
    bodies: dict[str, ast.FunctionDef] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
                bodies[path.name] = node
                break
        else:
            raise AssertionError(f"{path.name} defines no downgrade() function at all")
    return bodies


def _is_trivial(func: ast.FunctionDef) -> bool:
    """True if the body is only a docstring (optional) followed by `pass`
    — i.e., does nothing. Any real statement (an `op.execute`, a `return`
    with content, anything) fails this.
    """
    body = func.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # skip a leading docstring
    return len(body) == 1 and isinstance(body[0], ast.Pass)


def test_every_migration_has_at_least_one_version() -> None:
    assert list(VERSIONS_DIR.glob("*.py")), f"no migrations found under {VERSIONS_DIR}"


def test_every_migrations_downgrade_is_a_no_op() -> None:
    non_trivial = [name for name, func in _downgrade_bodies().items() if not _is_trivial(func)]
    assert not non_trivial, (
        "migrations are forward-only (ops/migrations/README.md) — downgrade() must be "
        f"empty, but these are not: {non_trivial}"
    )
