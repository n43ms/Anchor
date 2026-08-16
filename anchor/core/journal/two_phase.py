"""The two-phase journal, end to end (plan.md P5.4, T259-T266).

This is what `StepContext.call_tool` (phase 1's direct append sequence)
becomes in phase 5: every tool call now passes through the three-state
lookup before anything executes.

```
lookup(idempotency_key)
  Completed      -> emit STEP_SKIPPED_ON_REPLAY, return the recorded result
  NeverAttempted -> intent phase (commit) -> invoke -> result phase
  Uncertain      -> the tool's declared policy (core.journal.policies),
                     unless already operator-authorized to execute directly
```

**The intent is committed before invocation** (contracts/tool-contract.md).
That ordering is the whole mechanism: it means a crash can leave the system
*uncertain*, but never leaves it *unaware* that something might have
happened. The inverse ordering — execute, then record — would make an
unrecorded side effect possible, which the constitution forbids outright.

**Declaration conflicts gate new execution, never a replay of a completed
result** (T270, data-model.md §4). A tool fenced by a fleet-wide safety
disagreement cannot safely start a fresh attempt or resolve an uncertain
one — the ambiguity is in *which policy applies*, and neither path can
proceed without knowing that. A `Completed` lookup, however, needs no
policy at all: nothing new executes, so a conflict discovered after the
result was already recorded changes nothing about replaying it.
"""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

import asyncpg

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.journal.canonical import canonicalize
from anchor.core.journal.keys import derive_args_hash, derive_key
from anchor.core.journal.lookup import Completed, NeverAttempted, Uncertain, lookup
from anchor.core.journal.policies import NeedsReviewHalted, halt_needs_review, resolve_uncertain
from anchor.core.journal.tool_protocol import RegisteredToolLike

_CONFLICT_SQL = "SELECT conflict_at FROM tool_registry WHERE name = $1"


async def _is_conflicted(conn: asyncpg.Connection[Any], tool_name: str) -> bool:
    row = await conn.fetchrow(_CONFLICT_SQL, tool_name)
    return row is not None and row["conflict_at"] is not None


async def _emit_skip(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    step_index: int,
    idempotency_key: str,
    tool_name: str,
    original_result_at: str,
    original_epoch: int,
    max_payload_bytes: int,
) -> None:
    await append(
        conn,
        run_id=run_id,
        type=EventType.STEP_SKIPPED_ON_REPLAY,
        payload={
            "step_index": step_index,
            "idempotency_key": idempotency_key,
            "tool_name": tool_name,
            "original_result_at": original_result_at,
            "original_epoch": original_epoch,
        },
        epoch=epoch,
        worker_id=worker_id,
        step_index=step_index,
        max_payload_bytes=max_payload_bytes,
    )


async def _intent_phase(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    step_index: int,
    tool_name: str,
    idempotency_key: str,
    args_canonical: dict[str, Any],
    args_hash: str,
    safety: str,
    flush_pending_nondet: Callable[[], Awaitable[None]],
    max_payload_bytes: int,
) -> None:
    """Insert the `tool_journal` row and append `TOOL_INTENT`, with the
    step's buffered non-determinism, all in one transaction (D-47): there
    is no interleaving in which this effect's inputs — including any
    `ctx.new_id()` value feeding `args_canonical` — are unrecorded.
    """
    async with conn.transaction():
        await conn.execute("SELECT 1 FROM runs WHERE id = $1 FOR UPDATE", run_id)
        await flush_pending_nondet()
        await conn.execute(
            """
            INSERT INTO tool_journal
                (idempotency_key, run_id, step_index, tool_name,
                 args_canonical, args_hash, intent_epoch, attempts)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, 1)
            """,
            idempotency_key,
            run_id,
            step_index,
            tool_name,
            json.dumps(args_canonical),
            args_hash,
            epoch,
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.TOOL_INTENT,
            payload={
                "step_index": step_index,
                "tool_name": tool_name,
                "args_canonical": args_canonical,
                "idempotency_key": idempotency_key,
                "args_hash": args_hash,
                "safety": safety,
            },
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            max_payload_bytes=max_payload_bytes,
        )


async def _result_phase(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    step_index: int,
    tool_name: str,
    idempotency_key: str,
    result: Any,
    latency_ms: float,
    resolution: str | None,
    max_payload_bytes: int,
) -> None:
    async with conn.transaction():
        await conn.execute("SELECT 1 FROM runs WHERE id = $1 FOR UPDATE", run_id)
        await conn.execute(
            """
            UPDATE tool_journal
            SET result = $2::jsonb, result_at = now(), result_epoch = $3, resolution = $4
            WHERE idempotency_key = $1
            """,
            idempotency_key,
            json.dumps(result),
            epoch,
            resolution,
        )
        await append(
            conn,
            run_id=run_id,
            type=EventType.TOOL_RESULT,
            payload={
                "step_index": step_index,
                "tool_name": tool_name,
                "idempotency_key": idempotency_key,
                "result": result,
                "latency_ms": latency_ms,
                "resolution": resolution,
            },
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            max_payload_bytes=max_payload_bytes,
        )


async def _execute_and_record(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    step_index: int,
    tool: RegisteredToolLike,
    idempotency_key: str,
    args_canonical: dict[str, Any],
    resolution: str | None,
    max_payload_bytes: int,
) -> Any:
    start = time.monotonic()
    result = await tool.fn(
        args_canonical,
        idempotency_key=idempotency_key,
        conn=conn,
        run_id=run_id,
        step_index=step_index,
    )
    latency_ms = (time.monotonic() - start) * 1000
    await _result_phase(
        conn,
        run_id=run_id,
        epoch=epoch,
        worker_id=worker_id,
        step_index=step_index,
        tool_name=tool.name,
        idempotency_key=idempotency_key,
        result=result,
        latency_ms=latency_ms,
        resolution=resolution,
        max_payload_bytes=max_payload_bytes,
    )
    return result


async def execute_tool_call(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    step_index: int,
    tool: RegisteredToolLike,
    args: dict[str, Any],
    flush_pending_nondet: Callable[[], Awaitable[None]],
    max_payload_bytes: int,
) -> Any:
    """Execute `tool` with `args` through the three-state journal lookup.

    Crash behaviour, restated per window (contracts/tool-contract.md):
    before the intent transaction commits, neither the intent nor the
    buffered non-determinism landed — safely re-derivable, nothing executed.
    Between the committed intent and the result phase is the uncertainty
    window this module exists to resolve. After the result phase commits,
    the effect is durable and any further attempt at this exact call
    replays it via `STEP_SKIPPED_ON_REPLAY` rather than re-executing it.
    """
    idempotency_key = derive_key(run_id, step_index, tool.name, args)
    args_canonical = canonicalize(args)
    args_hash = derive_args_hash(args_canonical)

    state = await lookup(conn, idempotency_key)

    if isinstance(state, Completed):
        await _emit_skip(
            conn,
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            idempotency_key=idempotency_key,
            tool_name=tool.name,
            original_result_at=state.result_at.isoformat(),
            original_epoch=state.result_epoch,
            max_payload_bytes=max_payload_bytes,
        )
        return state.result

    if isinstance(state, NeverAttempted):
        if await _is_conflicted(conn, tool.name):
            await halt_needs_review(
                conn,
                run_id=run_id,
                epoch=epoch,
                worker_id=worker_id,
                step_index=step_index,
                idempotency_key=idempotency_key,
                tool_name=tool.name,
                reason=f"tool {tool.name!r} has a fleet-wide declaration conflict; "
                "the policy that would resolve a crash inside this call is ambiguous",
                max_payload_bytes=max_payload_bytes,
            )
            raise NeedsReviewHalted(run_id)

        await _intent_phase(
            conn,
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            tool_name=tool.name,
            idempotency_key=idempotency_key,
            args_canonical=args_canonical,
            args_hash=args_hash,
            safety=tool.safety,
            flush_pending_nondet=flush_pending_nondet,
            max_payload_bytes=max_payload_bytes,
        )
        return await _execute_and_record(
            conn,
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            tool=tool,
            idempotency_key=idempotency_key,
            args_canonical=args_canonical,
            resolution=None,
            max_payload_bytes=max_payload_bytes,
        )

    assert isinstance(state, Uncertain)

    if state.resolution == "operator_marked_not_executed":
        # An operator already reviewed this exact call and confirmed the
        # effect had not occurred (D-24) — authorized to execute directly,
        # bypassing the tool's own declared policy, which for an `unsafe`
        # tool would just halt again on the same ambiguity it already
        # resolved.
        return await _execute_and_record(
            conn,
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            tool=tool,
            idempotency_key=idempotency_key,
            args_canonical=state.args_canonical,
            resolution="operator_marked_not_executed",
            max_payload_bytes=max_payload_bytes,
        )

    if await _is_conflicted(conn, tool.name):
        await halt_needs_review(
            conn,
            run_id=run_id,
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            idempotency_key=idempotency_key,
            tool_name=tool.name,
            reason=f"tool {tool.name!r} has a fleet-wide declaration conflict; "
            "the uncertainty window cannot be resolved from an ambiguous declaration",
            max_payload_bytes=max_payload_bytes,
        )
        raise NeedsReviewHalted(run_id)

    return await resolve_uncertain(
        conn,
        run_id=run_id,
        epoch=epoch,
        worker_id=worker_id,
        step_index=step_index,
        state=state,
        tool=tool,
        max_payload_bytes=max_payload_bytes,
    )
