"""The three-state journal lookup (plan.md P5.4, T259; data-model.md §3).

A closed set of three dataclasses rather than an enum-plus-fields, so a
fourth state cannot be added by accident: every branch that matches on
`JournalState` is exhaustive, and `mypy --strict` flags a missing case at
every call site if a fourth variant is ever introduced.

This is the one place any code may read `tool_journal` to decide whether to
execute a tool. It queries the row directly rather than trusting anything
folded from `run_events` by replay, because the journal table — not the
event log — is what `tool_journal_result_once` and the partial
`WHERE result IS NULL` index make authoritative for this specific question.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import asyncpg

_LOOKUP_SQL = """
SELECT tool_name, args_canonical, args_hash, intent_epoch, result, result_at, result_epoch,
       resolution, attempts
FROM tool_journal
WHERE idempotency_key = $1
"""


@dataclass(frozen=True, slots=True)
class Completed:
    """A result was recorded. The step is replayed, not re-executed."""

    result: Any
    result_at: datetime
    result_epoch: int
    resolution: str | None


@dataclass(frozen=True, slots=True)
class NeverAttempted:
    """No journal row exists for this key. Execute normally."""


@dataclass(frozen=True, slots=True)
class Uncertain:
    """A row exists with no recorded result: the uncertainty window (`I8`).

    `resolution` carries what an operator has already decided, if anything.
    `None` means this window has never been resolved before, so the tool's
    *declared* policy applies. `"operator_marked_not_executed"` means an
    operator already reviewed this exact call and confirmed the effect had
    not occurred (D-24) — a second entry into this state for the same key,
    now authorized to execute directly rather than re-consult the tool's
    declared policy, which for an `unsafe` tool would just halt again on
    the same unresolved ambiguity.
    """

    idempotency_key: str
    tool_name: str
    args_canonical: dict[str, Any]
    intent_epoch: int
    resolution: str | None
    attempts: int


JournalState = Completed | NeverAttempted | Uncertain


async def lookup(conn: asyncpg.Connection[Any], idempotency_key: str) -> JournalState:
    """The three-state read (data-model.md §3's table, restated as code):

    | Row state                          | Returned            |
    |-------------------------------------|----------------------|
    | no row                              | `NeverAttempted()`   |
    | row, `result IS NOT NULL`           | `Completed(...)`     |
    | row, `result IS NULL`               | `Uncertain(...)`     |
    """
    row = await conn.fetchrow(_LOOKUP_SQL, idempotency_key)
    if row is None:
        return NeverAttempted()
    if row["result"] is not None:
        return Completed(
            result=json.loads(row["result"]),
            result_at=row["result_at"],
            result_epoch=row["result_epoch"],
            resolution=row["resolution"],
        )
    return Uncertain(
        idempotency_key=idempotency_key,
        tool_name=row["tool_name"],
        args_canonical=json.loads(row["args_canonical"]),
        intent_epoch=row["intent_epoch"],
        resolution=row["resolution"],
        attempts=row["attempts"],
    )
