"""The unregistered-tool check (plan.md P9.1, T569).

Reads the live in-process registry (`anchor.runtime.tools.registry.as_tool_registry`)
— the same dict `core.journal.two_phase` resolves calls against — so a
`ToolCall` naming a tool absent from it fails **in the editor**, rather
than at step 3 of a live run when the worker discovers the same thing the
hard way.
"""

from __future__ import annotations

import ast

from anchor.api.authoring.messages import unregistered_tool_message
from anchor.api.authoring.models import Finding
from anchor.runtime.tools.registry import as_tool_registry


def check(source: str) -> list[Finding]:
    tree = ast.parse(source)
    registered = set(as_tool_registry().keys())
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_toolcall(node)):
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        tool_name = node.args[0].value
        if not isinstance(tool_name, str):
            continue
        if tool_name not in registered:
            findings.append(
                Finding(
                    check="unregistered_tool",
                    line=node.lineno,
                    column=node.col_offset,
                    message=unregistered_tool_message(node.lineno, tool_name),
                )
            )
    return findings


def _is_toolcall(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "ToolCall"
    if isinstance(func, ast.Attribute):
        return func.attr == "ToolCall"
    return False
