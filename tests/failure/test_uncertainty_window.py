"""T236-T237 — the uncertainty window, one case per declared category
(FR-047, FR-048, FR-049): `retry_safe` re-executes with the key passed
through and produces one effect row; `reconcilable` runs the reconciler and
branches, recording `resolution`; `unsafe` halts as `needs_review` holding
no lease. A `reconcile_fn` returning `Unknown()` escalates to `needs_review`
exactly like `unsafe` — a reconciler that guesses is worse than none.

Each test manually inserts a `tool_journal` row with `result IS NULL` to
simulate "a crash landed between the committed intent and its result" —
the uncertainty window — without needing an actual worker kill.
"""

from __future__ import annotations

import json
from typing import Any

import asyncpg
import pytest

from anchor.core.journal.keys import derive_key
from anchor.core.journal.policies import NeedsReviewHalted
from anchor.core.journal.reconcile import Executed, NotExecuted, Unknown
from anchor.core.journal.two_phase import execute_tool_call
from anchor.runtime.tools.registry import ToolDeclaration

MAX_PAYLOAD = 1_000_000


async def _noop_flush() -> None:
    return None


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, status) VALUES ('demo_short', 'running') RETURNING id"
    )
    return run_id


async def _register(conn: asyncpg.Connection, decl: ToolDeclaration) -> None:
    await conn.execute(
        """
        INSERT INTO tool_registry
            (name, safety, naturally_idempotent, provider_accepts_key, has_reconcile_fn,
             default_policy, declaration_hash, declared_by_version)
        VALUES ($1, $2, $3, $4, $5, $6, 'h', 'test')
        ON CONFLICT DO NOTHING
        """,
        decl.name,
        decl.safety,
        decl.naturally_idempotent,
        decl.provider_accepts_key,
        decl.has_reconcile_fn,
        decl.default_policy,
    )


async def _insert_uncertain_journal_row(
    conn: asyncpg.Connection, *, run_id: int, key: str, tool_name: str, args: dict[str, Any]
) -> None:
    await conn.execute(
        """
        INSERT INTO tool_journal
            (idempotency_key, run_id, step_index, tool_name, args_canonical, args_hash, intent_epoch)
        VALUES ($1, $2, 0, $3, $4::jsonb, 'h', 0)
        """,
        key,
        run_id,
        tool_name,
        json.dumps(args),
    )


@pytest.mark.asyncio
async def test_retry_safe_reexecutes_with_key_passed_through(db_pool: asyncpg.Pool) -> None:
    calls: list[str] = []

    async def _charge(args: dict[str, Any], *, idempotency_key: str, **_: Any) -> Any:
        calls.append(idempotency_key)
        return {"charged": True, "key": idempotency_key}

    decl = ToolDeclaration(
        name="test_charge_card", fn=_charge, safety="retry_safe", provider_accepts_key=True
    )
    args = {"amount_cents": 500}

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await _register(conn, decl)
        key = derive_key(run_id, 0, decl.name, args)
        await _insert_uncertain_journal_row(
            conn, run_id=run_id, key=key, tool_name=decl.name, args=args
        )

        result = await execute_tool_call(
            conn,
            run_id=run_id,
            epoch=0,
            worker_id="worker-a#1",
            step_index=0,
            tool=decl,
            args=args,
            flush_pending_nondet=_noop_flush,
            max_payload_bytes=MAX_PAYLOAD,
        )

        row = await conn.fetchrow(
            "SELECT result, resolution, attempts FROM tool_journal WHERE idempotency_key = $1", key
        )

    assert calls == [key], "the same idempotency key must be passed through to the re-execution"
    assert result == {"charged": True, "key": key}
    assert row is not None
    assert json.loads(row["result"]) == {"charged": True, "key": key}
    assert row["resolution"] == "retry_safe"
    assert row["attempts"] == 2, "a genuine re-execution increments attempts"


@pytest.mark.asyncio
async def test_reconcilable_executed_records_result_without_reinvoking(
    db_pool: asyncpg.Pool,
) -> None:
    invoked = False

    async def _create_ticket(args: dict[str, Any], **_: Any) -> Any:
        nonlocal invoked
        invoked = True
        return {"should": "never run"}

    async def _reconcile(args: dict[str, Any], key: str) -> Any:
        return Executed({"external_key": key, "status": "already open"})

    decl = ToolDeclaration(
        name="test_create_ticket_a",
        fn=_create_ticket,
        safety="reconcilable",
        reconcile_fn=_reconcile,
    )
    args = {"title": "t1"}

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await _register(conn, decl)
        key = derive_key(run_id, 0, decl.name, args)
        await _insert_uncertain_journal_row(
            conn, run_id=run_id, key=key, tool_name=decl.name, args=args
        )

        result = await execute_tool_call(
            conn,
            run_id=run_id,
            epoch=0,
            worker_id="worker-a#1",
            step_index=0,
            tool=decl,
            args=args,
            flush_pending_nondet=_noop_flush,
            max_payload_bytes=MAX_PAYLOAD,
        )

        row = await conn.fetchrow(
            "SELECT resolution, attempts FROM tool_journal WHERE idempotency_key = $1", key
        )

    assert not invoked, "Executed() must short-circuit the tool's own fn"
    assert result == {"external_key": key, "status": "already open"}
    assert row is not None
    assert row["resolution"] == "reconcilable"
    assert row["attempts"] == 1


@pytest.mark.asyncio
async def test_reconcilable_not_executed_reexecutes(db_pool: asyncpg.Pool) -> None:
    async def _create_ticket(args: dict[str, Any], **_: Any) -> Any:
        return {"status": "created now"}

    async def _reconcile(args: dict[str, Any], key: str) -> Any:
        return NotExecuted()

    decl = ToolDeclaration(
        name="test_create_ticket_b",
        fn=_create_ticket,
        safety="reconcilable",
        reconcile_fn=_reconcile,
    )
    args = {"title": "t2"}

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await _register(conn, decl)
        key = derive_key(run_id, 0, decl.name, args)
        await _insert_uncertain_journal_row(
            conn, run_id=run_id, key=key, tool_name=decl.name, args=args
        )

        result = await execute_tool_call(
            conn,
            run_id=run_id,
            epoch=0,
            worker_id="worker-a#1",
            step_index=0,
            tool=decl,
            args=args,
            flush_pending_nondet=_noop_flush,
            max_payload_bytes=MAX_PAYLOAD,
        )

    assert result == {"status": "created now"}


@pytest.mark.asyncio
async def test_reconcilable_unknown_escalates_to_needs_review(db_pool: asyncpg.Pool) -> None:
    async def _create_ticket(args: dict[str, Any], **_: Any) -> Any:
        raise AssertionError("must not be invoked when the reconciler answers Unknown()")

    async def _reconcile(args: dict[str, Any], key: str) -> Any:
        return Unknown()

    decl = ToolDeclaration(
        name="test_create_ticket_c",
        fn=_create_ticket,
        safety="reconcilable",
        reconcile_fn=_reconcile,
    )
    args = {"title": "t3"}

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await _register(conn, decl)
        key = derive_key(run_id, 0, decl.name, args)
        await _insert_uncertain_journal_row(
            conn, run_id=run_id, key=key, tool_name=decl.name, args=args
        )

        with pytest.raises(NeedsReviewHalted):
            await execute_tool_call(
                conn,
                run_id=run_id,
                epoch=0,
                worker_id="worker-a#1",
                step_index=0,
                tool=decl,
                args=args,
                flush_pending_nondet=_noop_flush,
                max_payload_bytes=MAX_PAYLOAD,
            )

        run_row = await conn.fetchrow(
            "SELECT status, owner_worker_id, lease_expires_at FROM runs WHERE id = $1", run_id
        )
        journal_row = await conn.fetchrow(
            "SELECT resolution, result FROM tool_journal WHERE idempotency_key = $1", key
        )

    assert run_row is not None
    assert run_row["status"] == "needs_review"
    assert run_row["owner_worker_id"] is None
    assert run_row["lease_expires_at"] is None
    assert journal_row is not None
    assert journal_row["resolution"] == "unsafe_halted"
    assert journal_row["result"] is None, "an Unknown() reconciliation must not guess a result"


@pytest.mark.asyncio
async def test_unsafe_halts_as_needs_review_holding_no_lease(db_pool: asyncpg.Pool) -> None:
    async def _send_email(args: dict[str, Any], **_: Any) -> Any:
        raise AssertionError("an unsafe tool's own fn must never be invoked to resolve a window")

    decl = ToolDeclaration(name="test_send_email", fn=_send_email, safety="unsafe")
    args = {"recipient": "a@example.com"}

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "UPDATE runs SET owner_worker_id = 'worker-a#1', "
            "lease_expires_at = now() + interval '1 minute' WHERE id = $1",
            run_id,
        )
        await _register(conn, decl)
        key = derive_key(run_id, 0, decl.name, args)
        await _insert_uncertain_journal_row(
            conn, run_id=run_id, key=key, tool_name=decl.name, args=args
        )

        with pytest.raises(NeedsReviewHalted):
            await execute_tool_call(
                conn,
                run_id=run_id,
                epoch=0,
                worker_id="worker-a#1",
                step_index=0,
                tool=decl,
                args=args,
                flush_pending_nondet=_noop_flush,
                max_payload_bytes=MAX_PAYLOAD,
            )

        run_row = await conn.fetchrow(
            "SELECT status, owner_worker_id, lease_expires_at, finished_at FROM runs WHERE id = $1",
            run_id,
        )
        needs_review_event = await conn.fetchrow(
            "SELECT payload FROM run_events WHERE run_id = $1 AND type = 'RUN_NEEDS_REVIEW'",
            run_id,
        )

    assert run_row is not None
    assert run_row["status"] == "needs_review"
    assert run_row["owner_worker_id"] is None
    assert run_row["lease_expires_at"] is None
    assert run_row["finished_at"] is not None
    assert needs_review_event is not None
    payload = json.loads(needs_review_event["payload"])
    assert payload["tool_name"] == "test_send_email"
    assert payload["idempotency_key"] == key
    assert set(payload["available_resolutions"]) == {"mark_executed", "mark_not_executed", "retry"}
