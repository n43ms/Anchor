"""T561 — the import-path test (FR-113).

With `ANCHOR_AUTHORING_EXECUTE` unset, no import path in the API package
reaches registry-mutation code (`anchor.api.authoring.register`, whose
docstring names it as the one place that calls
`anchor.runtime.agents.registry.register`).

Static, not behavioural: walks the AST import graph of every module under
`anchor/api/` reachable from `anchor.api.app`'s **unconditionally mounted**
routers, and fails if any of them imports `anchor.api.authoring.register`
at module level. A dynamic "is it in sys.modules" check would pass or fail
depending on import order and test pollution from other test files in the
same process; walking the graph statically has neither problem.
"""

from __future__ import annotations

import ast
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[2] / "anchor" / "api"
_FORBIDDEN_MODULE = "anchor.api.authoring.register"

# The unconditionally-mounted entry points into anchor/api, per
# anchor.api.app.create_app: every router included outside the
# `if os.environ.get("ANCHOR_AUTHORING_EXECUTE", ...)` guard, plus app.py
# itself. `authoring.admin_router` is deliberately excluded — it IS the
# gated entry point, and its own module lazily imports the forbidden
# module inside the handler body specifically so this set does not have to
# special-case it.
_UNCONDITIONAL_ENTRY_POINTS = (
    "anchor.api.app",
    "anchor.api.routers.health",
    "anchor.api.routers.runs",
    "anchor.api.routers.workers",
    "anchor.api.routers.chaos",
    "anchor.api.routers.registry",
    "anchor.api.routers.observability",
    "anchor.api.routers.config",
    "anchor.api.routers.authoring",
    "anchor.api.ws.fleet",
    "anchor.api.ws.runs",
)


def _module_path(module_name: str) -> Path | None:
    parts = module_name.split(".")
    candidate = Path(*parts).with_suffix(".py")
    for base in (_API_ROOT.parent.parent,):
        full = base / candidate
        if full.is_file():
            return full
    return None


def _top_level_imports(path: Path) -> set[str]:
    """Only imports at module scope — a `from x import y` inside a
    function body (like `authoring.admin_router`'s handler) is a deferred
    import that does not execute merely because the module was imported,
    which is exactly the distinction this test exists to make.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _reachable_modules(start: str) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        path = _module_path(name)
        if path is None:
            continue
        for imported in _top_level_imports(path):
            if imported.startswith("anchor.") and imported not in seen:
                stack.append(imported)
    return seen


def test_forbidden_module_unreachable_from_any_unconditional_entry_point() -> None:
    for entry in _UNCONDITIONAL_ENTRY_POINTS:
        reachable = _reachable_modules(entry)
        assert _FORBIDDEN_MODULE not in reachable, (
            f"{entry} reaches {_FORBIDDEN_MODULE} via a module-level import; "
            "registry-mutation code must only be reachable from the gated "
            "admin_router handler, via a deferred (in-function) import"
        )


def test_forbidden_module_only_imported_lazily_by_its_own_router() -> None:
    router_path = _API_ROOT / "routers" / "authoring.py"
    assert _FORBIDDEN_MODULE not in _top_level_imports(router_path)
    source = router_path.read_text(encoding="utf-8")
    assert "from anchor.api.authoring.register import" in source
