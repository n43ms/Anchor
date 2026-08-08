"""`GET /api/health` (FR-072).

Fails closed (I7): returns 503 with `database_reachable: false` when
PostgreSQL is unreachable, and never reports a cached healthy state. This
route is deliberately the one place in the API that does not go through
`anchor.core.db.pool.acquire`'s error translation, because a database that
cannot be reached does not raise an anchor SQLSTATE — it raises a
connection-level error, which this handler treats as the health signal
itself rather than an exception to translate.

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

from anchor.core.config.loader import load_runtime_settings
from anchor.core.db.schema_gate import built_against_revision

router = APIRouter()


class HealthReport(BaseModel):
    database_reachable: bool
    worker_count: int
    deployment_mode: str
    degraded: bool
    schema_revision: str | None = None
    global_concurrency_cap: int | None = None
    running_count: int | None = None


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
            running_count = await conn.fetchval(
                "SELECT count(*) FROM runs WHERE status = 'running'"
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
            worker_count=0,
            deployment_mode=deployment_mode,
            degraded=True,
            schema_revision=None,
        )

    schema_mismatch = schema_revision != built_against_revision()
    return HealthReport(
        database_reachable=True,
        worker_count=int(worker_count),
        deployment_mode=deployment_mode,
        degraded=schema_mismatch,
        schema_revision=schema_revision,
        global_concurrency_cap=settings.global_concurrency_cap,
        running_count=int(running_count),
    )
