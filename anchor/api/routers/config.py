"""`GET`/`PATCH /api/config` (plan.md P6.6, T333-T335; FR-063, FR-064;
contracts/openapi.yaml `RuntimeConfig`).

Two routers, mounted differently: `router` (`GET`, read-only) is available
in every deployment mode; `admin_router` (`PATCH`) is mounted only in local
mode (`anchor.api.app`) — a 404 in demonstration mode, never a 403.
**This is an availability restriction, not a security boundary** (§31.2):
Anchor has no accounts, no sessions, no per-user identity anywhere
(FR-114), so there is no principal a 403 could meaningfully be denying.
Conflating "not reachable in this deployment" with "you are not allowed"
would invite exactly the kind of auth-shaped thinking §21.7 cuts for good
reasons that have not changed. `RuntimeConfig.editable` still reports this
honestly to a `GET` caller in either mode, so the console can grey out the
edit affordance rather than let an operator discover the 404 by trying.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError

from anchor.api.errors import ApiError
from anchor.core.config.live import publish_config_changed
from anchor.core.config.loader import load_runtime_settings
from anchor.core.config.settings import RuntimeSettings

router = APIRouter()
admin_router = APIRouter()

# contracts/openapi.yaml `RuntimeConfig.assertions` — the three
# relationships checked before any change is applied (FR-060), reported
# verbatim rather than re-derived from the checker's own code, since these
# strings are documentation for a human reading the response, not input to
# anything.
_ASSERTIONS = (
    "lease_duration_ms >= 4 * renewal_interval_ms",
    "margin_ms == lease_duration_ms - renewal_interval_ms",
    "step_timeout_ms > 0",
)


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


async def _read_version(conn: asyncpg.Connection[Any]) -> int:
    value = await conn.fetchval("SELECT max(version) FROM runtime_config")
    return int(value) if value is not None else 1


def _report(
    *, settings: RuntimeSettings, version: int, active_profile: str, editable: bool
) -> dict[str, Any]:
    return {
        "version": version,
        "active_profile": active_profile,
        "editable": editable,
        "values": settings.model_dump(),
        "assertions": list(_ASSERTIONS),
    }


@router.get("/api/config")
async def get_config(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)], request: Request
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        settings = await load_runtime_settings(conn)
        version = await _read_version(conn)
    active_profile: str = getattr(request.app.state, "config_profile", "unknown")
    editable = request.app.state.deployment_mode == "local"
    return _report(
        settings=settings, version=version, active_profile=active_profile, editable=editable
    )


@admin_router.patch("/api/config")
async def patch_config(
    body: dict[str, Any],
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    request: Request,
) -> dict[str, Any]:
    """`requestBody` is a flat, partial object of `runtime_config` keys
    (`contracts/openapi.yaml`: `additionalProperties: true`, example
    `{"lease_duration_ms": 20000, "renewal_interval_ms": 5000}`) — not
    wrapped in an envelope key, since every property of this object *is*
    a `runtime_config` key by construction (unknown keys are rejected
    below).

    Re-runs the three-part assertion (`RuntimeSettings.assert_relationships`)
    before writing anything, and **rejects the change, never the fleet**
    (FR-063): a violating `PATCH` returns 422 naming the relationship and
    both offending values, and `runtime_config` is left exactly as it was —
    matched, as a backstop, by the `runtime_config_assert` trigger
    (migration 001), which would raise `AN002` on the write itself if this
    application-level check were ever bypassed.
    """
    async with pool.acquire() as conn:
        current = await load_runtime_settings(conn)
        merged = current.model_dump()
        unknown = sorted(set(body) - set(merged))
        if unknown:
            raise ApiError(
                status_code=422,
                error="unknown_config_key",
                message=f"unknown configuration key(s): {unknown}",
            )
        merged.update(body)

        try:
            candidate = RuntimeSettings.model_validate(merged)
        except ValidationError as exc:
            raise ApiError(status_code=422, error="validation_error", message=str(exc)) from exc
        # Deliberately not caught here: ConfigAssertionError propagates to
        # the typed-error handler registered in anchor.api.app, which
        # already knows to report it as `error: "config_assertion_failed"`
        # — one of contracts/openapi.yaml's two explicit `Error.error`
        # examples — carrying `relationship` and `offending_values` in
        # `detail` straight from the exception's own attributes, rather
        # than this route re-deriving a second, possibly-drifting message.
        candidate.assert_relationships()

        async with conn.transaction():
            for key, value in body.items():
                await conn.execute(
                    """
                    INSERT INTO runtime_config (key, value, version, updated_at, updated_by)
                    VALUES ($1, $2::jsonb, 1, now(), 'operator')
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        version = runtime_config.version + 1,
                        updated_at = now(),
                        updated_by = 'operator'
                    """,
                    key,
                    json.dumps(value),
                )

        version = await _read_version(conn)

    redis_client = getattr(request.app.state, "redis_client", None)
    await publish_config_changed(redis_client)

    active_profile: str = getattr(request.app.state, "config_profile", "unknown")
    return _report(
        settings=candidate, version=version, active_profile=active_profile, editable=True
    )
