"""`GET /api/health` (FR-072).

Fails closed (I7): returns 503 with `database_reachable: false` when
PostgreSQL is unreachable, and never reports a cached healthy state. This
route is deliberately the one place in the API that does not go through
`anchor.core.db.pool.acquire`'s error translation, because a database that
cannot be reached does not raise an anchor SQLSTATE — it raises a
connection-level error, which this handler treats as the health signal
itself rather than an exception to translate.
"""

from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

router = APIRouter()


class HealthReport(BaseModel):
    database_reachable: bool
    worker_count: int
    deployment_mode: str
    degraded: bool
    schema_revision: str | None = None


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


@router.get("/api/health", response_model=HealthReport)
async def health(
    request: Request,
    response: Response,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> HealthReport:
    deployment_mode: str = request.app.state.deployment_mode

    try:
        async with pool.acquire(timeout=2.0) as conn:
            worker_count = await conn.fetchval(
                "SELECT count(*) FROM workers WHERE stopped_at IS NULL"
            )
            schema_revision: str | None = await conn.fetchval(
                "SELECT version_num FROM alembic_version"
            )
    except (asyncpg.PostgresError, TimeoutError, OSError):
        response.status_code = 503
        return HealthReport(
            database_reachable=False,
            worker_count=0,
            deployment_mode=deployment_mode,
            degraded=True,
            schema_revision=None,
        )

    return HealthReport(
        database_reachable=True,
        worker_count=int(worker_count),
        deployment_mode=deployment_mode,
        degraded=False,
        schema_revision=schema_revision,
    )
