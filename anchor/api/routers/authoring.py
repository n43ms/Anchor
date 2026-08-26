"""`POST /api/authoring/{validate,generate}` (always mounted) and
`POST /api/authoring/register` (local mode only) — plan.md P9.1-P9.7,
contracts/openapi.yaml `/api/authoring/*`.

Two routers, mounted differently, mirroring `anchor.api.routers.config`'s
`router`/`admin_router` split: `router` (`validate`, `generate`) is
available in **both** deployment modes; `admin_router` (`register`) is
mounted only when `ANCHOR_AUTHORING_EXECUTE=true` (`anchor.api.app`) — a
404 in demonstration mode, never a 401 or 403, because there is no
credential that would make the route exist (§27.3, §31.2, FR-112).
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Request
from redis import asyncio as redis_asyncio

from anchor.api.authoring.validator import DraftSyntaxError, validate
from anchor.api.errors import ApiError

router = APIRouter()
admin_router = APIRouter()


@router.post("/api/authoring/validate")
async def validate_draft(body: dict[str, Any]) -> dict[str, Any]:
    source = body.get("source")
    if not isinstance(source, str):
        raise ApiError(
            status_code=422,
            error="validation_error",
            message="'source' is required and must be a string",
        )
    try:
        report = validate(source)
    except DraftSyntaxError as exc:
        raise ApiError(status_code=422, error="draft_syntax_error", message=str(exc)) from exc
    return report.to_dict()


@router.post("/api/authoring/generate")
async def generate_draft(body: dict[str, Any]) -> dict[str, Any]:
    """Always mounted, in both modes — but this deployment has no LLM
    provider configured (no `ANCHOR_*_API_KEY` exists in `BootstrapEnv`),
    so generation degrades honestly on every call rather than partially
    working: a 503 stating plainly that no provider is configured, while
    `/api/authoring/validate` and the editor keep working (FR-126).
    """
    del body
    raise ApiError(
        status_code=503,
        error="generation_unavailable",
        message=(
            "no generation provider is configured for this deployment; the editor and "
            "/api/authoring/validate remain fully available — generation happens at "
            "authoring time, on text a human then reviews, and its absence here does not "
            "affect anything a run depends on"
        ),
    )


@admin_router.post("/api/authoring/register", status_code=201)
async def register_draft(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    from anchor.api.authoring.register import (
        RegistrationShapeError,
        RegistrationValidationError,
    )
    from anchor.api.authoring.register import register_draft as _register_draft

    source = body.get("source")
    agent_type = body.get("agent_type")
    if not isinstance(source, str) or not isinstance(agent_type, str) or not agent_type:
        raise ApiError(
            status_code=422,
            error="validation_error",
            message="'source' and 'agent_type' are required and must be non-empty strings",
        )
    try:
        redis_client = getattr(request.app.state, "redis_client", None)
        if redis_client is not None:
            await redis_client.set(f"anchor:authoring:draft:{agent_type}", source)
        else:
            redis_url = os.getenv("ANCHOR_REDIS_URL", "redis://redis:6379/0")
            r_client = redis_asyncio.from_url(redis_url)
            try:
                await r_client.set(f"anchor:authoring:draft:{agent_type}", source)
            finally:
                await r_client.aclose()
    except Exception as e:
        import sys
        sys.stderr.write(f"[REDIS DRAFT ERROR] {e}\n")

    try:
        return _register_draft(source, agent_type)
    except DraftSyntaxError as exc:
        raise ApiError(status_code=422, error="draft_syntax_error", message=str(exc)) from exc
    except RegistrationValidationError as exc:
        raise ApiError(
            status_code=422,
            error="validation_error",
            message=str(exc),
            detail=exc.report.to_dict(),
        ) from exc
    except RegistrationShapeError as exc:
        raise ApiError(status_code=422, error="validation_error", message=str(exc)) from exc
