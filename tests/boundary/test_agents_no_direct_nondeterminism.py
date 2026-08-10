"""T108 — the AST determinism ban over `anchor/runtime/agents/`.

Fails on any reference to `datetime`, `time`, `random`, or `uuid`, naming
the offending module and line (FR-035, constitution Principle III).
"""

from __future__ import annotations

from pathlib import Path

from anchor.core.determinism.ast_check import check_file, check_source

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_PACKAGE = REPO_ROOT / "anchor" / "runtime" / "agents"


def _iter_agent_modules() -> list[Path]:
    return sorted(AGENTS_PACKAGE.rglob("*.py"))


def test_no_agent_module_references_a_banned_nondeterminism_source() -> None:
    violations: dict[str, list[str]] = {}
    for path in _iter_agent_modules():
        findings = check_file(path)
        if findings:
            violations[str(path.relative_to(REPO_ROOT))] = [f.message for f in findings]

    assert not violations, "\n".join(msg for messages in violations.values() for msg in messages)


def test_the_walk_actually_covers_agent_files() -> None:
    """A ban that silently walks zero files proves nothing."""
    files = _iter_agent_modules()
    assert len(files) >= 2, (
        f"expected at least 2 files under {AGENTS_PACKAGE}, found {len(files)} — "
        "the walk is probably misconfigured"
    )


def test_checker_actually_detects_each_banned_module() -> None:
    """Prove the checker is not vacuously passing by feeding it code that
    must be flagged, one banned module at a time.
    """
    samples = {
        "datetime": "import datetime\nx = datetime.datetime.now()\n",
        "time": "import time\nx = time.time()\n",
        "random": "import random\nx = random.random()\n",
        "uuid": "import uuid\nx = uuid.uuid4()\n",
    }
    for banned_name, source in samples.items():
        findings = check_source(source, module_path="<test>")
        assert any(f.banned_name == banned_name for f in findings), (
            banned_name,
            findings,
        )


def test_checker_is_silent_on_clean_source() -> None:
    findings = check_source("def f(ctx):\n    return ctx.now()\n", module_path="<test>")
    assert findings == []
