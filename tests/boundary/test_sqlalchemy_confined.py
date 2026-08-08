"""T003 — `sqlalchemy` is imported nowhere outside `ops/migrations/`.

Pure: walks the AST of every `.py` file under `anchor/`, no I/O beyond
reading source files, no database needed. The one place SQLAlchemy is
legitimately used is `ops/migrations/env.py`'s sync engine, which is
outside `anchor/` entirely and untouched by this walk (D-05, D-34's
sibling rule: no ORM on the hot path).
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANCHOR_PACKAGE = REPO_ROOT / "anchor"


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _imports_sqlalchemy(tree: ast.AST) -> list[int]:
    """Return the line numbers of any `import sqlalchemy` or
    `from sqlalchemy import ...` in the module.
    """
    offending_lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sqlalchemy" or alias.name.startswith("sqlalchemy."):
                    offending_lines.append(node.lineno)
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == "sqlalchemy" or node.module.startswith("sqlalchemy."))
        ):
            offending_lines.append(node.lineno)
    return offending_lines


def test_sqlalchemy_imported_nowhere_under_anchor() -> None:
    violations: dict[str, list[int]] = {}
    for path in _iter_python_files(ANCHOR_PACKAGE):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        lines = _imports_sqlalchemy(tree)
        if lines:
            violations[str(path.relative_to(REPO_ROOT))] = lines

    assert not violations, (
        "sqlalchemy must be confined to ops/migrations/, but was imported in:\n"
        + "\n".join(f"  {path} (line {lines})" for path, lines in violations.items())
    )


def test_the_walk_actually_covers_files() -> None:
    """A confinement test that silently walks zero files proves nothing.
    Guard against the glob pattern or root path being wrong.
    """
    files = _iter_python_files(ANCHOR_PACKAGE)
    assert len(files) >= 10, (
        f"expected to walk at least 10 files under {ANCHOR_PACKAGE}, found {len(files)} — "
        "the walk is probably misconfigured"
    )
