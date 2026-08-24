"""T098 — `GET /api/runs` paginates on an opaque keyset cursor over
`(created_at, id)`, newest first, rather than an offset."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from anchor.api.routers.runs import list_runs
from anchor.core.events.append import append
from anchor.core.events.types import EventType


@pytest.mark.asyncio
async def test_list_runs_pages_forward_with_no_gaps_or_repeats(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE runs RESTART IDENTITY CASCADE")
        ids = []
        for _ in range(7):
            run_id = await conn.fetchval(
                "INSERT INTO runs (agent_type) VALUES ('demo_minimal') RETURNING id"
            )
            await append(
                conn,
                run_id=run_id,
                type=EventType.RUN_SUBMITTED,
                payload={
                    "agent_type": "demo_minimal",
                    "input": {},
                    "is_demo": True,
                    "client_request_key": None,
                    "chaos_run_id": None,
                },
                epoch=0,
                worker_id="api",
                max_payload_bytes=1_000_000,
            )
            ids.append(run_id)
            # created_at has second-level meaning only insofar as ordering
            # matters; a tiny sleep keeps timestamps from tying so the
            # (created_at, id) keyset is exercised on both columns.
            await asyncio.sleep(0.001)

    seen: list[int] = []
    cursor: str | None = None
    for _ in range(10):
        page = await list_runs(db_pool, limit=3, cursor=cursor)
        seen.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break

    assert seen == sorted(ids, reverse=True)
