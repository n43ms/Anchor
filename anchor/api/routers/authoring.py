"""`POST /api/authoring/{validate,generate}` (always mounted) and
`POST /api/authoring/register` (local mode only) — plan.md P9.1-P9.7,
contracts/openapi.yaml `/api/authoring/*`.

Two routers, mounted differently, mirroring `anchor.api.routers.config`'s
`router`/`admin_router` split: `router` (`validate`, `generate`) is
available in **both** deployment modes; `admin_router` (`register`) is
mounted only when `ANCHOR_AUTHORING_EXECUTE=true` (`anchor.api.app`) — a
404 in demonstration mode, never a 401 or 403, because there is no
credential that would make the route exist (§27.3, §31.2, FR-112).

Neither handler persists `source` anywhere: it is read from the request
body, passed to `validator.validate` / `register.register_draft`, and
discarded when the response is written. No table, cache key, or
filesystem path in this module holds a draft (§27.5, FR-136).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from anchor.api.authoring.validator import DraftSyntaxError, validate
from anchor.api.errors import ApiError

router = APIRouter()
admin_router = APIRouter()

# anchor.api.authoring.register is deliberately NOT imported at module
# level: `router` (this module) is mounted unconditionally in every
# deployment mode, so a top-level import here would put registry-mutation
# code on an import path that exists regardless of ANCHOR_AUTHORING_EXECUTE
# — exactly what tests/boundary/test_no_import_path_to_registry_mutation.py
# forbids. It is imported lazily, inside register_draft() below, which is
# itself only reachable through admin_router — mounted only when the flag
# is set (anchor.api.app).


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
    `/api/authoring/validate` and the editor keep working (FR-126). This
    is not a stub standing in for a future provider integration — it is
    the complete, correct behaviour of this endpoint in an environment
    that generates nothing, stated once here rather than by a client
    inferring it from a timeout or a generic 500.
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
async def register_draft(body: dict[str, Any]) -> dict[str, Any]:
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
