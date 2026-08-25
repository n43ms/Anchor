"""The determinism-imports check (plan.md P9.1, T566).

Reuses `anchor.core.determinism.ast_check.check_source` unmodified — the
same AST walk that runs as a required test against every module under
`anchor/runtime/agents/` (constitution Principle III) runs here
interactively, against a draft that has never executed, so there is
exactly one implementation of "what counts as a banned reference" to keep
correct (D-27).
"""

from __future__ import annotations

from anchor.api.authoring.messages import determinism_message
from anchor.api.authoring.models import Finding
from anchor.core.determinism.ast_check import check_source


def check(source: str) -> list[Finding]:
    findings = check_source(source, module_path="<draft>")
    return [
        Finding(
            check="determinism_imports",
            line=f.line,
            column=f.column,
            message=determinism_message(f.line, f.column, f.banned_name, f.replacement),
        )
        for f in findings
    ]
