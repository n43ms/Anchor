"""T244 — a completed key emits `STEP_SKIPPED_ON_REPLAY` carrying
`idempotency_key`, `tool_name`, `original_result_at`, and `original_epoch`,
and returns the recorded result **without** invoking the tool's `fn` again.
"""

from __future__ import annotations

import json
from typing import Any

import asyncpg
import pytest

from anchor.core.journal.keys import derive_key
from anchor.core.journal.two_phase import execute_tool_call
from anchor.runtime.tools.registry import ToolDeclaration, register_tool

MAX_PAYLOAD = 1_000_000


async def _noop_flush() -> None:
    return None


@pytest.mark.asyncio
async def test_completed_key_skips_and_never_reinvokes(db_pool: asyncpg.Pool) -> None:
    invoked = False

    async def _fn(args: dict[str, Any], **_: Any) -> Any:
        nonlocal invoked
        invoked = True
        return {"should": "never be reached"}

    decl = ToolDeclaration(
        name="test_skip_tool", fn=_fn, safety="retry_safe", naturally_idempotent=True
    )
    args = {"query": "already done"}

    async with db_pool.acquire() as conn:
        await register_tool(conn, decl, code_version="test")
        run_id: int = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_short') RETURNING id"
        )
        key = derive_key(run_id, 0, decl.name, args)
        await conn.execute(
            """
            INSERT INTO tool_journal
                (idempotency_key, run_id, step_index, tool_name, args_canonical, args_hash,
                 intent_epoch, result, result_at, result_epoch)
            VALUES ($1, $2, 0, $3, $4::jsonb, 'h', 0, $5::jsonb, now(), 0)
            """,
            key,
            run_id,
            decl.name,
            json.dumps(args),
            json.dumps({"results": ["cached"]}),
        )

        result = await execute_tool_call(
            conn,
            run_id=run_id,
            epoch=0,
            worker_id="worker-b#1",
            step_index=0,
            tool=decl,
            args=args,
            flush_pending_nondet=_noop_flush,
            max_payload_bytes=MAX_PAYLOAD,
        )

        event = await conn.fetchrow(
            "SELECT payload, epoch, worker_id FROM run_events "
            "WHERE run_id = $1 AND type = 'STEP_SKIPPED_ON_REPLAY'",
            run_id,
        )

    assert not invoked
    assert result == {"results": ["cached"]}
    assert event is not None
    payload = json.loads(event["payload"])
    assert payload["idempotency_key"] == key
    assert payload["tool_name"] == decl.name
    assert payload["original_epoch"] == 0
    assert payload["original_result_at"] is not None
    # A replayed skip is attributed to the *resuming* worker, distinct from
    # whichever worker originally recorded the result — the console's
    # replayed-vs-executed distinction depends on this attribution being
    # honest about who is replaying, not who executed originally.
    assert event["worker_id"] == "worker-b#1"
