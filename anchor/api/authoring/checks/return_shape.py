"""The return-shape check (plan.md P9.1, T567; agent-contract.md rule 5).

`decide_next_step` must return/yield exactly one of `ToolCall(...)`,
`ModelCall(...)` or `Done(...)` on every reachable `return` or `yield`.
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

        # Check if function is a generator (contains yield statements)
        is_generator = any(isinstance(sub, ast.Yield | ast.YieldFrom) for sub in ast.walk(node))

        for ret in ast.walk(node):
            if isinstance(ret, ast.Yield):
                if ret.value is None:
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
            elif isinstance(ret, ast.Return):
                if ret.value is None:
                    if is_generator:
                        continue  # Empty return in a generator is valid termination
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
