"""`Run` response serialization (plan.md P1.7, T101).

Kept separate from `anchor/api/routers/runs.py` so the shape a caller
receives — exactly `contracts/openapi.yaml`'s `Run` schema — is defined once
and reused by every route that returns a run (`get_run`, `list_runs`, and
the dedupe path of `submit_run`), rather than re-assembled per route.
"""

from __future__ import annotations

from typing import Any

import asyncpg
from pydantic import BaseModel

from anchor.api.serializers.timeline import RunSummary, TimelineSegment

# Every column `RunResponse` needs, plus `orphaned` derived in SQL rather
# than in Python: `status = 'running' AND lease_expires_at < now()` reads
# the database clock (I5), never a worker's or the API process's own clock.
# Storing `orphaned` would require a writer at the exact moment nobody owns
# the run (data-model.md §12), so it is computed on every read instead.
RUN_COLUMNS = """
    id, agent_type, status, epoch, owner_worker_id, lease_expires_at,
    priority, attempts, is_demo, cancel_requested_at, created_at,
    claimed_at, finished_at,
    (status = 'running' AND lease_expires_at < now()) AS orphaned
"""


class RunResponse(BaseModel):
    """`contracts/openapi.yaml` -> `components.schemas.Run`."""

    id: int
    display_id: str
    agent_type: str
    status: str
    epoch: int
    owner_worker_id: str | None
    lease_expires_at: str | None
    orphaned: bool
    priority: int
    attempts: int
    is_demo: bool
    cancel_requested_at: str | None
    created_at: str
    claimed_at: str | None
    finished_at: str | None
    needs_review: dict[str, Any] | None = None


def serialize_run(
    row: asyncpg.Record, *, needs_review: dict[str, Any] | None = None
) -> RunResponse:
    """Build a `RunResponse` from a row selected with `RUN_COLUMNS`.

    `needs_review` is supplied by the caller (`get_run`, `list_runs`) only
    for rows whose status is `needs_review` — the specific ambiguous call,
    its declared policy, and the available resolutions (T282), read from
    the most recent `RUN_NEEDS_REVIEW` event rather than re-derived here.
    """
    return RunResponse(
        id=row["id"],
        display_id=f"run_{row['id']}",
        agent_type=row["agent_type"],
        status=row["status"],
        epoch=row["epoch"],
        owner_worker_id=row["owner_worker_id"],
        lease_expires_at=row["lease_expires_at"].isoformat() if row["lease_expires_at"] else None,
        orphaned=row["orphaned"],
        priority=row["priority"],
        attempts=row["attempts"],
        is_demo=row["is_demo"],
        cancel_requested_at=(
            row["cancel_requested_at"].isoformat() if row["cancel_requested_at"] else None
        ),
        created_at=row["created_at"].isoformat(),
        claimed_at=row["claimed_at"].isoformat() if row["claimed_at"] else None,
        finished_at=row["finished_at"].isoformat() if row["finished_at"] else None,
        needs_review=needs_review,
    )


class RunListItemResponse(RunResponse):
    """`contracts/openapi.yaml` -> `RunListItem` (`Run` plus the thread
    summary a list row's compact strand renders from — `GET /api/runs`'s
    own contract, distinct from `RunResponse`, which every *other* runs
    route returns).
    """

    elapsed_ms: int
    segments: list[TimelineSegment]
    summary: RunSummary


def serialize_run_list_item(
    row: asyncpg.Record,
    *,
    db_now: Any,
    segments: list[TimelineSegment],
    summary: RunSummary,
    needs_review: dict[str, Any] | None = None,
) -> RunListItemResponse:
    """`db_now` is one `SELECT now()` the caller reads once per page — the
    database clock, never a worker's or the API process's own (`I5`) — used
    as the "elapsed so far" reference for a still-`running` row; a
    finished row uses its own `finished_at` instead.
    """
    base = serialize_run(row, needs_review=needs_review)
    finished_at = row["finished_at"] or db_now
    elapsed_ms = int((finished_at - row["created_at"]).total_seconds() * 1000)
    return RunListItemResponse(
        **base.model_dump(), elapsed_ms=elapsed_ms, segments=segments, summary=summary
    )
