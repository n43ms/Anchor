"""T027 — no timing/retry/concurrency constant lives outside `anchor.core.config`
(FR-059).

Pure: AST walk, no I/O, no database.

**Scope of the heuristic.** FR-059 names five categories precisely: "lease
duration, renewal interval, step timeout, retry limits and concurrency
caps." Rather than a broad, false-positive-prone pattern ("any numeric
literal near a name containing 'time'"), this test targets the fifteen
seeded `runtime_config` keys by name (data-model.md §9) — a hardcoded
assignment, default parameter, or keyword argument named
`lease_duration_ms`, `backoff_cap_ms`, `per_worker_concurrency`, etc.,
anywhere outside `anchor/core/config/`, is exactly the failure mode FR-059
forbids: the same conceptual value living in two places, one of them not
the config module. A vaguer heuristic would flag unrelated things like
`anchor.core.db.pool`'s connection-pool sizing or the worker's heartbeat
cadence, neither of which is a `runtime_config` key.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANCHOR_PACKAGE = REPO_ROOT / "anchor"
CONFIG_PACKAGE = ANCHOR_PACKAGE / "core" / "config"

# The fifteen seeded runtime_config keys (data-model.md §9). Matched by
# substring, case-sensitive, against assignment targets, function
# parameter names, and call-site keyword argument names — so
# `lease_duration_ms = 4_000` and `lease_ms = 4_000` both trip it (the
# second because "lease_duration" isn't literally present... intentionally
# NOT matched: substring matching on the *value's own name* only catches
# the value under (a version of) its real name, which is the case that
# actually happens when someone copies a config value out to "simplify"
# a call site).
_PROTECTED_KEY_SUBSTRINGS = (
    "lease_duration",
    "renewal_interval",
    "margin_ms",
    "step_timeout",
    "max_attempts_per_step",
    "backoff_base",
    "backoff_factor",
    "backoff_jitter",
    "backoff_cap",
    "per_worker_concurrency",
    "global_concurrency_cap",
    "reclaim_poll_interval",
    "renewal_latency_warn",
    "max_event_payload",
)


def _iter_python_files(root: Path, *, exclude: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if exclude not in p.parents and p != exclude)


def _is_numeric_literal(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float))


def _name_is_protected(name: str) -> bool:
    return any(substring in name for substring in _PROTECTED_KEY_SUBSTRINGS)


def _find_violations(tree: ast.AST) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        # Module/class/function-level assignment: `lease_duration_ms = 4000`
        if isinstance(node, ast.Assign) and _is_numeric_literal(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name) and _name_is_protected(target.id):
                    violations.append((node.lineno, target.id))

        elif isinstance(node, ast.AnnAssign) and _is_numeric_literal(node.value):
            if isinstance(node.target, ast.Name) and _name_is_protected(node.target.id):
                violations.append((node.lineno, node.target.id))

        # Function default: `def f(step_timeout_ms: int = 30_000): ...`
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            # `args.args[-0:]` is `args.args[0:]` — ALL of them, not none —
            # so a function with zero positional defaults must be handled
            # explicitly rather than trusting the negative slice.
            defaults = (
                list(zip(args.args[-len(args.defaults) :], args.defaults, strict=True))
                if args.defaults
                else []
            )
            kw_defaults = list(zip(args.kwonlyargs, args.kw_defaults, strict=True))
            for arg, default in [*defaults, *kw_defaults]:
                if (
                    default is not None
                    and _is_numeric_literal(default)
                    and _name_is_protected(arg.arg)
                ):
                    violations.append((node.lineno, arg.arg))

        # Call-site keyword argument: `RuntimeSettings(lease_duration_ms=4000)`
        # is legitimate ONLY inside anchor/core/config/ (that's where the
        # profiles are defined) — this branch fires on every file the walk
        # visits, and the walk itself already excludes that package.
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg and _name_is_protected(kw.arg) and _is_numeric_literal(kw.value):
                    violations.append((node.lineno, kw.arg))

    return violations


def test_no_runtime_config_key_is_hardcoded_outside_the_config_package() -> None:
    all_violations: dict[str, list[tuple[int, str]]] = {}
    for path in _iter_python_files(ANCHOR_PACKAGE, exclude=CONFIG_PACKAGE):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        found = _find_violations(tree)
        if found:
            all_violations[str(path.relative_to(REPO_ROOT))] = found

    assert not all_violations, (
        "runtime_config keys must be read from anchor.core.config, never hardcoded "
        "elsewhere (FR-059), but found:\n"
        + "\n".join(
            f"  {path}: " + ", ".join(f"line {ln} ({name})" for ln, name in found)
            for path, found in all_violations.items()
        )
    )


def test_the_heuristic_actually_fires_on_a_planted_violation() -> None:
    """A heuristic that never fires is worse than no test at all — this
    proves the walk's logic actually detects the failure mode it exists
    for, using a synthetic module rather than requiring one to exist (and
    be forgotten about) in the real codebase.
    """
    planted = ast.parse("lease_duration_ms = 4000\n")
    assert _find_violations(planted) == [(1, "lease_duration_ms")]

    planted_kwarg = ast.parse("register_tool(backoff_cap_ms=10_000)\n")
    assert _find_violations(planted_kwarg) == [(1, "backoff_cap_ms")]

    # A name that happens to contain a protected substring but is not
    # actually the config value (e.g. a docstring or an unrelated numeric
    # constant) must NOT trip the heuristic.
    unrelated = ast.parse("page_size = 4000\n")
    assert _find_violations(unrelated) == []
