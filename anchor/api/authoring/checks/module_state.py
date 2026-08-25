"""The module-level mutable state check (plan.md P9.1, T568;
agent-contract.md rule 4).

State held outside `ctx` does not survive a handoff and is the most likely
authoring mistake — the runtime reconstructs `ctx` fresh from the journal
on every attempt, but a module-level variable is process memory, not
journal state.

Two static signals catch the common cases without requiring full
alias/points-to analysis:

1. A `global` statement inside any function body — a function cannot
   reassign a module-level name without first declaring `global`, so this
   signal has no false negatives for reassignment and no false positives
   at all.
2. A call to a mutating method (`.append`, `.extend`, `.update`, `.add`,
   `.pop`, `.remove`, `.clear`, `.discard`, `.popitem`, `.insert`) on a
   bare name that is also assigned a mutable literal (list/dict/set) at
   module level — mutation of a module-level container in place, which
   needs no `global` statement to work and is the second most common form
   of this mistake.
"""

from __future__ import annotations

import ast

from anchor.api.authoring.messages import module_state_message
from anchor.api.authoring.models import Finding

_MUTATING_METHODS = {
    "append",
    "extend",
    "update",
    "add",
    "pop",
    "remove",
    "clear",
    "discard",
    "popitem",
    "insert",
}


def _module_level_mutable_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.List | ast.Dict | ast.Set):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def check(source: str) -> list[Finding]:
    tree = ast.parse(source)
    findings: list[Finding] = []
    mutable_names = _module_level_mutable_names(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Global):
                    for name in inner.names:
                        findings.append(
                            Finding(
                                check="module_level_mutable_state",
                                line=inner.lineno,
                                column=inner.col_offset,
                                message=module_state_message(inner.lineno, name),
                            )
                        )
                elif (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr in _MUTATING_METHODS
                    and isinstance(inner.func.value, ast.Name)
                    and inner.func.value.id in mutable_names
                ):
                    findings.append(
                        Finding(
                            check="module_level_mutable_state",
                            line=inner.lineno,
                            column=inner.col_offset,
                            message=module_state_message(inner.lineno, inner.func.value.id),
                        )
                    )
    return findings
