"""Per-event-type fold handlers (plan.md P2.1, T117).

One explicit handler per member of `EventType` — seventeen, matching the
`CHECK` constraint exactly — so a new event type added to the enum without a
handler here fails the completeness test loudly rather than being silently
absorbed by a default branch (`test_every_event_type_has_a_handler`).

Each handler has the signature `(context: RunContext, event: RunEvent) ->
None` and mutates `context` in place. `reconstruct()` is the only caller.
"""

from __future__ import annotations

from collections.abc import Callable

from anchor.core.events.models import RunEvent
from anchor.core.events.types import EventType
from anchor.core.replay.context import ModelCompletion, RunContext, ToolCompletion

Handler = Callable[[RunContext, RunEvent], None]


def _handle_run_submitted(context: RunContext, event: RunEvent) -> None:
    """No contribution to reconstructed step state — submission precedes
    any step and carries nothing a step reads back.
    """


def _handle_run_claimed(context: RunContext, event: RunEvent) -> None:
    """No contribution: ownership is the worker loop's concern, not the
    agent's. `ctx` never exposes who owns the run.
    """


def _handle_replay_completed(context: RunContext, event: RunEvent) -> None:
    """No contribution: this event is itself a record of a *previous*
    fold's outcome, not an input to this one. Re-folding a log that
    contains a prior `REPLAY_COMPLETED` must not double-count anything.
    """


def _handle_step_started(context: RunContext, event: RunEvent) -> None:
    """No contribution: `last_completed_step_index` only advances on
    `STEP_COMPLETED`, so a log that ends between `STEP_STARTED` and
    `STEP_COMPLETED` naturally excludes the partial step (T106) without
    this handler doing anything.
    """
    step_index = event.payload["step_index"]
    context.steps_with_journal_activity.add(step_index)


def _handle_llm_called(context: RunContext, event: RunEvent) -> None:
    step_index = event.payload["step_index"]
    context.model_calls_by_step[step_index] = ModelCompletion(
        step_index=step_index,
        response=event.payload["response"],
        model=event.payload["model"],
        stubbed=event.payload["stubbed"],
    )
    context.steps_with_journal_activity.add(step_index)


def _handle_tool_intent(context: RunContext, event: RunEvent) -> None:
    """Holds the intent's canonical arguments, keyed by idempotency_key,
    until the matching `TOOL_RESULT` arrives — that is what lets the
    completion recorded there carry real arguments for `has_result(tool,
    args)` and `completed_tool_args`. No `ToolCompletion` is recorded here:
    an intent with no matching result is the uncertainty window (Principle
    IV), left unresolved by phase 2's fold.
    """
    idempotency_key = event.payload["idempotency_key"]
    context.pending_intents[idempotency_key] = event.payload["args_canonical"]
    context.steps_with_journal_activity.add(event.payload["step_index"])


def _handle_tool_result(context: RunContext, event: RunEvent) -> None:
    step_index = event.payload["step_index"]
    idempotency_key = event.payload["idempotency_key"]
    tool_name = event.payload["tool_name"]
    args = context.pending_intents.pop(idempotency_key, {})
    completion = ToolCompletion(
        idempotency_key=idempotency_key,
        step_index=step_index,
        tool_name=tool_name,
        args=args,
        result=event.payload["result"],
        epoch=event.epoch,
    )
    context.results_by_key[idempotency_key] = completion
    context.results_by_tool.setdefault(tool_name, []).append(completion)
    context.steps_with_journal_activity.add(step_index)


def _handle_nondet_recorded(context: RunContext, event: RunEvent) -> None:
    step_index = event.payload["step_index"]
    context.steps_with_journal_activity.add(step_index)
    for entry in event.payload["entries"]:
        key = (step_index, entry["kind"])
        context.nondet_by_step_kind.setdefault(key, []).append(entry["value"])


def _handle_step_completed(context: RunContext, event: RunEvent) -> None:
    step_index = event.payload["step_index"]
    if step_index > context.last_completed_step_index:
        context.last_completed_step_index = step_index
    context.steps_replayed += 1


def _handle_step_skipped_on_replay(context: RunContext, event: RunEvent) -> None:
    """No contribution beyond marking the step as having journal activity:
    this event records that a *previous* worker already skipped
    re-executing a tool call, which is itself informational — it does not
    change what `has_result` / `result_of` return, since the underlying
    `TOOL_RESULT` this event refers to was already folded in independently.
    """
    context.steps_with_journal_activity.add(event.payload["step_index"])


def _handle_step_failed(context: RunContext, event: RunEvent) -> None:
    step_index = event.payload["step_index"]
    context.attempts_by_step[step_index] = context.attempts_by_step.get(step_index, 0) + 1
    context.steps_with_journal_activity.add(step_index)


def _handle_lease_renewed(context: RunContext, event: RunEvent) -> None:
    """Contributes **nothing** to reconstructed state, by design (T119):
    lease renewal is a liveness signal, not a step outcome, and licenses
    the conditional emission of D-48 — if renewal affected replay, skipping
    its emission on most renewals would make replay depend on which
    renewals happened to be logged.
    """


def _handle_worker_fenced(context: RunContext, event: RunEvent) -> None:
    """No contribution: a fencing record describes what happened to a
    *previous* worker, not a step outcome an agent reads back.
    """


def _handle_run_completed(context: RunContext, event: RunEvent) -> None:
    """No contribution: terminal. A run whose log already reached
    `RUN_COMPLETED` is never re-executed (the worker loop must not claim a
    terminal run in the first place)."""


def _handle_run_failed(context: RunContext, event: RunEvent) -> None:
    """No contribution: terminal, per `_handle_run_completed`."""


def _handle_run_cancelled(context: RunContext, event: RunEvent) -> None:
    """No contribution: terminal, per `_handle_run_completed`."""


def _handle_run_needs_review(context: RunContext, event: RunEvent) -> None:
    """No contribution: `needs_review` halts execution (phase 5); nothing
    downstream reads this from `ctx`.
    """


_HANDLERS: dict[EventType, Handler] = {
    EventType.RUN_SUBMITTED: _handle_run_submitted,
    EventType.RUN_CLAIMED: _handle_run_claimed,
    EventType.REPLAY_COMPLETED: _handle_replay_completed,
    EventType.STEP_STARTED: _handle_step_started,
    EventType.LLM_CALLED: _handle_llm_called,
    EventType.TOOL_INTENT: _handle_tool_intent,
    EventType.TOOL_RESULT: _handle_tool_result,
    EventType.NONDET_RECORDED: _handle_nondet_recorded,
    EventType.STEP_COMPLETED: _handle_step_completed,
    EventType.STEP_SKIPPED_ON_REPLAY: _handle_step_skipped_on_replay,
    EventType.STEP_FAILED: _handle_step_failed,
    EventType.LEASE_RENEWED: _handle_lease_renewed,
    EventType.WORKER_FENCED: _handle_worker_fenced,
    EventType.RUN_COMPLETED: _handle_run_completed,
    EventType.RUN_FAILED: _handle_run_failed,
    EventType.RUN_CANCELLED: _handle_run_cancelled,
    EventType.RUN_NEEDS_REVIEW: _handle_run_needs_review,
}


def handler_for(event_type: EventType) -> Handler:
    """Raises `KeyError` naming the missing type rather than silently
    no-opping, so a seventeen-to-eighteen drift in `EventType` is caught
    here rather than at replay time on a real run.
    """
    return _HANDLERS[event_type]


ALL_EVENT_TYPES_HAVE_HANDLERS = frozenset(_HANDLERS) == frozenset(EventType)
