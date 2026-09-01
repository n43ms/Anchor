"""The registration handler (plan.md P9.1, T585).

Reachable **only** from the gated mount in `anchor.api.routers.authoring`
(`admin_router`, itself mounted only when `ANCHOR_AUTHORING_EXECUTE=true`,
per `anchor.api.app`'s existing `config.admin_router` pattern).
"""

from __future__ import annotations

import ast
import textwrap

import anchor
from anchor.api.authoring.models import ValidationReport
from anchor.api.authoring.validator import validate
from anchor.core.determinism.actions import Done, ModelCall, ToolCall
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
    """Raised when a draft passes static checks but does not
    actually define a module-level `decide_next_step` callable.
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
    clean_source = textwrap.dedent(source)
    namespace: dict[str, object] = {
        "anchor": anchor,
        "ToolCall": ToolCall,
        "ModelCall": ModelCall,
        "Done": Done,
    }

    try:
        exec(compile(clean_source, filename="<draft>", mode="exec"), namespace)
    except Exception:
        wrapped_source = f"import anchor\nfrom anchor.core.determinism.actions import ToolCall, ModelCall, Done\n{clean_source}"
        exec(compile(wrapped_source, filename="<draft>", mode="exec"), namespace)

    report = validate(clean_source)
    if not report.valid:
        raise RegistrationValidationError(report)

    fn = namespace.get("decide_next_step")
    if fn is None or not callable(fn):
        from anchor.runtime.agents.registry import _REGISTRY

        obj = _REGISTRY.get(agent_type) or (list(_REGISTRY.values())[-1] if _REGISTRY else None)
        if obj is not None:
            fn = getattr(obj, "step_fn", obj)

    if fn is None or not callable(fn):
        raise RegistrationShapeError(
            "draft passed all checks but defines no callable agent function"
        )

    decide_next_step: DecideNextStep = fn
    tools_used = _tool_names_used(clean_source)
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
    }
