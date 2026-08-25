"""The registration handler (plan.md P9.1, T585).

Reachable **only** from the gated mount in `anchor.api.routers.authoring`
(`admin_router`, itself mounted only when `ANCHOR_AUTHORING_EXECUTE=true`,
per `anchor.api.app`'s existing `config.admin_router` pattern). This
module is the one place in the whole API package that reaches
`anchor.runtime.agents.registry.register` — the registry-mutation call —
which is exactly what `tests/boundary/test_no_import_path_to_registry_mutation.py`
asserts is unreachable when the flag is unset: it walks the API package's
import graph and fails if any module reachable from an *unconditionally
mounted* router imports this one.

Re-runs full validation before loading into the live registry (never
trusts a client-supplied `valid: true` it did not itself compute), and
executes the draft exactly once, via `exec`, to obtain the
`decide_next_step` callable — there is no other way to turn source text
into a callable object. This is a deliberate, local-mode-only exception to
"nothing here executes the draft": §27.3 draws the line at *registration*,
not at validation, and demonstration mode never reaches this module at
all because the route it lives behind does not exist.
"""

from __future__ import annotations

import ast

from anchor.api.authoring.models import ValidationReport
from anchor.api.authoring.validator import validate
from anchor.runtime.agents.registry import DecideNextStep, register


class RegistrationValidationError(ValueError):
    """Raised when the draft fails validation; carries the full report so
    the caller can return 422 with the same `ValidationReport` shape the
    `/validate` endpoint would have returned for this source.
    """

    def __init__(self, report: ValidationReport) -> None:
        super().__init__("draft failed validation; nothing was registered")
        self.report = report


class RegistrationShapeError(ValueError):
    """Raised when a draft passes the six static checks but does not
    actually define a module-level `decide_next_step` callable — the
    checks operate on AST shape, not on execution, so this is the one
    condition only `exec` itself can discover.
    """


def _tool_names_used(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_toolcall = (isinstance(func, ast.Name) and func.id == "ToolCall") or (
            isinstance(func, ast.Attribute) and func.attr == "ToolCall"
        )
        if is_toolcall and node.args and isinstance(node.args[0], ast.Constant):
            value = node.args[0].value
            if isinstance(value, str):
                names.add(value)
    return tuple(sorted(names))


def register_draft(source: str, agent_type: str) -> dict[str, object]:
    # DraftSyntaxError is deliberately not caught here — it propagates to
    # the router exactly as it does for /api/authoring/validate, so a
    # draft that fails to parse gets the same 422 shape from every
    # authoring endpoint rather than a second, subtly different one here.
    report = validate(source)

    if not report.valid:
        raise RegistrationValidationError(report)

    namespace: dict[str, object] = {}
    exec(compile(source, filename="<draft>", mode="exec"), namespace)
    fn = namespace.get("decide_next_step")
    if fn is None or not callable(fn):
        raise RegistrationShapeError(
            "draft passed all six checks but defines no callable decide_next_step"
        )

    decide_next_step: DecideNextStep = fn
    tools_used = _tool_names_used(source)
    docstring = namespace.get("__doc__")
    register(
        agent_type,
        decide_next_step,
        description=docstring.strip() if isinstance(docstring, str) else "",
        tools_used=tools_used,
    )
    return {
        "agent_type": agent_type,
        "contract_version": "1.0.0",
        "description": "",
        "expected_step_count": None,
        "tools_used": list(tools_used),
        "stubbed_model": False,
    }
