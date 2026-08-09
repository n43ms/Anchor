"""`POST /api/runs` and the read endpoints (plan.md P1.3, P1.7)."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from anchor.api.serializers.runs import RUN_COLUMNS, RunResponse, serialize_run
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


_RUN_ROW_SQL = f"SELECT {RUN_COLUMNS} FROM runs WHERE id = $1"


def _encode_cursor(created_at: datetime, run_id: int) -> str:
    """Opaque keyset cursor over `(created_at, id)` — the same pair the
    `ORDER BY` sorts on, so the page boundary is stable even while newer
    rows are being inserted concurrently (T071/T098).
    """
    raw = f"{created_at.isoformat()}|{run_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        created_at_str, run_id_str = raw.rsplit("|", 1)
        return datetime.fromisoformat(created_at_str), int(run_id_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail="malformed cursor") from exc


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
                    return serialize_run(row)

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
            return serialize_run(row)


@router.get("/api/runs")
async def list_runs(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    status: list[str] | None = None,
    agent_type: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Newest first, keyset-paginated on `(created_at, id)` — never
    offset-based, so a page boundary stays correct while runs are being
    submitted concurrently (contracts/openapi.yaml).
    """
    page_size = min(limit, 200)
    async with pool.acquire() as conn:
        clauses = []
        params: list[Any] = []
        if status:
            params.append(status)
            clauses.append(f"status = ANY(${len(params)})")
        if agent_type:
            params.append(agent_type)
            clauses.append(f"agent_type = ${len(params)}")
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            params.append(cursor_created_at)
            params.append(cursor_id)
            clauses.append(f"(created_at, id) < (${len(params) - 1}, ${len(params)})")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(page_size)
        rows = await conn.fetch(
            f"""
            SELECT {RUN_COLUMNS}
            FROM runs
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ${len(params)}
            """,
            *params,
        )

    items = [serialize_run(r).model_dump() for r in rows]
    next_cursor = (
        _encode_cursor(rows[-1]["created_at"], rows[-1]["id"]) if len(rows) == page_size else None
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: int, pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> RunResponse:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_RUN_ROW_SQL, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return serialize_run(row)


@router.get("/api/runs/{run_id}/events")
async def get_run_events(
    run_id: int,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    after_seq: int = 0,
    limit: int = 200,
) -> dict[str, Any]:
    page_size = min(limit, 1000)
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
            page_size,
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
    next_after_seq = items[-1]["seq"] if len(items) == page_size else None
    return {"run_id": run_id, "items": items, "next_after_seq": next_after_seq}
