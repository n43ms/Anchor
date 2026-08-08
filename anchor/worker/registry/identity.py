"""Fleet-slot label claiming and incarnation allocation (D-42, FR-129).

Hostname plus pid is reused on a container platform: a killed worker
restarts with the same hostname and can receive the same pid. A reused id
would silently falsify "which worker executed each step" and break the
Deployments page's ability to answer "which build is actually running." So
identity is `{label}#{incarnation}`, where the incarnation is drawn from a
counter that survives the worker that last held the label.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import asyncpg


@dataclass(frozen=True, slots=True)
class WorkerIdentity:
    label: str
    incarnation: int

    @property
    def id(self) -> str:
        return f"{self.label}#{self.incarnation}"


async def claim_identity(conn: asyncpg.Connection[Any], label_pool: list[str]) -> WorkerIdentity:
    """Claim the first label in `label_pool` not already held by a live
    worker, and allocate its next incarnation atomically.

    A label is "held" while a `workers` row for it has `stopped_at IS NULL`
    and a recent `last_seen_at` — a crashed worker's row does not block its
    label from being reclaimed, because nothing will ever update it again.
    This runs inside the caller's transaction so the label check and the
    incarnation allocation are consistent with each other.
    """
    for label in label_pool:
        held = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM workers
                WHERE label = $1
                  AND stopped_at IS NULL
                  AND last_seen_at > now() - interval '30 seconds'
            )
            """,
            label,
        )
        if held:
            continue

        incarnation = await conn.fetchval(
            """
            INSERT INTO worker_label_incarnations (label, next_incarnation)
            VALUES ($1, 2)
            ON CONFLICT (label) DO UPDATE
                SET next_incarnation = worker_label_incarnations.next_incarnation + 1
            RETURNING next_incarnation - 1
            """,
            label,
        )
        return WorkerIdentity(label=label, incarnation=incarnation)

    raise RuntimeError(
        f"no free fleet-slot label in pool {label_pool!r} — every label is held by a live worker"
    )
