"""T213 — the zombie-stall injection (`anchor.chaos.injections.stall`) must
not be reachable from any production import path: `anchor.api`,
`anchor.worker.__main__`, or `anchor.runtime`. It exists solely to construct
a failure condition on demand for tests and the chaos harness.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ANCHOR_ROOT = Path(__file__).resolve().parent.parent.parent / "anchor"
_STALL_MODULE = "anchor.chaos.injections.stall"

# Every production entrypoint/package that must never import the stall
# injection, directly or transitively. `anchor.chaos` itself is exempt (it
# is the harness), and `tests/` is exempt (checked separately by pytest
# discovery — this file lives there and imports the module directly).
_PRODUCTION_ROOTS = ("api", "worker", "runtime", "core")


def _direct_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.add(node.module)
    return found


def test_stall_injection_not_imported_by_any_production_module() -> None:
    offenders = []
    for root_name in _PRODUCTION_ROOTS:
        root = _ANCHOR_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            imports = _direct_imports(path)
            if any(
                name == _STALL_MODULE or name.startswith(_STALL_MODULE + ".") for name in imports
            ):
                offenders.append(str(path.relative_to(_ANCHOR_ROOT)))
    assert offenders == [], (
        f"production modules importing the stall injection: {offenders} — it must remain "
        "reachable only from tests/ and anchor/chaos/ (T213, FR-077)"
    )
