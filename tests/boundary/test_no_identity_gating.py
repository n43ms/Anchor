"""T373 — no route reads a session, cookie, token, or user identifier
(FR-114). Every restriction in this API is a function of deployment mode
alone (`app.state.deployment_mode`, decided once at process start from
configuration), never of who is asking — there is no "who is asking" for
this API to know, by design (§18, §21.7: no accounts, no login, no
per-user data).

Pure: AST walk over `anchor/api/`, no I/O, no database.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "anchor" / "api"

# Attribute/method names that would signal an identity check if they
# appeared anywhere under anchor/api/ — a cookie jar, a bearer token, a
# session object, or an auth dependency.
_FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "cookies",
        "session",
        "authorization",
    }
)
_FORBIDDEN_SUBSTRINGS_IN_STRINGS = ("authorization", "bearer ", "session_id", "user_id")


def _iter_python_files() -> list[Path]:
    return sorted(API_ROOT.rglob("*.py"))


def _find_identity_reads(tree: ast.AST) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.lower() in _FORBIDDEN_ATTRIBUTES:
            findings.append((node.lineno, node.attr))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            for forbidden in _FORBIDDEN_SUBSTRINGS_IN_STRINGS:
                if forbidden in lowered:
                    findings.append((node.lineno, node.value))
    return findings


def test_no_route_reads_a_session_cookie_or_token() -> None:
    all_findings: dict[str, list[tuple[int, str]]] = {}
    for path in _iter_python_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        found = _find_identity_reads(tree)
        if found:
            all_findings[str(path.relative_to(REPO_ROOT))] = found

    assert not all_findings, (
        "an identity-shaped read was found under anchor/api/ (FR-114) — every "
        "restriction in this API must be a function of deployment mode alone:\n"
        + "\n".join(
            f"  {path}: " + ", ".join(f"line {ln} ({name!r})" for ln, name in found)
            for path, found in all_findings.items()
        )
    )


def test_deployment_mode_gating_uses_only_app_state() -> None:
    """The one legitimate form of mode-based restriction in this codebase
    (§31.2) — `request.app.state.deployment_mode`, set once at process
    start, never per-request. Spot-checks that this is in fact how the
    scoped-to-demo routes gate themselves, so the previous test's absence
    of forbidden reads isn't merely because gating was removed entirely.
    """
    runs_source = (API_ROOT / "routers" / "runs.py").read_text(encoding="utf-8")
    assert "request.app.state.deployment_mode" in runs_source
