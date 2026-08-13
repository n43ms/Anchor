"""The three uncertainty policies (plan.md P5.6, T274-T279; `I8`).

Entered only when `core.journal.lookup` returns `Uncertain` — a crash landed
between a committed `TOOL_INTENT` and its `TOOL_RESULT`. Each policy's job is
to resolve that ambiguity **without guessing**: `retry_safe` re-executes
because re-execution is provably safe; `reconcilable` asks an authoritative
source; `unsafe` admits it cannot know and halts. Which branch runs is read
from the tool's *declared* safety category — never inferred from the
tool's name, its arguments, or anything about the crash itself.
"""

from __future__ import annotations

import json
import time
from typing import Any

import asyncpg

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.journal.lookup import Uncertain
from anchor.core.journal.reconcile import Executed, NotExecuted, Unknown
from anchor.core.journal.tool_protocol import RegisteredToolLike

_UNSAFE_RESOLUTIONS = ("mark_executed", "mark_not_executed", "retry")


class NeedsReviewHalted(Exception):
    """Raised after a run has been transitioned to `needs_review` and its
    lease released, so the worker loop's step iteration stops immediately
    rather than proceeding to `RUN_COMPLETED` or the next step. Pure
    control flow — by the time this is raised, the halt is already
    committed; there is nothing left to undo.
    """

    def __init__(self, run_id: int) -> None:
        self.run_id = run_id
        super().__init__(f"run {run_id} halted for review")


async def halt_needs_review(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    step_index: int,
    idempotency_key: str,
    tool_name: str,
    reason: str,
    max_payload_bytes: int,
) -> None:
    """Set the run to `needs_review`, release its lease, and append
    `RUN_NEEDS_REVIEW` — atomically (FR-049). **Does not guess**: no
    branch of this module ever assumes the effect succeeded or failed on
    its behalf.

    Crash behaviour: a crash before this transaction commits leaves the
    run exactly as it was before the halt was attempted — still `running`,
    still holding its lease, so the renewer keeps it alive and the worker
    (or its successor, after a fencing handoff) re-enters this same
    decision on the next attempt. There is no partial halt: the event and
    the status/lease transition are one statement group.
    """
    async with conn.transaction():
        await append(
            conn,
            run_id=run_id,
            type=EventType.RUN_NEEDS_REVIEW,
            payload={
                "step_index": step_index,
                "idempotency_key": idempotency_key,
                "tool_name": tool_name,
                "reason": reason,
                "available_resolutions": list(_UNSAFE_RESOLUTIONS),
            },
            epoch=epoch,
            worker_id=worker_id,
            step_index=step_index,
            max_payload_bytes=max_payload_bytes,
        )
        await conn.execute(
            """
            UPDATE runs
            SET status = 'needs_review',
                owner_worker_id = NULL,
                lease_expires_at = NULL,
                finished_at = now()
            WHERE id = $1
            """,
            run_id,
        )


async def _record_result(
    conn: asyncpg.Connection[Any],
    *,
    idempotency_key: str,
    result: Any,
    result_epoch: int,
    resolution: str | None,
    increment_attempts: bool,
) -> None:
    """The result phase for a policy-resolved call: `NULL -> result`, an
    optional `attempts` increment, and setting `resolution` — exactly the
    transitions `tool_journal_result_once` permits (data-model.md §10).
    """
    await conn.execute(
        """
        UPDATE tool_journal
        SET result = $2::jsonb,
            result_at = now(),
            result_epoch = $3,
            resolution = $4,
            resolved_at = now(),
            attempts = attempts + $5
        WHERE idempotency_key = $1
        """,
        idempotency_key,
        json.dumps(result),
        result_epoch,
        resolution,
        1 if increment_attempts else 0,
    )


async def _append_tool_result(
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


async def resolve_uncertain(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    epoch: int,
    worker_id: str,
    step_index: int,
    state: Uncertain,
    tool: RegisteredToolLike,
    max_payload_bytes: int,
) -> Any:
    """Apply `tool.safety`'s declared policy to an `Uncertain` window.

    Raises `NeedsReviewHalted` for `unsafe` (and for `reconcilable` whose
    `reconcile_fn` returns `Unknown()`) rather than returning — there is no
    result to hand back to the caller in either case, because none was
    produced and none may be guessed.
    """
    if tool.safety == "retry_safe":
        # The strongest option available: re-execute, passing the same
        # idempotency key through so the provider deduplicates on its own
        # side if this is in fact a second physical attempt
        # (contracts/tool-contract.md).
        start = time.monotonic()
        result = await tool.fn(
            state.args_canonical,
            idempotency_key=state.idempotency_key,
            conn=conn,
            run_id=run_id,
            step_index=step_index,
        )
        latency_ms = (time.monotonic() - start) * 1000
        async with conn.transaction():
            await _record_result(
                conn,
                idempotency_key=state.idempotency_key,
                result=result,
                result_epoch=epoch,
                resolution="retry_safe",
                increment_attempts=True,
            )
            await _append_tool_result(
                conn,
                run_id=run_id,
                epoch=epoch,
                worker_id=worker_id,
                step_index=step_index,
                tool_name=tool.name,
                idempotency_key=state.idempotency_key,
                result=result,
                latency_ms=latency_ms,
                resolution="retry_safe",
                max_payload_bytes=max_payload_bytes,
            )
        return result

    if tool.safety == "reconcilable":
        assert tool.reconcile_fn is not None  # enforced at registration (FR-046)
        outcome = await tool.reconcile_fn(state.args_canonical, state.idempotency_key)

        if isinstance(outcome, Unknown):
            # A reconciler that cannot determine the answer must say so
            # rather than default to either branch — guessing here is worse
            # than no reconciler at all (contracts/tool-contract.md).
            async with conn.transaction():
                await conn.execute(
                    "UPDATE tool_journal SET resolution = 'unsafe_halted', resolved_at = now() "
                    "WHERE idempotency_key = $1",
                    state.idempotency_key,
                )
            await halt_needs_review(
                conn,
                run_id=run_id,
                epoch=epoch,
                worker_id=worker_id,
                step_index=step_index,
                idempotency_key=state.idempotency_key,
                tool_name=tool.name,
                reason=f"reconciliation for {tool.name!r} returned Unknown()",
                max_payload_bytes=max_payload_bytes,
            )
            raise NeedsReviewHalted(run_id)

        if isinstance(outcome, Executed):
            async with conn.transaction():
                await _record_result(
                    conn,
                    idempotency_key=state.idempotency_key,
                    result=outcome.result,
                    result_epoch=epoch,
                    resolution="reconcilable",
                    increment_attempts=False,
                )
                await _append_tool_result(
                    conn,
                    run_id=run_id,
                    epoch=epoch,
                    worker_id=worker_id,
                    step_index=step_index,
                    tool_name=tool.name,
                    idempotency_key=state.idempotency_key,
                    result=outcome.result,
                    latency_ms=0.0,
                    resolution="reconcilable",
                    max_payload_bytes=max_payload_bytes,
                )
            return outcome.result

        assert isinstance(outcome, NotExecuted)
        start = time.monotonic()
        result = await tool.fn(
            state.args_canonical,
            idempotency_key=state.idempotency_key,
            conn=conn,
            run_id=run_id,
            step_index=step_index,
        )
        latency_ms = (time.monotonic() - start) * 1000
        async with conn.transaction():
            await _record_result(
                conn,
                idempotency_key=state.idempotency_key,
                result=result,
                result_epoch=epoch,
                resolution="reconcilable",
                increment_attempts=True,
            )
            await _append_tool_result(
                conn,
                run_id=run_id,
                epoch=epoch,
                worker_id=worker_id,
                step_index=step_index,
                tool_name=tool.name,
                idempotency_key=state.idempotency_key,
                result=result,
                latency_ms=latency_ms,
                resolution="reconcilable",
                max_payload_bytes=max_payload_bytes,
            )
        return result

    # unsafe: do not guess. Halt, release the lease, and surface the
    # specific ambiguous call for an operator (FR-049).
    assert tool.safety == "unsafe"
    async with conn.transaction():
        await conn.execute(
            "UPDATE tool_journal SET resolution = 'unsafe_halted', resolved_at = now() "
            "WHERE idempotency_key = $1",
            state.idempotency_key,
        )
    await halt_needs_review(
        conn,
        run_id=run_id,
        epoch=epoch,
        worker_id=worker_id,
        step_index=step_index,
        idempotency_key=state.idempotency_key,
        tool_name=tool.name,
        reason=f"{tool.name!r} is unsafe: cannot determine whether the previous attempt's "
        "side effect occurred",
        max_payload_bytes=max_payload_bytes,
    )
    raise NeedsReviewHalted(run_id)
