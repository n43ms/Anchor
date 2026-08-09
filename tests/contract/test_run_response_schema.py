"""T101 — every `Run` response validates against `contracts/openapi.yaml`'s
`Run` schema: every field the schema requires is present, with the type the
schema declares.
"""

from __future__ import annotations

import asyncpg
import pytest

from anchor.api.serializers.runs import RUN_COLUMNS, serialize_run

# contracts/openapi.yaml -> components.schemas.Run.required
_OPENAPI_RUN_REQUIRED = ("id", "agent_type", "status", "epoch", "created_at", "is_demo")

# contracts/openapi.yaml -> components.schemas.Run.properties, by declared type.
_OPENAPI_RUN_PROPERTY_TYPES: dict[str, type | tuple[type, ...]] = {
    "id": int,
    "display_id": str,
    "agent_type": str,
    "status": str,
    "epoch": int,
    "owner_worker_id": (str, type(None)),
    "lease_expires_at": (str, type(None)),
    "orphaned": bool,
    "current_step_index": (int, type(None)),
    "attempts": int,
    "priority": int,
    "is_demo": bool,
    "cancel_requested_at": (str, type(None)),
    "created_at": str,
    "claimed_at": (str, type(None)),
    "finished_at": (str, type(None)),
}


@pytest.mark.asyncio
async def test_serialize_run_matches_the_openapi_run_schema(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await conn.fetchval(
            "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
        )
        row = await conn.fetchrow(f"SELECT {RUN_COLUMNS} FROM runs WHERE id = $1", run_id)
        assert row is not None

    body = serialize_run(row).model_dump()

    for field in _OPENAPI_RUN_REQUIRED:
        assert field in body, f"Run schema requires {field!r}, missing from the response"

    for field, expected_type in _OPENAPI_RUN_PROPERTY_TYPES.items():
        if field not in body:
            continue
        assert isinstance(body[field], expected_type), (
            f"{field}={body[field]!r} does not match the openapi.yaml Run schema type "
            f"{expected_type!r}"
        )
