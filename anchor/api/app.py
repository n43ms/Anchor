"""The FastAPI application factory.

Minimal in phase 0: health only. Phase 1 adds the runs routers and the
typed-error exception handlers (plan.md P1.7, T102); later phases add the
remaining routers named in `anchor/api/routers/__init__.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as redis_asyncio
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from anchor.api.errors import error_body
from anchor.core.config.live import load_live_settings, poll_forever
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
from anchor.core.events.publish import configure_publisher

# Every typed database error this API can surface, mapped to its status
# code and its `contracts/openapi.yaml` `Error.error` machine code (T102).
# LeaseFencedError should never actually reach the API layer — fenced
# writes are a worker-internal concern (I3) — but the mapping exists so a
# bug that lets one leak through fails as a clear 409 rather than an
# unhandled 500.
_ERROR_STATUS_CODES: dict[type[Exception], tuple[int, str]] = {
    LeaseFencedError: (409, "lease_fenced"),
    # "config_assertion_failed" is one of the two machine codes
    # contracts/openapi.yaml names explicitly as an example.
    ConfigAssertionError: (422, "config_assertion_failed"),
    ImmutableRecordError: (409, "immutable_record"),
    ResultOverwriteError: (409, "result_overwrite"),
    PayloadTooLargeError: (413, "payload_too_large"),
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
    app.state.config_profile = env.config_profile.value
    app.state.code_version = env.code_version

    # The API is a publisher (submission, resolve, cancel all append events
    # of their own, P6.3/P6.7) and, via anchor.api.ws.subscriber, the one
    # standing subscriber the console's WebSocket channels demultiplex from
    # in process (D-50). Both roles share this one client.
    redis_client = redis_asyncio.from_url(env.redis_url)
    app.state.redis_client = redis_client
    configure_publisher(redis_client)

    from anchor.api.ws.subscriber import Hub

    app.state.ws_hub = Hub()

    background_tasks: list[asyncio.Task[None]] = []
    app.state.chaos_tasks = set()

    try:
        async with pool.acquire(timeout=5.0) as conn:
            await assert_schema_matches(conn)
    except SchemaVersionMismatchError:
        # Auto-apply Alembic migrations on fresh database boot
        try:
            logger.info("running automatic schema migration to head...")
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "alembic", "-c", "ops/migrations/alembic.ini", "upgrade", "head"
            )
            await proc.wait()
            async with pool.acquire(timeout=5.0) as conn:
                await assert_schema_matches(conn)
        except Exception as exc:
            logger.error("auto-migration failed: %s", exc)
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

    from anchor.api.serializers.rollup import run_rollup_once
    from anchor.api.ws.orphan_watcher import watch_for_orphans
    from anchor.api.ws.subscriber import run_subscriber
    from anchor.chaos.harness import mark_abandoned_chaos_runs

    try:
        async with pool.acquire(timeout=5.0) as conn:
            abandoned = await mark_abandoned_chaos_runs(conn)
        if abandoned:
            logger.warning(
                "marked stale chaos runs abandoned at startup", extra={"count": abandoned}
            )
    except (asyncpg.PostgresError, TimeoutError, OSError) as exc:
        # Same posture as the schema check above: the database being
        # unreachable at boot is not this check's problem to solve, and
        # the API still starts (I7) — a chaos run left `running` with a
        # stale heartbeat is reconciled the next time this succeeds.
        logger.warning("could not check for abandoned chaos runs at startup: %s", exc)

    async def _rollup_forever() -> None:
        # Periodic, never a trigger on the append path (D-49) — see
        # anchor.api.serializers.rollup's module docstring for why.
        while True:
            await asyncio.sleep(10.0)
            try:
                async with pool.acquire() as conn:
                    await run_rollup_once(conn)
            except (asyncpg.PostgresError, OSError, TimeoutError) as exc:
                logger.warning("metrics rollup tick failed", extra={"error": str(exc)})

    try:
        live = None
        async with pool.acquire(timeout=5.0) as conn:
            with contextlib.suppress(asyncpg.PostgresError, TimeoutError, OSError, KeyError):
                live = await load_live_settings(conn)
    except (asyncpg.PostgresError, TimeoutError, OSError):
        live = None

    background_tasks.append(
        asyncio.create_task(run_subscriber(redis_client, app.state), name="ws-redis-subscriber")
    )
    background_tasks.append(
        asyncio.create_task(watch_for_orphans(pool, app.state.ws_hub), name="ws-orphan-watcher")
    )
    background_tasks.append(asyncio.create_task(_rollup_forever(), name="metrics-rollup"))
    if live is not None:
        background_tasks.append(
            asyncio.create_task(
                poll_forever(pool, live, redis_client=redis_client), name="live-config-poll"
            )
        )

    try:
        yield
    finally:
        chaos_tasks: set[asyncio.Task[None]] = app.state.chaos_tasks
        for task in (*background_tasks, *chaos_tasks):
            task.cancel()
        for task in (*background_tasks, *chaos_tasks):
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await redis_client.aclose()
        await pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Anchor", lifespan=lifespan)

    from anchor.api.middleware import log_requests, rate_limit_requests
    from anchor.api.routers import (
        authoring,
        chaos,
        config,
        health,
        observability,
        registry,
        runs,
        workers,
    )
    from anchor.api.ws import fleet as fleet_ws
    from anchor.api.ws import runs as runs_ws
    from anchor.runtime.agents import register_all

    register_all()
    # Order matters: middleware is applied outermost-registered-last, so
    # registering rate limiting after logging means an over-limit request
    # is still logged (T359) before being rejected. CORSMiddleware is added
    # last so it wraps outermost, handling preflights immediately and attaching
    # headers to every response.
    app.middleware("http")(rate_limit_requests)
    app.middleware("http")(log_requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(runs.router)
    app.include_router(workers.router)
    app.include_router(chaos.router)
    app.include_router(registry.router)
    app.include_router(observability.router)
    app.include_router(config.router)
    app.include_router(authoring.router)
    app.include_router(runs_ws.router)
    app.include_router(fleet_ws.router)

    # PATCH /api/config is mounted only in local mode — a 404 in
    # demonstration mode, never a 403 (§31.2, FR-064): see
    # anchor.api.routers.config's module docstring for why that
    # distinction matters. Read the one flag directly from the environment
    # here, at app-construction time, rather than via `BootstrapEnv`
    # (which also requires `database_url`/`redis_url` to be set just to
    # decide which routes exist — a requirement this decision doesn't need
    # and that would make importing this module fail in, e.g., a test
    # process that configures the database only inside a fixture) or from
    # `app.state.deployment_mode` (set inside `lifespan`, which has not run
    # yet when routers are mounted).
    if os.environ.get("ANCHOR_AUTHORING_EXECUTE", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        app.include_router(config.admin_router)
        # POST /api/authoring/register is the RCE boundary named in
        # contracts/openapi.yaml and quickstart.md V11: unmounted in
        # demonstration mode means a 404, not a permission check, and the
        # handler module that imports registry-mutation code
        # (anchor.api.authoring.register) is imported for the first time
        # right here — see that module's docstring for why no import path
        # from an unconditionally-mounted router reaches it.
        app.include_router(authoring.admin_router)

    for error_type, (status_code, error_code) in _ERROR_STATUS_CODES.items():

        def _make_handler(
            code: int, machine_code: str
        ) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
            async def _handler(request: Request, exc: Exception) -> JSONResponse:
                # Every one of these five typed errors carries its own
                # structured attributes (run_id, stale_epoch, relationship,
                # offending_values, ...) beyond the message `str(exc)`
                # already renders — surfaced here as `detail` so a caller
                # can act on the specifics, not just display the sentence.
                detail = {
                    key: value
                    for key, value in vars(exc).items()
                    if not key.startswith("_") and key != "args"
                }
                return JSONResponse(
                    status_code=code,
                    content={"error": machine_code, "message": str(exc), "detail": detail},
                )

            return _handler

        app.add_exception_handler(error_type, _make_handler(status_code, error_code))

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Reshapes every `raise HTTPException(...)` in this codebase into
        `contracts/openapi.yaml`'s `Error` (`{error, message, detail}`) —
        see `anchor.api.errors`'s module docstring for why this is a
        global handler rather than a rewrite of every individual raise
        site. `ApiError` (a `HTTPException` subclass) already carries a
        `{error, message}` dict as `.detail`; a plain `HTTPException` with
        a string `.detail` gets a status-derived default `error` code
        instead.
        """
        if isinstance(exc.detail, dict) and "error" in exc.detail and "message" in exc.detail:
            body = exc.detail
        else:
            body = error_body(exc.status_code, str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """FastAPI's own request-body/query-param validation failures
        raise this, not `HTTPException` — a separate handler is required
        for the same `Error` shape to cover it (contracts/openapi.yaml
        `ValidationError` response).
        """
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "request validation failed",
                "detail": {"errors": exc.errors()},
            },
        )

    return app


app = create_app()
