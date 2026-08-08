"""`StepContext` v1 (plan.md P1.5).

This version appends `TOOL_INTENT` / `TOOL_RESULT` / `LLM_CALLED` **as
events only** — there is no journal table and no three-state lookup yet
(those are phase 5, P5.3-P5.4). A crash after a tool executes but before
`TOOL_RESULT` is committed currently loses the record; that is the honest
interim state, not a bug, and phase 5 exists to close it (I1 does not hold
end to end until then — plan.md "An honest note about the interim
guarantee").

`ctx.now()` / `ctx.random()` / `ctx.new_id()` and their per-step batching
into one `NONDET_RECORDED` are phase 2 (P2.2). This module exposes only
what plan.md P1.5 requires: `input`, `step_index`, `messages`, `attempt`,
`call_tool`, `call_model`.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import asyncpg

from anchor.core.events.append import append
from anchor.core.events.types import EventType


class ModelAdapter(Protocol):
    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> Any: ...


def _phase1_idempotency_key(
    run_id: int, step_index: int, tool_name: str, args: dict[str, Any]
) -> str:
    """A placeholder key derivation for phase 1 only.

    The canonical, collision-proof derivation
    (`sha256(canonical_json([run_id, step_index, action_name, args]))`) is
    core/journal's job, built in phase 5 (D-12, D-41). This version exists
    only so `TOOL_INTENT`'s required `idempotency_key` field is populated —
    there is no journal table yet to look it up against, so nothing reads
    this value back for deduplication in phase 1.
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

    conn: asyncpg.Connection[Any] | None = None
    model_adapter: ModelAdapter | None = None
    tool_registry: dict[str, Any] = field(default_factory=dict)

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Execute a tool directly, appending `TOOL_INTENT` — committed
        before invocation — then `TOOL_RESULT` (FR-039, FR-040).

        This establishes the two-phase *ordering* now, even though phase 1
        cannot yet deduplicate on it: the ordering is what phase 5 makes
        load-bearing by adding the journal it is written against.
        """
        assert self.conn is not None
        tool = self.tool_registry[name]
        idempotency_key = _phase1_idempotency_key(self.run_id, self.step_index, name, args)
        args_hash = hashlib.sha256(
            json.dumps(args, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

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
        """
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
