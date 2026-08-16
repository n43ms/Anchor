"""`GET /api/health` (FR-072; contracts/openapi.yaml `Health`).

Fails closed (I7): returns 503 with `database_reachable: false` when
PostgreSQL is unreachable, and never reports a cached healthy state. This
route is deliberately the one place in the API that does not go through
`anchor.core.db.pool.acquire`'s error translation for the database check,
because a database that cannot be reached does not raise an anchor
SQLSTATE — it raises a connection-level error, which this handler treats
as the health signal itself rather than an exception to translate.

`redis_reachable` is checked and reported honestly but never gates the 503
— Redis is non-authoritative display/fan-out only (FR-058); its absence
degrades the console to polling and is reported as such, not as an outage.

Also re-derives the schema-version comparison on every call (cheap: the
"built against" side is a local file read, no I/O to the database beyond
one already-open query). This is what surfaces a schema mismatch as
`degraded` even in the one case the startup gate couldn't refuse to start
over it — the database was unreachable at boot and became reachable, but
mismatched, afterward (see anchor/api/app.py's lifespan).
"""

from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from anchor.api.serializers.workers import STALE_AFTER_SECONDS
from anchor.core.config.loader import load_runtime_settings
from anchor.core.db.schema_gate import built_against_revision

router = APIRouter()


class HealthReport(BaseModel):
    database_reachable: bool
    redis_reachable: bool
    worker_count: int
    deployment_mode: str
    healthy_worker_count: int | None = None
    stale_worker_count: int | None = None
    pending_run_count: int | None = None
    running_run_count: int | None = None
    global_concurrency_cap: int | None = None
    oldest_pending_age_ms: int | None = None
    active_profile: str | None = None
    code_version: str | None = None
    schema_revision: str | None = None
    degraded: bool = False


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


async def _check_redis(request: Request) -> bool:
    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is None:
        return False
    try:
        await redis_client.ping()
        return True
    except (OSError, TimeoutError):
        return False


@router.get("/api/health", response_model=HealthReport)
async def health(
    request: Request,
    response: Response,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> HealthReport:
    deployment_mode: str = request.app.state.deployment_mode
    redis_reachable = await _check_redis(request)

    try:
        async with pool.acquire(timeout=2.0) as conn:
            worker_rows = await conn.fetch(
                f"""
                SELECT
                    count(*) AS worker_count,
                    count(*) FILTER (
                        WHERE now() - last_seen_at <= interval '{STALE_AFTER_SECONDS} seconds'
                    ) AS healthy_worker_count,
                    count(*) FILTER (
                        WHERE now() - last_seen_at > interval '{STALE_AFTER_SECONDS} seconds'
                    ) AS stale_worker_count
                FROM workers
                WHERE stopped_at IS NULL
                """
            )
            worker_row = worker_rows[0]
            schema_revision: str | None = await conn.fetchval(
                "SELECT version_num FROM alembic_version"
            )
            run_counts = await conn.fetchrow(
                """
                SELECT
                    count(*) FILTER (WHERE status = 'pending') AS pending_run_count,
                    count(*) FILTER (WHERE status = 'running') AS running_run_count,
                    (
                        SELECT EXTRACT(EPOCH FROM (now() - min(created_at))) * 1000
                        FROM runs WHERE status = 'pending'
                    ) AS oldest_pending_age_ms
                FROM runs
                """
            )
            # Reported here, not enforced: the cap is enforced inside the
            # claim statement itself, from phase 3 onward (D-44). A cap
            # applied at submission would enforce nothing and contradict
            # "new runs stay pending."
            settings = await load_runtime_settings(conn)
    except (asyncpg.PostgresError, TimeoutError, OSError):
        response.status_code = 503
        return HealthReport(
            database_reachable=False,
            redis_reachable=redis_reachable,
            worker_count=0,
            deployment_mode=deployment_mode,
            degraded=True,
            schema_revision=None,
        )

    schema_mismatch = schema_revision != built_against_revision()
    # "Below its expected complement" (contracts/openapi.yaml): a schema
    # mismatch or zero live workers, never Redis — Redis is explicitly
    # non-authoritative and reported through its own `redis_reachable`
    # field instead, so a display-only outage never flips this badge
    # (FR-058).
    degraded = schema_mismatch or worker_row["worker_count"] == 0
    active_profile: str = getattr(request.app.state, "config_profile", "unknown")
    oldest_pending_age_ms = run_counts["oldest_pending_age_ms"]

    return HealthReport(
        database_reachable=True,
        redis_reachable=redis_reachable,
        worker_count=int(worker_row["worker_count"]),
        healthy_worker_count=int(worker_row["healthy_worker_count"]),
        stale_worker_count=int(worker_row["stale_worker_count"]),
        pending_run_count=int(run_counts["pending_run_count"]),
        running_run_count=int(run_counts["running_run_count"]),
        oldest_pending_age_ms=int(oldest_pending_age_ms)
        if oldest_pending_age_ms is not None
        else None,
        deployment_mode=deployment_mode,
        active_profile=active_profile,
        schema_revision=schema_revision,
        degraded=degraded,
        global_concurrency_cap=settings.global_concurrency_cap,
        code_version=getattr(request.app.state, "code_version", None),
    )
