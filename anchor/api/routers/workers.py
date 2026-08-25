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

**The kill endpoint was intentionally partial through phase 7.**
`contracts/openapi.yaml`'s documented response for
`POST /api/workers/{worker_id}/kill` carries a `chaos_event_id`, which
needed `chaos_events` (migration `006_chaos.py`, phase 8, T491) to exist.
Now that it does, every kill — the console's manual button and the chaos
harness's kill injection (`anchor.chaos.injections.kill`) alike — is
recorded as a `chaos_events` row here, server-side, in the same
transaction as `stopped_at` (D-36: one implementation, not a console path
and a harness path that could silently diverge). `chaos_run_id` is `NULL`
for the console's manual kill and set for a harness-driven one
(data-model.md §6). A `graceful` kill is still refused with `501`: no
channel or worker-side handler for a *remotely requested* cooperative
shutdown exists yet (the only graceful path today is the worker's own
`SIGTERM` handler in `anchor/worker/__main__.py`, which nothing here can
address into) — stating that plainly is preferable to silently downgrading
`graceful` to a hard kill it did not ask for.
"""

from __future__ import annotations

from typing import Annotated, Literal

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from anchor.api.errors import ApiError
from anchor.api.serializers.workers import WORKER_COLUMNS, WorkerResponse, serialize_worker
from anchor.worker.registry.kill import publish_kill

# Deliberately not imported from `anchor.chaos.recorder`, even though that
# module does the same insert for every other injection type: `anchor.api`
# must not depend on `anchor.chaos` (the adversarial test rig sits beside
# production code, never inside its import graph — the same boundary
# `tests/boundary/test_stall_injection_not_reachable.py` enforces for
# `anchor.chaos.injections.stall`). A kill is recorded here, server-side,
# because both the console's manual kill button and the harness's kill
# injection go through this one endpoint (D-36) and must be recorded
# identically; every other injection type has no such shared endpoint and
# is recorded by the harness itself via `anchor.chaos.recorder`.
_RECORD_KILL_EVENT_SQL = """
    INSERT INTO chaos_events (chaos_run_id, type, target_worker_id)
    VALUES ($1, 'worker_kill', $2)
    RETURNING id
"""

router = APIRouter()


class WorkersListResponse(BaseModel):
    items: list[WorkerResponse]


class KillRequest(BaseModel):
    graceful: bool = False
    chaos_run_id: int | None = None
    """Set only by `anchor.chaos.injections.kill` (phase 8): associates the
    `chaos_events` row this endpoint writes with the harness run that
    requested it. Omitted (`None`) by every other caller — the console's
    manual kill button included — which is exactly `NULL`,
    "a kill issued manually from the console" (data-model.md §6). Additive
    to the contract documented in `contracts/openapi.yaml`: existing
    callers that never send this field are unaffected.
    """


class KillResponse(BaseModel):
    ok: bool
    worker_id: str
    mode: Literal["hard"]
    chaos_event_id: int


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
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM workers WHERE id = $1)", worker_id
        )
        if not exists:
            raise ApiError(status_code=404, error="worker_not_found", message="worker not found")
        async with conn.transaction():
            await conn.execute("UPDATE workers SET stopped_at = now() WHERE id = $1", worker_id)
            chaos_event_id = await conn.fetchval(
                _RECORD_KILL_EVENT_SQL, body.chaos_run_id, worker_id
            )

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

    return KillResponse(ok=True, worker_id=worker_id, mode="hard", chaos_event_id=chaos_event_id)
