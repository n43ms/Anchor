"""`RunContext` — the reconstructed-state container (plan.md P2.1, T115).

This is what `reconstruct()` (a pure fold over `run_events`, no I/O) builds,
and what `StepContext` reads from on every claim, including the first. It
holds exactly what agent-contract.md's read-only accessors need and nothing
else — it is not a general-purpose event store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolCompletion:
    """One journaled `TOOL_RESULT`, matched to its `TOOL_INTENT` by
    `idempotency_key` (data-model.md `tool_journal`'s phase-2 stand-in — the
    table itself is phase 5; this is the in-memory shape the fold produces).
    """

    idempotency_key: str
    step_index: int
    tool_name: str
    args: dict[str, Any]
    result: Any
    epoch: int


@dataclass(frozen=True, slots=True)
class ModelCompletion:
    """One journaled `LLM_CALLED`, keyed by the step that produced it — an
    agent returns exactly one action per step (agent-contract.md rule 3), so
    at most one model call exists per `step_index`.
    """

    step_index: int
    response: Any
    model: str
    stubbed: bool


@dataclass
class RunContext:
    """Reconstructed run state (agent-contract.md's `StepContext` surface is
    a thin, per-step view over this).

    Not frozen: `reconstruct()` builds one of these by mutating a single
    instance across an ordered fold, then hands it to the worker loop, which
    owns it exclusively for the run's lifetime — no shared mutable state
    between concurrent runs (constitution, Code Standards).
    """

    last_completed_step_index: int = -1
    messages: list[dict[str, Any]] = field(default_factory=list)

    # Keyed by idempotency_key: the exact-match lookup a future retry of the
    # *same* step would need once phase 5's journal exists. Kept even though
    # nothing dedupes on it yet, because the fold that produces it is the
    # fold this phase must get right.
    results_by_key: dict[str, ToolCompletion] = field(default_factory=dict)

    # Keyed by tool name: what `ctx.has_result` / `ctx.result_of` /
    # `ctx.completed_tool_args` actually query. An agent asks "have I
    # already emailed this address" without knowing which step index
    # produced that completion (agent-contract.md's resumable-loop
    # pattern), so the tool-name index — not the idempotency-key index — is
    # the one the accessors read.
    results_by_tool: dict[str, list[ToolCompletion]] = field(default_factory=dict)

    # One model completion per step, since a step returns exactly one action.
    model_calls_by_step: dict[int, ModelCompletion] = field(default_factory=dict)

    # Non-deterministic values in original call order, keyed by
    # (step_index, kind) -> ordered values. Read back by `call_ordinal`
    # (agent-contract.md: "replayed in call order, by call_ordinal").
    nondet_by_step_kind: dict[tuple[int, str], list[Any]] = field(default_factory=dict)

    # Fold-internal only: `TOOL_INTENT.args_canonical` keyed by
    # idempotency_key, held until the matching `TOOL_RESULT` arrives so the
    # completion recorded in `results_by_tool` carries its real arguments.
    # Not part of the public accessor surface.
    pending_intents: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Every step_index that already has *some* journaled activity — a
    # NONDET_RECORDED, a TOOL_INTENT, or an LLM_CALLED — even if that step
    # never reached STEP_COMPLETED. This is what makes `ctx.is_replaying`
    # correct for a step that crashed mid-attempt: the step is being
    # retried into state that was partially recorded before, not executed
    # for the first time (agent-contract.md "Crash behaviour of ctx.now()").
    steps_with_journal_activity: set[int] = field(default_factory=set)

    # Derived from STEP_FAILED counts, never from `runs.attempts` (D-43): an
    # in-memory counter resets on handoff, and a poison step would then
    # retry forever under a worker that just took over.
    attempts_by_step: dict[int, int] = field(default_factory=dict)

    # REPLAY_COMPLETED telemetry, accumulated during the fold so the worker
    # can append the event verbatim from this object (FR-029).
    steps_replayed: int = 0
    journal_entries_loaded: int = 0
    nondet_values_loaded: int = 0

    def has_result(self, tool_name: str, args: dict[str, Any] | None = None) -> bool:
        """Whether a completed result exists for `tool_name`, optionally for
        those exact arguments (agent-contract.md).
        """
        completions = self.results_by_tool.get(tool_name, [])
        if args is None:
            return len(completions) > 0
        return any(c.args == args for c in completions)

    def result_of(self, tool_name: str, args: dict[str, Any] | None = None) -> Any:
        """The recorded result, or raises if absent (agent-contract.md)."""
        completions = self.results_by_tool.get(tool_name, [])
        if args is None:
            if not completions:
                raise KeyError(f"no completed result for tool {tool_name!r}")
            return completions[-1].result
        for completion in completions:
            if completion.args == args:
                return completion.result
        raise KeyError(f"no completed result for tool {tool_name!r} with args {args!r}")

    def completed_tool_args(self, tool_name: str) -> list[dict[str, Any]]:
        """Every argument set for which `tool_name` has a recorded result —
        the mechanism that makes a resumable loop expressible without a
        counter (agent-contract.md).
        """
        return [c.args for c in self.results_by_tool.get(tool_name, [])]

    def is_replaying(self, step_index: int) -> bool:
        """True while this step_index is being re-attempted into state that
        was already journaled before — informational only
        (agent-contract.md: branching on it makes replay non-deterministic).
        """
        return step_index in self.steps_with_journal_activity
