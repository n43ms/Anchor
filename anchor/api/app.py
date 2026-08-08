"""The FastAPI application factory.

Minimal in phase 0: health only. Phase 1 adds the runs routers and the
typed-error exception handlers (plan.md P1.7, T102); later phases add the
remaining routers named in `anchor/api/routers/__init__.py`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from anchor.core.config.loader import BootstrapEnv
from anchor.core.db.errors import (
    ConfigAssertionError,
    ImmutableRecordError,
    LeaseFencedError,
    PayloadTooLargeError,
    ResultOverwriteError,
)
from anchor.core.db.pool import create_pool
from anchor.core.db.schema_gate import SchemaVersionMismatchError, assert_schema_matches

# Every typed database error this API can surface, mapped to the status
# code that names the problem for a caller (T102). LeaseFencedError should
# never actually reach the API layer — fenced writes are a worker-internal
# concern (I3) — but the mapping exists so a bug that lets one leak through
# fails as a clear 409 rather than an unhandled 500.
_ERROR_STATUS_CODES: dict[type[Exception], int] = {
    LeaseFencedError: 409,
    ConfigAssertionError: 400,
    ImmutableRecordError: 409,
    ResultOverwriteError: 409,
    PayloadTooLargeError: 413,
}

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # database_url and redis_url are required fields with no Python-level
    # default because they must always come from the environment
    # (ANCHOR_DATABASE_URL / ANCHOR_REDIS_URL) — mypy cannot see
    # pydantic-settings' env-sourcing, so it reads this as a missing
    # argument. It is not: BaseSettings.__init__ populates required fields
    # from the environment at runtime, and raises its own clear
    # ValidationError if they are genuinely absent.
    env = BootstrapEnv()  # type: ignore[call-arg]
    pool = await create_pool(env.database_url)
    app.state.db_pool = pool
    app.state.deployment_mode = "local" if env.authoring_execute else "demonstration"

    try:
        async with pool.acquire(timeout=5.0) as conn:
            await assert_schema_matches(conn)
    except SchemaVersionMismatchError:
        # A real, actionable misconfiguration — the applied schema and the
        # code disagree. Retrying without an operator noticing would only
        # hide the problem, so this is the one case the process actually
        # refuses to start over (D-45, FR-128).
        raise
    except (asyncpg.PostgresError, TimeoutError, OSError) as exc:
        # The database is unreachable, not merely mismatched — a different
        # failure with a different correct response. Per I7, the API still
        # starts: GET /api/health must be reachable in order to REPORT the
        # outage as 503, which it cannot do if the process never boots.
        # health.py re-derives the schema comparison on every request once
        # the database is reachable, so a mismatch discovered later is
        # still surfaced as `degraded`, just later than at boot.
        logger.warning("database unreachable at startup; starting in a degraded state: %s", exc)

    try:
        yield
    finally:
        await pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Anchor", lifespan=lifespan)

    from anchor.api.middleware import log_requests
    from anchor.api.routers import health, runs
    from anchor.runtime.agents import register_all

    register_all()
    app.middleware("http")(log_requests)
    app.include_router(health.router)
    app.include_router(runs.router)

    for error_type, status_code in _ERROR_STATUS_CODES.items():

        def _make_handler(code: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
            async def _handler(request: Request, exc: Exception) -> JSONResponse:
                return JSONResponse(status_code=code, content={"detail": str(exc)})

            return _handler

        app.add_exception_handler(error_type, _make_handler(status_code))

    return app


app = create_app()
