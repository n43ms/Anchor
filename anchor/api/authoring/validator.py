"""The validator entrypoint (plan.md P9.1, T565).

Runs the six static checks over a draft's source text and assembles a
`ValidationReport`. Static analysis only — the source is parsed, walked,
and discarded; nothing here executes the draft or imports it as a module
(§27.5, FR-136). Callers (`anchor.api.routers.authoring`) must not persist
`source` anywhere; this module never sees a request object or a database
connection, so it cannot do so even by accident.

An empty `findings` list means no contract violation was found. It does
**not** mean the draft is correct — see `models.UNCHECKED_CHECKLIST`, which
every `ValidationReport` carries regardless of `valid` (§34, §35, FR-134).
"""

from __future__ import annotations

from anchor.api.authoring.checks import (
    determinism,
    module_state,
    recursion,
    return_shape,
    safety,
    tool_names,
)
from anchor.api.authoring.models import Finding, ValidationReport


class DraftSyntaxError(ValueError):
    """Raised when a draft does not parse as Python at all — distinct from
    a `ValidationReport` finding because a draft that cannot be parsed
    cannot be walked by any of the six checks, so there is nothing for
    them to run against. Callers should surface this as its own error
    rather than fabricate a finding under one of the six enum values none
    of which describe "not Python".
    """


def validate(source: str) -> ValidationReport:
    try:
        # Each check re-parses `source` independently: they are individually
        # unit-testable (T552-T557) against a bare source string, without a
        # shared mutable AST that one check could accidentally mutate for
        # the next.
        findings: list[Finding] = [
            *determinism.check(source),
            *return_shape.check(source),
            *module_state.check(source),
            *tool_names.check(source),
            *safety.check(source),
            *recursion.check(source),
        ]
    except SyntaxError as exc:
        raise DraftSyntaxError(f"draft does not parse as Python: {exc}") from exc

    findings.sort(key=lambda f: (f.line, f.column or 0, f.check))
    return ValidationReport(valid=not findings, findings=tuple(findings))
