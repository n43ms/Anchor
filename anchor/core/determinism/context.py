"""`StepContext` (plan.md P1.5, extended by P2.2/P2.4/P5.4 — T089-T094,
T120-T127, T259-T266).

Agent code reaches the outside world **only** through this object
(constitution Principle III; agent-contract.md).

Two journaling regimes meet here:

- `ctx.call_tool` routes every call through `core.journal.two_phase`'s
  three-state lookup (phase 5): a completed key replays via
  `STEP_SKIPPED_ON_REPLAY`, a fresh key gets the two-phase
  intent-then-invoke-then-result sequence, and an uncertain key is resolved
  by the tool's declared policy. `ctx.call_model` still appends
  `LLM_CALLED` directly — a model call has no side effect and therefore no
  uncertainty window to resolve.
- `ctx.now()` / `ctx.random()` / `ctx.new_id()` buffer into one
  `NONDET_RECORDED` per step, flushed atomically with that step's
  `TOOL_INTENT` (or, when the step has no tool call, its `STEP_COMPLETED`)
  — never eagerly per call (research.md D-47). On replay of a step that
  already has recorded values, they are returned in original call order by
  `call_ordinal` instead of being regenerated (agent-contract.md).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random as _random
import time
import uuid as _uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar

import asyncpg

from anchor.core.determinism.buffer import NondetBuffer
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.journal.tool_protocol import RegisteredToolLike
from anchor.core.journal.two_phase import execute_tool_call
from anchor.core.replay.context import ModelCompletion, RunContext

_T = TypeVar("_T")


class StepTimeoutError(Exception):
    """Raised when a step's external call (a tool invocation or a model
    call) runs longer than `step_timeout_ms` (plan.md P6.5, T328, FR-055).

    **Deliberately not retried by `worker.retry.policy`.** A step that is
    merely slow gets no special treatment elsewhere in this system — but a
    step that has been running for longer than the configured timeout is
    treated as a sign that *this worker* may be stalled, not as an ordinary
    failure to back off and re-attempt from the same process. The caller
    (`anchor.worker.loop.run_claimed`) lets this propagate out of the
    execution task uncaught; `asyncio.TaskGroup`'s structured concurrency
    then cancels the sibling renewer task exactly as it does for
    `LeaseFencedError`, so the lease simply stops being renewed and lapses
    on its own schedule (FR-013) — the run is reclaimed by whichever
    worker's poll next observes the expired lease, which may be this same
    worker once it has recovered. Nothing is written to the run's log by
    the timing-out worker itself: it does not know, and must not guess,
    whether the external call it abandoned actually completed.
    """


class ModelAdapter(Protocol):
    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> Any: ...


def _as_float(value: Any) -> float:
    return float(value)


def _as_str(value: Any) -> str:
    return str(value)


@dataclass
class StepContext:
    """Reconstructed run state, and the only surface agent code may reach
    the outside world through (agent-contract.md).
    """

    run_id: int
    epoch: int
    worker_id: str
    step_index: int
    input: dict[str, Any]
    messages: list[dict[str, Any]] = field(default_factory=list)
    attempt: int = 1
    max_payload_bytes: int = 1_000_000
    # No numeric default: this is a `runtime_config` key (FR-059), and a
    # hardcoded fallback here would be a second place that value lives,
    # which `tests/boundary/test_no_hardcoded_constants.py` forbids by
    # construction. `None` is the sentinel for "not yet supplied by the
    # caller", asserted away at both use sites below.
    step_timeout_ms: int | None = None
    run_context: RunContext = field(default_factory=RunContext)

    conn: asyncpg.Connection[Any] | None = None
    model_adapter: ModelAdapter | None = None
    tool_registry: Mapping[str, RegisteredToolLike] = field(default_factory=dict)

    nondet_buffer: NondetBuffer = field(init=False)
    _tool_called_this_step: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.nondet_buffer = NondetBuffer(step_index=self.step_index)

    # --- Read-only accessors over journaled history (agent-contract.md) ---

    @property
    def is_replaying(self) -> bool:
        """True while this step is being re-attempted into state already
        journaled before. **Informational only** — branching on it makes
        replay non-deterministic, and the phase-9 validator flags it
        (agent-contract.md).
        """
        return self.run_context.is_replaying(self.step_index)

    def has_result(self, tool_name: str, args: dict[str, Any] | None = None) -> bool:
        return self.run_context.has_result(tool_name, args)

    def result_of(self, tool_name: str, args: dict[str, Any] | None = None) -> Any:
        return self.run_context.result_of(tool_name, args)

    def model_response_at(self, step_index: int) -> Any:
        recorded = self.run_context.model_calls_by_step.get(step_index)
        if recorded is not None:
            return {"text": recorded.response, "model": recorded.model, "stubbed": recorded.stubbed}
        return None

    def completed_tool_args(self, tool_name: str) -> list[dict[str, Any]]:
        return self.run_context.completed_tool_args(tool_name)

    # --- Journaled non-determinism (P2.2) ---

    def _nondet_call(
        self,
        kind: str,
        generate: Callable[[], _T],
        serialize: Callable[[_T], Any],
        deserialize: Callable[[Any], _T],
    ) -> _T:
        """Shared machinery for `now()` / `random()` / `new_id()`: check
        whether a value already exists at the next ordinal for `kind` (this
        step was attempted before and got at least this far), and return it
        instead of generating a new one. No external effect and no I/O —
        buffered values are flushed by the caller (`call_tool` or the
        worker loop), never written here, so a crash before that flush is
        safely re-derivable on the next attempt: nothing in the world
        observed the discarded value (agent-contract.md).
        """
        ordinal = self.nondet_buffer.next_ordinal(kind)
        recorded = self.run_context.nondet_by_step_kind.get((self.step_index, kind))
        if recorded is not None and ordinal < len(recorded):
            self.nondet_buffer.mark_read(kind)
            return deserialize(recorded[ordinal])
        value = generate()
        self.nondet_buffer.record(kind, serialize(value))
        return value

    def now(self) -> datetime:
        """Journals as `NONDET_RECORDED` kind `time`; returns the recorded
        timestamp on replay (agent-contract.md).
        """
        # The explicit local annotation, not just the function's return
        # type, is load-bearing: mypy only uses a call's *assignment*
        # target as inference context for a multi-typevar generic like
        # `_nondet_call`, not a bare `return` expression, and silently
        # widens to `Any` without it.
        result: datetime = self._nondet_call(
            "time",
            generate=lambda: datetime.now(UTC),
            serialize=lambda v: v.isoformat(),
            deserialize=datetime.fromisoformat,
        )
        return result

    def random(self) -> float:
        """Journals as `NONDET_RECORDED` kind `random`; returns the recorded
        value on replay (agent-contract.md).
        """
        result: float = self._nondet_call(
            "random", generate=_random.random, serialize=lambda v: v, deserialize=_as_float
        )
        return result

    def new_id(self) -> str:
        """Journals as `NONDET_RECORDED` kind `id`; returns the recorded
        identifier on replay. Named separately from `random()` deliberately
        — a generated identifier differing across replay is the specific
        failure that defeats deduplication, so it is individually visible
        in the log and individually greppable in agent code
        (agent-contract.md, FR-033).
        """
        result: str = self._nondet_call(
            "id",
            generate=lambda: str(_uuid.uuid4()),
            serialize=lambda v: v,
            deserialize=_as_str,
        )
        return result

    async def flush_pending_nondet(self) -> None:
        """Append the buffered non-determinism as one `NONDET_RECORDED`, or
        do nothing if the buffer is empty. Callers (`call_tool`, and the
        worker loop for steps with no tool call) are responsible for
        wrapping this together with the event it must be atomic with, in
        one transaction (D-47).
        """
        assert self.conn is not None
        entries = self.nondet_buffer.drain()
        if not entries:
            return
        await append(
            self.conn,
            run_id=self.run_id,
            type=EventType.NONDET_RECORDED,
            payload={"step_index": self.step_index, "entries": entries},
            epoch=self.epoch,
            worker_id=self.worker_id,
            step_index=self.step_index,
            max_payload_bytes=self.max_payload_bytes,
        )

    # --- The two side-effecting calls (P1.5) ---

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Execute a tool through the three-state journal lookup
        (`core.journal.two_phase`, phase 5): a key already carrying a
        result replays via `STEP_SKIPPED_ON_REPLAY`; a fresh key gets the
        two-phase intent-then-invoke-then-result sequence, with the intent
        committed atomically with any buffered non-determinism and before
        invocation (FR-039, FR-040); an uncertain key — a crash landed
        between a committed intent and its result — is resolved by the
        tool's declared policy, never guessed (`I8`).

        **One side effect per step** (D-26): a second call in the same
        step raises, because that constraint is what makes the idempotency
        key unique without a within-step counter.

        Crash behaviour: a crash before the intent transaction commits
        leaves neither the intent nor the buffered non-determinism — one
        statement group, so there is no interleaving in which an effect's
        inputs are unrecorded (D-47, T113). A crash between the committed
        intent and the result phase is the uncertainty window; the next
        attempt at this exact call resolves it per the tool's declared
        policy rather than assuming success or failure.
        """
        assert self.conn is not None
        if self._tool_called_this_step:
            raise RuntimeError(
                f"step {self.step_index} attempted a second side-effecting tool "
                f"call ({name!r}) — exactly one side effect per step is what makes "
                "the idempotency key unique without a within-step counter (D-26)"
            )
        self._tool_called_this_step = True
        tool = self.tool_registry[name]
        effective_timeout = getattr(tool, "timeout_ms", None) or self.step_timeout_ms or 600_000

        try:
            async with asyncio.timeout(effective_timeout / 1000):
                result = await execute_tool_call(
                    self.conn,
                    run_id=self.run_id,
                    epoch=self.epoch,
                    worker_id=self.worker_id,
                    step_index=self.step_index,
                    tool=tool,
                    args=args,
                    flush_pending_nondet=self.flush_pending_nondet,
                    max_payload_bytes=self.max_payload_bytes,
                )
                from anchor.core.journal.keys import derive_key
                from anchor.core.replay.context import ToolCompletion

                idempotency_key = derive_key(self.run_id, self.step_index, name, args)
                completion = ToolCompletion(
                    idempotency_key=idempotency_key,
                    step_index=self.step_index,
                    tool_name=name,
                    args=args,
                    result=result,
                    epoch=self.epoch,
                )
                self.run_context.results_by_key[idempotency_key] = completion
                self.run_context.results_by_tool.setdefault(name, []).append(completion)
                return result
        except TimeoutError as exc:
            raise StepTimeoutError(
                f"step {self.step_index}: tool {name!r} exceeded step_timeout_ms "
                f"({effective_timeout})"
            ) from exc

    async def call_model(self, messages: list[dict[str, Any]], model: str | None = None) -> Any:
        """Call the configured `ModelAdapter` (the stub by default on every
        path, D-55) and append `LLM_CALLED`.

        Crash behaviour: a crash after the provider call but before this
        append costs the call again on the next attempt — money, not
        correctness (agent-contract.md). Buffered non-determinism is
        *not* flushed here; a model call is not a side effect, so any
        nondet values feeding into it are flushed with this step's
        `STEP_COMPLETED` instead (the worker loop's responsibility).

        If this exact step already has a journaled `LLM_CALLED` — a step
        that reached the model call but crashed before `STEP_COMPLETED`,
        now being retried — the recorded completion is returned directly
        and the provider is **not called again** (agent-contract.md,
        T114). This does not need phase 5's journal: unlike a tool call,
        a model call has no uncertainty window to resolve, so a plain
        per-step lookup in the already-reconstructed `RunContext` is
        sufficient.
        """
        recorded = self.run_context.model_calls_by_step.get(self.step_index)
        if recorded is not None:
            return recorded.response

        assert self.conn is not None
        assert self.model_adapter is not None
        effective_timeout = self.step_timeout_ms or 600_000
        start = time.monotonic()
        try:
            async with asyncio.timeout(effective_timeout / 1000):
                response = await self.model_adapter.complete(messages, model)
        except TimeoutError as exc:
            raise StepTimeoutError(
                f"step {self.step_index}: model call exceeded step_timeout_ms ({effective_timeout})"
            ) from exc
        latency_ms = (time.monotonic() - start) * 1000
        prompt_hash = hashlib.sha256(
            json.dumps(messages, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        if self.run_context is not None:
            self.run_context.model_calls_by_step[self.step_index] = ModelCompletion(
                step_index=self.step_index,
                response=response.text,
                model=model or response.model,
                stubbed=response.stubbed,
            )

        await append(
            self.conn,
            run_id=self.run_id,
            type=EventType.LLM_CALLED,
            payload={
                "step_index": self.step_index,
                "prompt_hash": prompt_hash,
                "response": response.text,
                "model": model or response.model,
                "latency_ms": latency_ms,
                "stubbed": response.stubbed,
            },
            epoch=self.epoch,
            worker_id=self.worker_id,
            step_index=self.step_index,
            max_payload_bytes=self.max_payload_bytes,
        )
        return response.text
