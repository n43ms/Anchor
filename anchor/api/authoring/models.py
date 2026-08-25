"""`ValidationReport` and `Finding` (plan.md P9.1, T572; contracts/openapi.yaml
`ValidationReport`).

Kept as plain dataclasses, not pydantic models, because nothing here is
parsed from external input — every `ValidationReport` is *constructed* by
`validator.py` from a draft's AST, and `anchor/api/routers/authoring.py`
calls `.to_dict()` at the response boundary. A pydantic model would buy
input validation this module never needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CheckName = Literal[
    "determinism_imports",
    "return_shape",
    "module_level_mutable_state",
    "unregistered_tool",
    "missing_safety_declaration",
    "unbounded_self_recursion",
]

Severity = Literal["error", "warning"]

# contracts/agent-contract.md's pre-registration checklist, §35 — the four
# judgements no static check in this module can make. Carried on every
# ValidationReport, including a clean one, so the ceiling travels with the
# response rather than depending on a console that might render `valid:
# true` alone (FR-134, D-59).
UNCHECKED_CHECKLIST: tuple[str, ...] = (
    "Every branch reads state from ctx, never a variable held across calls",
    "Every loop filters using ctx.completed_tool_args(...), not a counter",
    "There is a reachable Done(...) branch once the loop's work is exhausted",
    "Every ctx.call_tool(...) checks ctx.has_result(...) first",
)


@dataclass(frozen=True, slots=True)
class Finding:
    check: CheckName
    line: int
    message: str
    column: int | None = None
    severity: Severity = "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    valid: bool
    findings: tuple[Finding, ...] = field(default_factory=tuple)
    unchecked: tuple[str, ...] = UNCHECKED_CHECKLIST

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "findings": [f.to_dict() for f in self.findings],
            "unchecked": list(self.unchecked),
        }
