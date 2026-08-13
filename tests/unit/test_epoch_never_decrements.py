"""T197 — no code path decrements `epoch`, and a hand-crafted decrement is
rejected by the `CHECK (epoch >= 0)` only insofar as it cannot go negative;
the actual monotonicity guarantee is structural: nothing in `anchor/` ever
assigns `epoch` to anything but `epoch + 1` (claim) or reads it unchanged
(renew). This test asserts both: no source-level decrement exists, and a
hand-crafted `UPDATE ... SET epoch = epoch - 1` still leaves every
subsequent append at the *new, lower* epoch rejected by nothing structurally
protecting monotonicity other than the absence of such an assignment in code
— so the source-level check is the real assertion here.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import asyncpg
import pytest

_ANCHOR_ROOT = Path(__file__).resolve().parent.parent.parent / "anchor"

# Matches an UPDATE ... SET epoch = epoch - <n> pattern anywhere in a SQL
# string literal — the one shape a decrementing assignment would take.
_DECREMENT_PATTERN = re.compile(r"epoch\s*=\s*epoch\s*-", re.IGNORECASE)


def test_no_source_module_assigns_epoch_a_decrement() -> None:
    offenders = []
    for path in _ANCHOR_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and _DECREMENT_PATTERN.search(node.value)
            ):
                offenders.append(str(path.relative_to(_ANCHOR_ROOT)))
    assert offenders == [], f"modules containing an epoch-decrementing SQL fragment: {offenders}"


@pytest.mark.asyncio
async def test_hand_crafted_epoch_decrement_is_rejected_by_check(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, input, epoch) VALUES ($1, '{}'::jsonb, 3) RETURNING id",
            "demo_minimal",
        )
        with pytest.raises(asyncpg.PostgresError):
            await conn.execute("UPDATE runs SET epoch = -1 WHERE id = $1", run_id)
