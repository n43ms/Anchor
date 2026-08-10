"""`StepContext` (plan.md P1.5, extended by P2.2/P2.4 — T089-T094, T120-T127).

Agent code reaches the outside world **only** through this object
(constitution Principle III; agent-contract.md).

Two journaling regimes meet here:

- `ctx.call_tool` / `ctx.call_model` append events directly, as phase 1
  established. Phase 5 adds the two-phase *journal table* and per-tool
  uncertainty policies on top of the event log this module already writes
  — until then, a crash between a tool's execution and its `TOOL_RESULT`
  being recorded can still double-execute (plan.md P1.5, P2.5's stated
  interim limitation).
- `ctx.now()` / `ctx.random()` / `ctx.new_id()` buffer into one
  `NONDET_RECORDED` per step, flushed atomically with that step's
  `TOOL_INTENT` (or, when the step has no tool call, its `STEP_COMPLETED`)
  — never eagerly per call (research.md D-47). On replay of a step that
  already has recorded values, they are returned in original call order by
  `call_ordinal` instead of being regenerated (agent-contract.md).
"""

from __future__ import annotations

import hashlib
import json
import random as _random
import time
import uuid as _uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar

import asyncpg

from anchor.core.determinism.buffer import NondetBuffer
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.replay.context import RunContext

_T = TypeVar("_T")


class ModelAdapter(Protocol):
    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> Any: ...


def _as_float(value: Any) -> float:
    return float(value)


def _as_str(value: Any) -> str:
    return str(value)


def _phase1_idempotency_key(
    run_id: int, step_index: int, tool_name: str, args: dict[str, Any]
) -> str:
    """A placeholder key derivation for phase 1 and 2 only.

    The canonical, collision-proof derivation
    (`sha256(canonical_json([run_id, step_index, action_name, args]))`) is
    core/journal's job, built in phase 5 (D-12, D-41). This version exists
    only so `TOOL_INTENT`'s required `idempotency_key` field is populated —
    there is no journal table yet to look it up against, so nothing reads
    this value back for deduplication before phase 5.
    """
    canonical = json.dumps(
        [run_id, step_index, tool_name, args], sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    run_context: RunContext = field(default_factory=RunContext)

    conn: asyncpg.Connection[Any] | None = None
    model_adapter: ModelAdapter | None = None
    tool_registry: dict[str, Any] = field(default_factory=dict)

    nondet_buffer: NondetBuffer = field(init=False)

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
        """Execute a tool, appending `TOOL_INTENT` — committed atomically
        with any buffered non-determinism, and before invocation — then
        `TOOL_RESULT` (FR-039, FR-040).

        Crash behaviour: a crash before the `TOOL_INTENT` transaction
        commits leaves neither the intent nor the buffered non-determinism
        — they are one statement group, so there is no interleaving in
        which an effect's inputs are unrecorded (D-47, T113). A crash
        between the committed intent and `TOOL_RESULT` is the uncertainty
        window; phase 5 resolves it per the tool's declared policy; until
        then the interim behaviour is a possible duplicate execution on
        retry, stated rather than assumed (P2.5).
        """
        assert self.conn is not None
        tool = self.tool_registry[name]
        idempotency_key = _phase1_idempotency_key(self.run_id, self.step_index, name, args)
        args_hash = hashlib.sha256(
            json.dumps(args, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        async with self.conn.transaction():
            await self.flush_pending_nondet()
            await append(
                self.conn,
                run_id=self.run_id,
                type=EventType.TOOL_INTENT,
                payload={
                    "step_index": self.step_index,
                    "tool_name": name,
                    "args_canonical": args,
                    "idempotency_key": idempotency_key,
                    "args_hash": args_hash,
                    "safety": tool.safety,
                },
                epoch=self.epoch,
                worker_id=self.worker_id,
                step_index=self.step_index,
                max_payload_bytes=self.max_payload_bytes,
            )

        start = time.monotonic()
        result = await tool.fn(args)
        latency_ms = (time.monotonic() - start) * 1000

        await append(
            self.conn,
            run_id=self.run_id,
            type=EventType.TOOL_RESULT,
            payload={
                "step_index": self.step_index,
                "tool_name": name,
                "idempotency_key": idempotency_key,
                "result": result,
                "latency_ms": latency_ms,
            },
            epoch=self.epoch,
            worker_id=self.worker_id,
            step_index=self.step_index,
            max_payload_bytes=self.max_payload_bytes,
        )
        return result

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
        start = time.monotonic()
        response = await self.model_adapter.complete(messages, model)
        latency_ms = (time.monotonic() - start) * 1000
        prompt_hash = hashlib.sha256(
            json.dumps(messages, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

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
