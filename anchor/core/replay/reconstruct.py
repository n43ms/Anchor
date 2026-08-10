"""`core.replay.reconstruct` — the pure fold (plan.md P2.1, T116).

No I/O. This is what makes `reconstruct` unit-testable against fixtures
without a database, which is what makes the invariant tests (replay
determinism, canonical-hash equality) meaningful rather than an artifact of
whatever happened to be in a live database at test time.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from anchor.core.events.models import RunEvent
from anchor.core.replay.context import RunContext
from anchor.core.replay.handlers import handler_for


def reconstruct(events: list[RunEvent]) -> RunContext:
    """Fold `events`, ordered by `seq`, into a `RunContext`.

    Assumes `events` is already ordered by `seq` ascending — the caller
    (the worker, reading `run_events` for one `run_id`) is responsible for
    that ordering; this function does not re-sort, so an out-of-order input
    produces an out-of-order (wrong) fold rather than silently correcting
    itself.
    """
    context = RunContext()
    for event in events:
        handler_for(event.type)(context, event)

    context.journal_entries_loaded = len(context.results_by_key)
    context.nondet_values_loaded = sum(
        len(values) for values in context.nondet_by_step_kind.values()
    )
    return context


def canonical_state(context: RunContext) -> dict[str, Any]:
    """A JSON-native, deterministically-ordered projection of `context`,
    used only to compute a canonical hash for replay-determinism
    comparison (T105). Deliberately excludes fold-internal bookkeeping
    (`pending_intents`) that has no bearing on the state an agent observes.
    """
    return {
        "last_completed_step_index": context.last_completed_step_index,
        "messages": context.messages,
        "results_by_key": {
            key: {
                "step_index": completion.step_index,
                "tool_name": completion.tool_name,
                "args": completion.args,
                "result": completion.result,
                "epoch": completion.epoch,
            }
            for key, completion in sorted(context.results_by_key.items())
        },
        "model_calls_by_step": {
            str(step_index): {
                "response": completion.response,
                "model": completion.model,
                "stubbed": completion.stubbed,
            }
            for step_index, completion in sorted(context.model_calls_by_step.items())
        },
        "nondet_by_step_kind": {
            f"{step_index}:{kind}": values
            for (step_index, kind), values in sorted(context.nondet_by_step_kind.items())
        },
        "attempts_by_step": {
            str(step_index): count for step_index, count in sorted(context.attempts_by_step.items())
        },
    }


def canonical_state_hash(context: RunContext) -> str:
    """`sha256` over `canonical_state`'s canonical JSON encoding (T105).

    A field-by-field comparison silently omits the field someone forgot to
    add to the assertion; hashing the whole canonical projection cannot.
    """
    encoded = json.dumps(canonical_state(context), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
