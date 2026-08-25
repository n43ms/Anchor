"""The unbounded-self-recursion check (plan.md P9.1, T571).

Catches the trivial infinite-run case: a `decide_next_step` whose every
reachable `return` calls itself again, with no path that ever returns a
`ToolCall`, `ModelCall` or `Done`. The attempt cap enforced in phase 6
(`core.worker` retry/attempt limits) catches everything this check
misses — a self-call reachable only along one of several branches, for
instance — so this check is deliberately narrow: it flags only the case
where *no* branch can ever terminate the loop, which the phase-6 cap
cannot distinguish from a slow-but-finite draft at authoring time.
"""

from __future__ import annotations

import ast

from anchor.api.authoring.messages import self_recursion_message
from anchor.api.authoring.models import Finding

_ACTION_NAMES = {"ToolCall", "ModelCall", "Done"}


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
    return None


def check(source: str) -> list[Finding]:
    tree = ast.parse(source)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        returns = [inner for inner in ast.walk(node) if isinstance(inner, ast.Return)]
        if not returns:
            continue
        names = [_call_name(r.value) if r.value is not None else None for r in returns]
        if not names or any(n in _ACTION_NAMES for n in names):
            continue
        if all(n == node.name for n in names):
            findings.append(
                Finding(
                    check="unbounded_self_recursion",
                    line=node.lineno,
                    column=node.col_offset,
                    message=self_recursion_message(node.lineno, node.name),
                )
            )
    return findings
