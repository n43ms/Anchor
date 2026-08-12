"""T148 — `pending` and expired-lease runs are handled by ONE statement,
never two queries (FR-009, constitution Principle II: "two separate queries
create a window in which two workers can claim the same row").

Structural check: `_CLAIM_SQL` is a single `WITH ... UPDATE ...` statement
(one semicolon-free string, exactly one `UPDATE`), so there is no code path
that issues a separate SELECT before the UPDATE. Behavioural check: one call
to `claim_one` claims a `pending` run, and one call claims an expired-lease
`running` run — the same statement serves both, not two different ones
dispatched on status.
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases import claim as claim_module
from anchor.core.leases.claim import claim_one

MAX_PAYLOAD = 1_000_000


def test_claim_sql_is_a_single_statement() -> None:
    sql = claim_module._CLAIM_SQL
    assert sql.strip().count(";") == 0, "no semicolon-separated second statement"
    # "FOR UPDATE SKIP LOCKED" is a row-lock clause, not a second UPDATE
    # statement — the only actual `UPDATE <table>` clause is the claim
    # itself, so `\nUPDATE ` (the statement keyword at the start of a line)
    # is what distinguishes the two.
    assert sql.count("\nUPDATE ") == 1, (
        "exactly one UPDATE statement — select and claim are not two queries"
    )
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert sql.count("SELECT") == 2, (
        "the candidate SELECT and the uncorrelated cap-count SELECT are the only two SELECTs; "
        "neither is a separate round trip issued by Python"
    )


async def _insert_run(conn: asyncpg.Connection, agent_type: str = "demo_minimal") -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
        agent_type,
        json.dumps({}),
    )
    await append(
        conn,
        run_id=run_id,
        type=EventType.RUN_SUBMITTED,
        payload={
            "agent_type": agent_type,
            "input": {},
            "is_demo": True,
            "client_request_key": None,
            "chaos_run_id": None,
        },
        epoch=0,
        worker_id="api",
        max_payload_bytes=MAX_PAYLOAD,
    )
    return run_id


@pytest.mark.asyncio
async def test_one_statement_claims_a_pending_run(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        claimed = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=4_000,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert claimed is not None
        assert claimed.run_id == run_id
        assert claimed.reason == "initial"


@pytest.mark.asyncio
async def test_the_same_statement_reclaims_an_expired_lease_run(db_pool: asyncpg.Pool) -> None:
    import asyncio

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev'), "
            "('worker-b#1', 'worker-b', 1, 'test', 2, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        first = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=50,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert first is not None
        await asyncio.sleep(0.2)

        second = await claim_one(
            conn,
            worker_id="worker-b#1",
            lease_duration_ms=4_000,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert second is not None
        assert second.run_id == run_id
        assert second.reason == "reclaimed_after_lease_expiry"
