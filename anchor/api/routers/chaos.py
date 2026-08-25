"""`POST /api/chaos/start`, `GET /api/chaos`, `GET /api/chaos/latest`,
`GET /api/chaos/{chaos_run_id}/report` (plan.md P8.6, T517-T520).

**Bounded per deployment mode, never withheld** (FR-116, §31): demonstration
mode caps `worker_count` and `duration_seconds`; local mode does not. The
two bounds are module constants, not `runtime_config` keys, for the same
reason `anchor.api.middleware`'s rate-limit constants are — API-tier-only,
no correctness invariant depends on them, and `runtime_config` seeds
exactly fifteen keys (data-model.md §9).

The harness itself runs as a background `asyncio.Task` on this process's
own event loop, driving the system through an **ASGI-transport** HTTP
client — a real client issuing real HTTP requests against this exact app,
serialized and routed exactly as an external caller's would be, just
without opening a socket to reach itself (`anchor.chaos.harness.build_http_client`).
This is the same function the scheduled CI job calls with a real
network client instead (D-36): one implementation, two transports.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

import asyncpg
import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from anchor.api.errors import ApiError
from anchor.api.serializers.chaos import (
    CHAOS_REPORT_COLUMNS,
    CHAOS_RUN_COLUMNS,
    ChaosReportResponse,
    ChaosRunResponse,
    serialize_chaos_report,
    serialize_chaos_run,
)
from anchor.chaos.harness import ChaosConfig, build_http_client, create_chaos_run, run_harness
from anchor.core.config.live import load_live_settings

router = APIRouter()
logger = logging.getLogger(__name__)

# FR-116: cap the parameters, not the capability. Matched to the compose
# fleet size (3 always-on workers) and a two-minute run — long enough to
# show kills, recovery, and the invariant panel filling in; short enough
# that a shared public instance isn't monopolized by one visitor's run.
CHAOS_MAX_WORKER_COUNT_DEMO = 3
CHAOS_MAX_DURATION_SECONDS_DEMO = 120


class ChaosStartRequest(BaseModel):
    worker_count: int = Field(gt=0)
    duration_seconds: int = Field(ge=10)
    run_count: int = Field(default=10, gt=0)
    kill_rate_per_minute: float = Field(default=0.0, ge=0)
    latency_injection_ms: int = Field(default=0, ge=0)
    stall_injection_rate: float = Field(default=0.0, ge=0, le=1)
    tool_failure_rate: float = Field(default=0.0, ge=0, le=1)
    uncertainty_crash_rate: float = Field(default=0.0, ge=0, le=1)
    step_mix: dict[str, int] | None = None


class ChaosHistoryItem(ChaosRunResponse):
    """`contracts/openapi.yaml`'s `GET /api/chaos` item is `allOf: [ChaosRun,
    {report}]` — a flat merge, `report` alongside the run's own fields, not
    a `{run, report}` wrapper. Subclassing `ChaosRunResponse` is what
    produces that exact shape.
    """

    report: ChaosReportResponse | None = None


class ChaosHistoryResponse(BaseModel):
    items: list[ChaosHistoryItem]


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


async def _fetch_report_row(
    conn: asyncpg.Connection[Any], chaos_run_id: int
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        f"""
        SELECT {CHAOS_REPORT_COLUMNS}
        FROM chaos_reports cr
        JOIN chaos_runs run ON run.id = cr.chaos_run_id
        WHERE cr.chaos_run_id = $1
        """,
        chaos_run_id,
    )


def check_demo_bounds(deployment_mode: str, *, worker_count: int, duration_seconds: int) -> None:
    """FR-116: cap the parameters, not the capability. A pure, standalone
    function so the bound logic is testable without spinning up a real
    chaos run (which `POST /api/chaos/start` does immediately after this
    check passes) — `tests/boundary/test_chaos_bounded_in_demo_mode.py`
    exercises this directly for the "bounds do not apply outside
    demonstration mode" case for exactly that reason.
    """
    if deployment_mode != "demonstration":
        return
    if worker_count > CHAOS_MAX_WORKER_COUNT_DEMO:
        raise ApiError(
            status_code=422,
            error="chaos_bounds_exceeded",
            message=f"worker_count exceeds the demonstration-mode bound of "
            f"{CHAOS_MAX_WORKER_COUNT_DEMO}",
        )
    if duration_seconds > CHAOS_MAX_DURATION_SECONDS_DEMO:
        raise ApiError(
            status_code=422,
            error="chaos_bounds_exceeded",
            message=f"duration_seconds exceeds the demonstration-mode bound of "
            f"{CHAOS_MAX_DURATION_SECONDS_DEMO}",
        )


@router.post("/api/chaos/start", response_model=ChaosRunResponse, status_code=202)
async def start_chaos(
    body: ChaosStartRequest,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    request: Request,
) -> ChaosRunResponse:
    deployment_mode: str = request.app.state.deployment_mode
    check_demo_bounds(
        deployment_mode, worker_count=body.worker_count, duration_seconds=body.duration_seconds
    )

    config = ChaosConfig(
        worker_count=body.worker_count,
        duration_seconds=body.duration_seconds,
        run_count=body.run_count,
        kill_rate_per_minute=body.kill_rate_per_minute,
        latency_injection_ms=body.latency_injection_ms,
        stall_injection_rate=body.stall_injection_rate,
        tool_failure_rate=body.tool_failure_rate,
        uncertainty_crash_rate=body.uncertainty_crash_rate,
        step_mix=body.step_mix,
    )

    async with pool.acquire() as conn:
        settings = await load_live_settings(conn)

    chaos_run_id = await create_chaos_run(
        pool,
        config=config,
        deployment_mode=deployment_mode,
        config_profile=request.app.state.config_profile,
        lease_duration_ms=settings.current.lease_duration_ms,
        renewal_interval_ms=settings.current.renewal_interval_ms,
    )

    client = build_http_client(
        "http://chaos-harness.internal",
        transport=httpx.ASGITransport(app=request.app),
    )

    async def _run() -> None:
        try:
            async with client:
                await run_harness(
                    pool,
                    chaos_run_id=chaos_run_id,
                    client=client,
                    config=config,
                    lease_duration_ms=settings.current.lease_duration_ms,
                    live=settings,
                    code_version=request.app.state.code_version,
                )
        except Exception:
            logger.exception("chaos harness run failed", extra={"chaos_run_id": chaos_run_id})

    task = asyncio.create_task(_run(), name="chaos-harness-run")
    chaos_tasks: set[asyncio.Task[None]] = request.app.state.chaos_tasks
    chaos_tasks.add(task)
    task.add_done_callback(chaos_tasks.discard)

    async with pool.acquire() as conn:
        run_row = await conn.fetchrow(
            f"SELECT {CHAOS_RUN_COLUMNS} FROM chaos_runs WHERE id = $1", chaos_run_id
        )
        assert run_row is not None
        return serialize_chaos_run(run_row)


@router.get("/api/chaos", response_model=ChaosHistoryResponse)
async def list_chaos_runs(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)], limit: int = 25
) -> ChaosHistoryResponse:
    page_size = min(max(limit, 1), 100)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT {CHAOS_RUN_COLUMNS} FROM chaos_runs ORDER BY started_at DESC LIMIT $1",
            page_size,
        )
        items = []
        for row in rows:
            report_row = await _fetch_report_row(conn, row["id"])
            items.append(
                ChaosHistoryItem(
                    **serialize_chaos_run(row).model_dump(),
                    report=serialize_chaos_report(report_row) if report_row is not None else None,
                )
            )
    return ChaosHistoryResponse(items=items)


@router.get("/api/chaos/latest", response_model=ChaosReportResponse)
async def latest_chaos_report(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> ChaosReportResponse:
    """Read by the landing page's evidence band and the live evidence badge.
    404 when no report exists — the badge is absent, never a placeholder
    (FR-104, SC-017, constitution Principle VIII).
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            SELECT {CHAOS_REPORT_COLUMNS}
            FROM chaos_reports cr
            JOIN chaos_runs run ON run.id = cr.chaos_run_id
            ORDER BY cr.created_at DESC
            LIMIT 1
            """
        )
    if row is None:
        raise ApiError(
            status_code=404, error="no_chaos_report", message="no completed chaos run yet"
        )
    return serialize_chaos_report(row)


@router.get("/api/chaos/{chaos_run_id}/report", response_model=ChaosReportResponse)
async def get_chaos_report(
    chaos_run_id: int, pool: Annotated[asyncpg.Pool, Depends(get_pool)]
) -> ChaosReportResponse:
    async with pool.acquire() as conn:
        run_exists = await conn.fetchval("SELECT 1 FROM chaos_runs WHERE id = $1", chaos_run_id)
        if not run_exists:
            raise ApiError(
                status_code=404, error="chaos_run_not_found", message="chaos run not found"
            )
        report_row = await _fetch_report_row(conn, chaos_run_id)
    if report_row is None:
        raise ApiError(
            status_code=409,
            error="chaos_run_not_completed",
            message="chaos run has not completed; no report exists yet",
        )
    return serialize_chaos_report(report_row)
