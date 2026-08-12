"""`GET /api/workers` — fleet state (plan.md P3.6, T176).

Also backs the Deployments page, which groups by `code_version` — no new
schema and no new instrumentation, since `workers.code_version` already
exists (contracts/openapi.yaml).

The kill endpoints (`POST /api/workers/{worker_id}/kill`) are deferred to
phase 8: their documented response carries a `chaos_event_id`, and
`chaos_events` does not exist until phase 8's migration. Building the kill
endpoint against this contract now would mean either inventing a schema
change three phases early or shipping a response that silently disagrees
with `contracts/openapi.yaml` — both rejected; see the phase-3 completion
report for the full reasoning. `GET /api/workers` has no such dependency
and is not deferred.
"""

from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from anchor.api.serializers.workers import WORKER_COLUMNS, WorkerResponse, serialize_worker

router = APIRouter()


class WorkersListResponse(BaseModel):
    items: list[WorkerResponse]


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


@router.get("/api/workers", response_model=WorkersListResponse)
async def list_workers(pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> WorkersListResponse:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT {WORKER_COLUMNS} FROM workers ORDER BY label, incarnation DESC"
        )
    return WorkersListResponse(items=[serialize_worker(row) for row in rows])
