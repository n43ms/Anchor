"""`GET /api/workers` — fleet state (plan.md P3.6, T176).

Also backs the Deployments page, which groups by `code_version` — no new
schema and no new instrumentation, since `workers.code_version` already
exists (contracts/openapi.yaml).

**Dedup by slot label.** `workers` rows are append-only per incarnation
(`anchor/worker/registry/register.py`): every restart inserts a new row
rather than updating the old one, and a hard kill never sets `stopped_at`
on the row it abandons (`register.mark_stopped`'s docstring — that
omission is deliberately informative). `label` is the fleet *slot*;
`incarnation` is the generation currently occupying it. So the only row
that describes "what is running in this slot right now" is the
highest-incarnation row per label — `DISTINCT ON (label) ... ORDER BY
label, incarnation DESC`. Returning every historical incarnation instead
(the prior query) makes every crashed worker a permanent ghost node and
makes `degraded` computed over that list latch true forever. This is a
read-query fix aligned with the identity model already documented in
`identity.py`, not a schema change.

**The kill endpoint is intentionally partial.** `contracts/openapi.yaml`'s
documented response for `POST /api/workers/{worker_id}/kill` carries a
`chaos_event_id`, and `chaos_events` does not exist until phase 8's
migration 005 (T491). Rather than invent that table early or leave the
route unmounted (which surfaces to the operator as a bare 404 on a
first-class, documented product feature — Principle VIII), this mounts a
**hard-kill-only** version now: it drives the same Redis
`publish_kill`/`subscribe_and_wait_for_kill` mechanism every worker already
runs, and returns `{ok, worker_id, mode}` without `chaos_event_id`. A
`graceful` kill is refused with `501`: no channel or worker-side handler
for a *remotely requested* cooperative shutdown exists yet (the only
graceful path today is the worker's own `SIGTERM` handler in
`anchor/worker/__main__.py`, which nothing here can address into) — stating
that plainly is preferable to silently downgrading `graceful` to a hard
kill it did not ask for. Phase 8 adds `chaos_event_id` logging and rate
limiting; both are additive to this contract, not breaking.
"""

from __future__ import annotations

from typing import Annotated, Literal

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from anchor.api.errors import ApiError
from anchor.api.serializers.workers import WORKER_COLUMNS, WorkerResponse, serialize_worker
from anchor.worker.registry.kill import publish_kill

router = APIRouter()


class WorkersListResponse(BaseModel):
    items: list[WorkerResponse]


class KillRequest(BaseModel):
    graceful: bool = False


class KillResponse(BaseModel):
    ok: bool
    worker_id: str
    mode: Literal["hard"]


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


@router.get("/api/workers", response_model=WorkersListResponse)
async def list_workers(pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> WorkersListResponse:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT DISTINCT ON (label) {WORKER_COLUMNS} FROM workers ORDER BY label, incarnation DESC"
        )
    return WorkersListResponse(items=[serialize_worker(row) for row in rows])


@router.post("/api/workers/{worker_id}/kill", response_model=KillResponse, status_code=202)
async def kill_worker(
    worker_id: str,
    body: KillRequest,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    request: Request,
) -> KillResponse:
    """Hard-kill only — see module docstring for why `graceful` is refused
    rather than silently downgraded.
    """
    if body.graceful:
        raise ApiError(
            status_code=501,
            error="graceful_kill_not_implemented",
            message="graceful kill is not wired yet — no remote cooperative-shutdown "
            "channel exists; retry with graceful=false for a hard kill",
        )

    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT EXISTS (SELECT 1 FROM workers WHERE id = $1)", worker_id)
        if not exists:
            raise ApiError(status_code=404, error="worker_not_found", message="worker not found")
        await conn.execute("UPDATE workers SET stopped_at = now() WHERE id = $1", worker_id)

    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is None:
        raise ApiError(
            status_code=503,
            error="redis_unreachable",
            message="redis unreachable — kill delivery unavailable; execution is unaffected "
            "because redis is non-authoritative",
        )
    try:
        await publish_kill(redis_client, worker_id)
    except Exception as exc:
        raise ApiError(
            status_code=503,
            error="redis_unreachable",
            message="redis unreachable — kill delivery unavailable; execution is unaffected "
            "because redis is non-authoritative",
        ) from exc

    return KillResponse(ok=True, worker_id=worker_id, mode="hard")
