"""The return-shape check (plan.md P9.1, T567; agent-contract.md rule 5).

`decide_next_step` must return exactly one of `ToolCall(...)`,
`ModelCall(...)` or `Done(...)` on every reachable `return`. Anything else
— a bare `return`, a dict literal, a tuple, a call to something else —
stalls the worker loop, because the runtime has nothing it recognizes to
act on.

This is deliberately restricted to functions named `decide_next_step`:
that is the one function name the agent contract gives meaning to, and
flagging return statements in arbitrary helper functions the draft defines
would produce false positives against ordinary helper code.
"""

from __future__ import annotations

import ast

from anchor.api.authoring.messages import return_shape_message
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
        if not (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == "decide_next_step"
        ):
            continue
        for ret in ast.walk(node):
            if not isinstance(ret, ast.Return):
                continue
            if ret.value is None:
                findings.append(
                    Finding(
                        check="return_shape",
                        line=ret.lineno,
                        column=ret.col_offset,
                        message=return_shape_message(ret.lineno, empty=True),
                    )
                )
                continue
            name = _call_name(ret.value)
            if name not in _ACTION_NAMES:
                findings.append(
                    Finding(
                        check="return_shape",
                        line=ret.lineno,
                        column=ret.col_offset,
                        message=return_shape_message(ret.lineno),
                    )
                )
    return findings
