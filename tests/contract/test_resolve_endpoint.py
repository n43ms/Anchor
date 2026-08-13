"""T243 — `POST /api/runs/{id}/resolve`: the write is attributed to
`worker_id: "operator"` at the run's current epoch, permitted only on a
leaseless `needs_review` run, and offers three outcomes none of which is a
guess (D-24, FR-050).
"""

from __future__ import annotations

from typing import Any

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from anchor.api.app import create_app
from anchor.core.journal.keys import derive_key
from anchor.core.journal.policies import NeedsReviewHalted
from anchor.core.journal.two_phase import execute_tool_call
from anchor.runtime.tools.registry import ToolDeclaration, register_tool

MAX_PAYLOAD = 1_000_000


async def _noop_flush() -> None:
    return None


async def _make_needs_review_run(db_pool: asyncpg.Pool, *, is_demo: bool = True) -> tuple[int, str]:
    async def _send_email(args: dict[str, Any], **_: Any) -> Any:
        raise AssertionError("must not be invoked while the run is still needs_review")

    decl = ToolDeclaration(name="send_email", fn=_send_email, safety="unsafe")
    args = {"recipient": "a@example.com"}

    async with db_pool.acquire() as conn:
        await register_tool(conn, decl, code_version="test")
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type, status, owner_worker_id, lease_expires_at, is_demo) "
            "VALUES ('demo_unsafe', 'running', 'worker-a#1', now() + interval '1 minute', $1) "
            "RETURNING id",
            is_demo,
        )
        key = derive_key(run_id, 0, decl.name, args)
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
    return run_id, key


def _client_for(db_pool: asyncpg.Pool) -> AsyncClient:
    app = create_app()
    app.state.db_pool = db_pool
    app.state.deployment_mode = "local"
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_mark_executed_writes_the_missing_result_and_resumes(db_pool: asyncpg.Pool) -> None:
    run_id, key = await _make_needs_review_run(db_pool)

    async with _client_for(db_pool) as client:
        resp = await client.post(
            f"/api/runs/{run_id}/resolve", json={"resolution": "mark_executed"}
        )

    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"

    async with db_pool.acquire() as conn:
        journal_row = await conn.fetchrow(
            "SELECT result, resolution FROM tool_journal WHERE idempotency_key = $1", key
        )
        result_event = await conn.fetchrow(
            "SELECT worker_id, epoch FROM run_events WHERE run_id = $1 AND type = 'TOOL_RESULT'",
            run_id,
        )

    assert journal_row is not None
    assert journal_row["result"] is not None
    assert journal_row["resolution"] == "operator_marked_executed"
    assert result_event is not None
    assert result_event["worker_id"] == "operator"
    assert result_event["epoch"] == 0


@pytest.mark.asyncio
async def test_mark_not_executed_authorizes_execution_and_resumes(db_pool: asyncpg.Pool) -> None:
    run_id, key = await _make_needs_review_run(db_pool)

    async with _client_for(db_pool) as client:
        resp = await client.post(
            f"/api/runs/{run_id}/resolve", json={"resolution": "mark_not_executed"}
        )

    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT result, resolution FROM tool_journal WHERE idempotency_key = $1", key
        )
    assert row is not None
    assert row["result"] is None
    assert row["resolution"] == "operator_marked_not_executed"


@pytest.mark.asyncio
async def test_retry_resumes_without_touching_the_journal(db_pool: asyncpg.Pool) -> None:
    run_id, key = await _make_needs_review_run(db_pool)

    async with db_pool.acquire() as conn:
        before = await conn.fetchrow(
            "SELECT result, resolution FROM tool_journal WHERE idempotency_key = $1", key
        )

    async with _client_for(db_pool) as client:
        resp = await client.post(f"/api/runs/{run_id}/resolve", json={"resolution": "retry"})

    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"

    async with db_pool.acquire() as conn:
        after = await conn.fetchrow(
            "SELECT result, resolution FROM tool_journal WHERE idempotency_key = $1", key
        )
    assert before is not None and after is not None
    assert dict(after) == dict(before), "retry must not write to the journal at all"


@pytest.mark.asyncio
async def test_resolve_rejects_a_run_not_in_needs_review(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_short') RETURNING id"
        )
    async with _client_for(db_pool) as client:
        resp = await client.post(f"/api/runs/{run_id}/resolve", json={"resolution": "retry"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_resolve_rejects_a_non_demo_run_in_demonstration_mode(db_pool: asyncpg.Pool) -> None:
    run_id, _ = await _make_needs_review_run(db_pool, is_demo=False)

    app = create_app()
    app.state.db_pool = db_pool
    app.state.deployment_mode = "demonstration"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/runs/{run_id}/resolve", json={"resolution": "retry"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_resolve_404s_on_an_unknown_run(db_pool: asyncpg.Pool) -> None:
    async with _client_for(db_pool) as client:
        resp = await client.post("/api/runs/999999999/resolve", json={"resolution": "retry"})
    assert resp.status_code == 404
