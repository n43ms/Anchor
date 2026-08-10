"""The shared AST determinism-ban checker (plan.md P2.3, T128-T129, D-27).

Walks a module's source for references to `datetime`, `time`, `random`, or
`uuid` — the four modules `ctx.now()` / `ctx.random()` / `ctx.new_id()`
replace. Written once here, against agent code, and reused unmodified by
the phase-9 authoring validator, so the rule has exactly one implementation
to keep correct (constitution Principle III: "A required test MUST import
every module under runtime/agents/ and fail if any references datetime,
time, random, or uuid directly. The same check runs interactively in the
authoring validator.").
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

# Each banned top-level module name maps to the StepContext call that
# replaces it, so the finding teaches the fix rather than only naming the
# violation (FR-124).
BANNED_MODULES: dict[str, str] = {
    "datetime": "ctx.now()",
    "time": "ctx.now()",
    "random": "ctx.random()",
    "uuid": "ctx.new_id()",
}


@dataclass(frozen=True, slots=True)
class DeterminismFinding:
    module_path: str
    line: int
    column: int
    banned_name: str

    @property
    def replacement(self) -> str:
        return BANNED_MODULES[self.banned_name]

    @property
    def message(self) -> str:
        return (
            f"{self.module_path}:{self.line}:{self.column}: direct reference to "
            f"{self.banned_name!r} is forbidden in agent code — use {self.replacement} "
            "instead, so the value is journaled and replay stays deterministic "
            "(constitution Principle III)"
        )


def check_source(source: str, *, module_path: str) -> list[DeterminismFinding]:
    """Return every reference to a banned module in `source`.

    Catches both the import statement (`import random`, `from uuid import
    uuid4`) and any bare use of the name afterward (`datetime.now()`,
    `dt = datetime`) — an `ast.Name` node fires for both, since `ast.walk`
    visits the `Name` node inside an `Attribute` access as well as a
    standalone reference. This is deliberately blunt: a local variable that
    happens to be named `random` also flags, and that false-positive risk
    is accepted in exchange for not requiring alias-tracking to catch
    `import random as r; r.random()`.
    """
    tree = ast.parse(source, filename=module_path)
    findings: list[DeterminismFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BANNED_MODULES:
                    findings.append(
                        DeterminismFinding(module_path, node.lineno, node.col_offset, root)
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in BANNED_MODULES:
                findings.append(DeterminismFinding(module_path, node.lineno, node.col_offset, root))
        elif isinstance(node, ast.Name) and node.id in BANNED_MODULES:
            findings.append(DeterminismFinding(module_path, node.lineno, node.col_offset, node.id))
    return findings


def check_file(path: Path) -> list[DeterminismFinding]:
    return check_source(path.read_text(encoding="utf-8"), module_path=str(path))
