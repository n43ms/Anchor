"""`GET /api/tools` and `GET /api/agents` — the declared registries (plan.md
P5.5/T272, P6.11/T370; FR-120).

Read-only. Tools come from `tool_registry`, written by `register_tool` at
worker startup; agents come from `anchor.runtime.agents.registry`, an
in-process dict populated by `register_all()` at API/worker startup —
there is no database table for agent contracts, because the contract is a
property of the code deployed, not of any run.
"""

from __future__ import annotations

from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends, Request

from anchor.runtime.agents.registry import list_agents

router = APIRouter()


async def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


@router.get("/api/agents")
async def get_agents() -> dict[str, Any]:
    items = [
        {
            "agent_type": a.agent_type,
            "description": a.description,
            "contract_version": a.contract_version,
            "expected_step_count": a.expected_step_count,
            "tools_used": list(a.tools_used),
            "stubbed_model": a.stubbed_model,
        }
        for a in list_agents()
    ]
    return {"items": items}


@router.get("/api/tools")
async def list_tools(pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> dict[str, Any]:
    """`contracts/openapi.yaml` -> `ToolDescriptor`: declared category,
    reconciler presence, conflict state, and last-used timestamp.

    `executable` is `false` exactly when `conflict_at IS NOT NULL` — a
    fleet-wide declaration disagreement refuses the tool for execution
    everywhere until an operator resolves it (data-model.md §4), and the
    console must be able to say so without inferring it from two other
    fields.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT name, safety, naturally_idempotent, provider_accepts_key, has_reconcile_fn,
                   default_policy, declaration_hash, declared_by_version,
                   conflict_at, conflict_version, description, last_used_at
            FROM tool_registry
            ORDER BY name
            """
        )

    items = [
        {
            "name": r["name"],
            "safety": r["safety"],
            "naturally_idempotent": r["naturally_idempotent"],
            "provider_accepts_key": r["provider_accepts_key"],
            "has_reconcile_fn": r["has_reconcile_fn"],
            "default_policy": r["default_policy"],
            "declaration_hash": r["declaration_hash"],
            "declared_by_version": r["declared_by_version"],
            "executable": r["conflict_at"] is None,
            "conflict": (
                {
                    "detected_at": r["conflict_at"].isoformat(),
                    "versions": [r["declared_by_version"], r["conflict_version"]],
                }
                if r["conflict_at"] is not None
                else None
            ),
            "description": r["description"],
            "last_used_at": r["last_used_at"].isoformat() if r["last_used_at"] else None,
        }
        for r in rows
    ]
    return {"items": items}
