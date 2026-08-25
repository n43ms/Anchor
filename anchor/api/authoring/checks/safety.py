"""The missing-safety-declaration check (plan.md P9.1, T570).

A draft may declare a new tool inline with the `@anchor.tool(...)` /
`@tool(...)` decorator (`docs/tools.md`'s SDK-convenience form of
`@anchor.tool(safety="retry_safe")`). `anchor.runtime.tools.registry.register`
already refuses
a `safety` value outside `retry_safe` / `reconcilable` / `unsafe` at
registration time (`_validate`), but a missing `safety=` keyword entirely
is a `TypeError` at decoration time — a mistake worth catching here,
before the draft is ever imported, because "there is no default to fall
back to" is exactly the invariant this check exists to teach early.
"""

from __future__ import annotations

import ast

from anchor.api.authoring.messages import missing_safety_message
from anchor.api.authoring.models import Finding


def check(source: str) -> list[Finding]:
    tree = ast.parse(source)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not (isinstance(decorator, ast.Call) and _is_tool_decorator(decorator)):
                continue
            has_safety = any(kw.arg == "safety" for kw in decorator.keywords)
            if not has_safety:
                findings.append(
                    Finding(
                        check="missing_safety_declaration",
                        line=decorator.lineno,
                        column=decorator.col_offset,
                        message=missing_safety_message(decorator.lineno, node.name),
                    )
                )
    return findings


def _is_tool_decorator(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "tool"
    if isinstance(func, ast.Attribute):
        return func.attr == "tool"
    return False
