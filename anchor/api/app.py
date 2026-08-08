"""The FastAPI application factory.

Minimal in phase 0: health only. Phase 1 adds the runs routers and the
typed-error exception handlers (plan.md P1.7, T102); later phases add the
remaining routers named in `anchor/api/routers/__init__.py`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from anchor.core.config.loader import BootstrapEnv
from anchor.core.db.pool import create_pool
from anchor.core.db.schema_gate import assert_schema_matches


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    env = BootstrapEnv()
    pool = await create_pool(env.database_url)
    app.state.db_pool = pool
    app.state.deployment_mode = "local" if env.authoring_execute else "demonstration"

    async with pool.acquire() as conn:
        await assert_schema_matches(conn)

    try:
        yield
    finally:
        await pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Anchor", lifespan=lifespan)

    from anchor.api.routers import health

    app.include_router(health.router)
    return app


app = create_app()
