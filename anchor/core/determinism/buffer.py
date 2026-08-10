"""The per-step non-determinism buffer (plan.md P2.2, T120).

`ctx.now()` / `ctx.random()` / `ctx.new_id()` accumulate here in call order,
one buffer per step attempt. The buffer is drained into a single
`NONDET_RECORDED` event committed in the same transaction as that step's
`TOOL_INTENT` (or, when the step has no tool call, as its `STEP_COMPLETED`)
— never written eagerly per call (research.md D-47, agent-contract.md
"Crash behaviour of each ctx call"): durability is required before anything
depending on the value leaves the process, and the only such thing is a
side effect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NondetBuffer:
    """Accumulates `(kind, value)` pairs for one step attempt, assigning
    each an ordinal **within its kind** — `ctx.now()` called twice in one
    step yields ordinals 0 and 1 under kind `time`, independent of any
    `ctx.random()` calls interleaved between them. This is what lets replay
    read the two `time` values back in the order they were originally
    produced (T107): filtering by kind first, then ordinal, is unambiguous
    regardless of call interleaving across kinds.
    """

    step_index: int
    _entries: list[tuple[str, Any, int]] = field(default_factory=list)
    _next_ordinal: dict[str, int] = field(default_factory=dict)

    def next_ordinal(self, kind: str) -> int:
        """The ordinal the next call of this kind would receive, without
        recording anything — used by `StepContext` to check whether a
        recorded value already exists at that ordinal before generating a
        new one.
        """
        return self._next_ordinal.get(kind, 0)

    def record(self, kind: str, value: Any) -> int:
        """Record `value` under `kind`, returning its ordinal."""
        ordinal = self._next_ordinal.get(kind, 0)
        self._next_ordinal[kind] = ordinal + 1
        self._entries.append((kind, value, ordinal))
        return ordinal

    def mark_read(self, kind: str) -> int:
        """Advance `kind`'s ordinal counter without recording an entry —
        used when a value already recorded in a prior attempt is returned
        instead of generated, so a later call of the same kind this
        attempt receives the *next* ordinal rather than repeating this one.
        """
        ordinal = self._next_ordinal.get(kind, 0)
        self._next_ordinal[kind] = ordinal + 1
        return ordinal

    def is_empty(self) -> bool:
        return not self._entries

    def drain(self) -> list[dict[str, Any]]:
        """Return the buffered entries as `NONDET_RECORDED` payload entries
        and clear the buffer. Idempotent to call when empty (returns `[]`).
        """
        entries = [
            {"kind": kind, "value": value, "call_ordinal": ordinal}
            for kind, value, ordinal in self._entries
        ]
        self._entries.clear()
        self._next_ordinal.clear()
        return entries
