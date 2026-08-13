"""The three answers a `reconcile_fn` may give (contracts/tool-contract.md).

Lives in `core/` rather than `runtime/` even though only `runtime/tools/`
authors implementations of `ReconcileFn`, because `core.journal.policies`
(the `reconcilable` policy) must be able to name these types without
`core/` depending on `runtime/` — the constitution's architecture boundary
runs the other direction.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Executed:
    """The effect occurred. `result` is recorded exactly as if the tool had
    returned it directly.
    """

    result: Any


@dataclass(frozen=True, slots=True)
class NotExecuted:
    """The effect did not occur. Safe to re-execute now."""


@dataclass(frozen=True, slots=True)
class Unknown:
    """The reconciler cannot determine the answer.

    **Escalates to `needs_review`** rather than defaulting to either branch
    — a reconciler that guesses is worse than no reconciler, because it
    converts an honest halt into a silent double execution
    (contracts/tool-contract.md).
    """


ReconcileResult = Executed | NotExecuted | Unknown

ReconcileFn = Callable[[dict[str, Any], str], Awaitable[ReconcileResult]]
