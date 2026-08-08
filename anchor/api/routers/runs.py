"""`POST /api/runs` and the read endpoints (plan.md P1.3, P1.7)."""

from __future__ import annotations

import json
from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from anchor.core.config.loader import load_runtime_settings
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.runtime.agents.registry import is_registered

router = APIRouter()


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


class RunSubmission(BaseModel):
    agent_type: str
    input: dict[str, Any] = Field(default_factory=dict)
    client_request_key: str | None = None
    priority: int = 0
    is_demo: bool = False


class RunResponse(BaseModel):
    id: int
    display_id: str
    agent_type: str
    status: str
    epoch: int
    owner_worker_id: str | None
    lease_expires_at: str | None
    orphaned: bool
    priority: int
    attempts: int
    is_demo: bool
    cancel_requested_at: str | None
    created_at: str
    claimed_at: str | None
    finished_at: str | None


_RUN_COLUMNS = """
    id, agent_type, status, epoch, owner_worker_id, lease_expires_at,
    priority, attempts, is_demo, cancel_requested_at, created_at,
    claimed_at, finished_at,
    -- Derived, never stored (data-model.md §12): a run is orphaned exactly
    -- when it is running and its lease has actually expired against the
    -- database clock (I5) — not merely when it holds one. Storing this
    -- would require a writer at the exact moment nobody owns the run.
    (status = 'running' AND lease_expires_at < now()) AS orphaned
"""

_RUN_ROW_SQL = f"SELECT {_RUN_COLUMNS} FROM runs WHERE id = $1"


def _serialize_run(row: asyncpg.Record) -> RunResponse:
    return RunResponse(
        id=row["id"],
        display_id=f"run_{row['id']}",
        agent_type=row["agent_type"],
        status=row["status"],
        epoch=row["epoch"],
        owner_worker_id=row["owner_worker_id"],
        lease_expires_at=row["lease_expires_at"].isoformat() if row["lease_expires_at"] else None,
        orphaned=row["orphaned"],
        priority=row["priority"],
        attempts=row["attempts"],
        is_demo=row["is_demo"],
        cancel_requested_at=(
            row["cancel_requested_at"].isoformat() if row["cancel_requested_at"] else None
        ),
        created_at=row["created_at"].isoformat(),
        claimed_at=row["claimed_at"].isoformat() if row["claimed_at"] else None,
        finished_at=row["finished_at"].isoformat() if row["finished_at"] else None,
    )


@router.post("/api/runs", response_model=RunResponse, status_code=201)
async def submit_run(
    submission: RunSubmission,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> RunResponse:
    if not is_registered(submission.agent_type):
        raise HTTPException(status_code=404, detail=f"unknown agent_type: {submission.agent_type}")

    async with pool.acquire() as conn:
        settings = await load_runtime_settings(conn)
        async with conn.transaction():
            if submission.client_request_key is not None:
                existing = await conn.fetchrow(
                    "SELECT id FROM runs WHERE client_request_key = $1",
                    submission.client_request_key,
                )
                if existing is not None:
                    row = await conn.fetchrow(_RUN_ROW_SQL, existing["id"])
                    assert row is not None
                    return _serialize_run(row)

            run_row = await conn.fetchrow(
                """
                INSERT INTO runs (agent_type, input, client_request_key, priority, is_demo)
                VALUES ($1, $2::jsonb, $3, $4, $5)
                RETURNING id, epoch
                """,
                submission.agent_type,
                json.dumps(submission.input),
                submission.client_request_key,
                submission.priority,
                submission.is_demo,
            )
            assert run_row is not None
            run_id, epoch = run_row["id"], run_row["epoch"]

            await append(
                conn,
                run_id=run_id,
                type=EventType.RUN_SUBMITTED,
                payload={
                    "agent_type": submission.agent_type,
                    "input": submission.input,
                    "is_demo": submission.is_demo,
                    "client_request_key": submission.client_request_key,
                },
                epoch=epoch,
                worker_id="api",
                max_payload_bytes=settings.max_event_payload_bytes,
            )

            row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
            assert row is not None
            return _serialize_run(row)


@router.get("/api/runs")
async def list_runs(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    status: list[str] | None = None,
    agent_type: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        clauses = []
        params: list[Any] = []
        if status:
            params.append(status)
            clauses.append(f"status = ANY(${len(params)})")
        if agent_type:
            params.append(agent_type)
            clauses.append(f"agent_type = ${len(params)}")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(min(limit, 200))
        rows = await conn.fetch(
            f"""
            SELECT {_RUN_COLUMNS}
            FROM runs
            {where}
            ORDER BY created_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )
        return {"items": [_serialize_run(r).model_dump() for r in rows]}


@router.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: int, pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> RunResponse:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _serialize_run(row)


@router.get("/api/runs/{run_id}/events")
async def get_run_events(
    run_id: int,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    after_seq: int = 0,
    limit: int = 200,
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM runs WHERE id = $1", run_id)
        if not exists:
            raise HTTPException(status_code=404, detail="run not found")
        rows = await conn.fetch(
            """
            SELECT run_id, seq, type, payload, epoch, worker_id, step_index, created_at
            FROM run_events
            WHERE run_id = $1 AND seq > $2
            ORDER BY seq ASC
            LIMIT $3
            """,
            run_id,
            after_seq,
            min(limit, 1000),
        )
    items = [
        {
            "run_id": r["run_id"],
            "seq": r["seq"],
            "type": r["type"],
            "payload": json.loads(r["payload"]),
            "epoch": r["epoch"],
            "worker_id": r["worker_id"],
            "step_index": r["step_index"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
    next_after_seq = items[-1]["seq"] if len(items) == min(limit, 1000) else None
    return {"run_id": run_id, "items": items, "next_after_seq": next_after_seq}
