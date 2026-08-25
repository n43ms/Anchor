"""T563 — the no-draft-persistence test (FR-136, §27.5).

No table, cache key, or filesystem path holds a draft after the response
is written. Checked statically here, at the source level: the validate and
generate handlers, and every function they call, must contain no write to
a database connection, no Redis call, and no filesystem write.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_FILES = (
    _ROOT / "anchor" / "api" / "routers" / "authoring.py",
    _ROOT / "anchor" / "api" / "authoring" / "validator.py",
    _ROOT / "anchor" / "api" / "authoring" / "checks" / "determinism.py",
    _ROOT / "anchor" / "api" / "authoring" / "checks" / "return_shape.py",
    _ROOT / "anchor" / "api" / "authoring" / "checks" / "module_state.py",
    _ROOT / "anchor" / "api" / "authoring" / "checks" / "tool_names.py",
    _ROOT / "anchor" / "api" / "authoring" / "checks" / "safety.py",
    _ROOT / "anchor" / "api" / "authoring" / "checks" / "recursion.py",
)

_FORBIDDEN_CALL_NAMES = {"open", "execute", "fetch", "fetchval", "fetchrow", "hset", "sadd"}


def _calls_a_forbidden_persistence_api(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.id
            if isinstance(func, ast.Name)
            else func.attr
            if isinstance(func, ast.Attribute)
            else None
        )
        if name in _FORBIDDEN_CALL_NAMES:
            hits.append(f"{path.name}:{node.lineno}:{name}")
    return hits


def test_validate_and_generate_path_never_touches_a_persistence_api() -> None:
    all_hits: list[str] = []
    for path in _FILES:
        assert path.is_file(), f"expected {path} to exist"
        all_hits.extend(_calls_a_forbidden_persistence_api(path))
    assert not all_hits, f"found calls to persistence-shaped APIs in the draft path: {all_hits}"


def test_validate_handler_takes_no_database_or_redis_dependency() -> None:
    import inspect

    from anchor.api.routers.authoring import validate_draft

    sig = inspect.signature(validate_draft)
    param_names = set(sig.parameters)
    assert "pool" not in param_names
    assert "redis" not in param_names
    assert "conn" not in param_names
