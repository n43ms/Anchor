"""`Worker` response serialization (plan.md P3.6, T176-T177).

Kept separate from `anchor/api/routers/workers.py`, matching the `runs`
serializer's convention, so the shape a caller receives — the
`contracts/openapi.yaml` `Worker` schema — is defined once.
"""

from __future__ import annotations

import asyncpg
from pydantic import BaseModel

# `stale` is derived here, in SQL, against the database clock (I5) — never
# computed in Python against a worker's or the API process's own clock,
# for the same reason `orphaned` is derived in `serializers/runs.py`.
# Threshold: 3x the heartbeat interval (15s), the same "tolerate a few
# missed beats before calling it dead" shape as the lease/renewal
# relationship, chosen because no numeric threshold is specified anywhere
# in data-model.md §5 ("fleet staleness: now() - last_seen_at against a
# threshold") and this mirrors the one relationship that IS specified.
STALE_AFTER_SECONDS = 15

WORKER_COLUMNS = f"""
    id, label, incarnation, hostname, pid, started_at, last_seen_at,
    current_run_count, capacity, code_version, role, stopped_at,
    (EXTRACT(EPOCH FROM (now() - last_seen_at)) * 1000) AS heartbeat_age_ms,
    (now() - last_seen_at > interval '{STALE_AFTER_SECONDS} seconds') AS stale,
    (EXTRACT(EPOCH FROM (now() - started_at)) * 1000) AS uptime_ms
"""


class WorkerResponse(BaseModel):
    """`contracts/openapi.yaml` -> `components.schemas.Worker`."""

    id: str
    label: str
    incarnation: int
    hostname: str
    pid: int
    started_at: str
    last_seen_at: str
    heartbeat_age_ms: int
    stale: bool
    uptime_ms: int
    current_run_count: int
    capacity: int
    code_version: str
    role: str
    stopped_at: str | None


def serialize_worker(row: asyncpg.Record) -> WorkerResponse:
    """Build a `WorkerResponse` from a row selected with `WORKER_COLUMNS`."""
    return WorkerResponse(
        id=row["id"],
        label=row["label"],
        incarnation=row["incarnation"],
        hostname=row["hostname"],
        pid=row["pid"],
        started_at=row["started_at"].isoformat(),
        last_seen_at=row["last_seen_at"].isoformat(),
        heartbeat_age_ms=int(row["heartbeat_age_ms"]),
        stale=row["stale"],
        uptime_ms=int(row["uptime_ms"]),
        current_run_count=row["current_run_count"],
        capacity=row["capacity"],
        code_version=row["code_version"],
        role=row["role"],
        stopped_at=row["stopped_at"].isoformat() if row["stopped_at"] else None,
    )
