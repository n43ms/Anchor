"""Worker self-registration (FR-065).

Each process lifetime inserts its own row — rows are never updated across
incarnations, so the fleet's history is append-only in practice as well as
in principle (data-model.md §5).
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import Any

import asyncpg

from anchor.worker.registry.identity import WorkerIdentity, claim_identity


@dataclass(frozen=True, slots=True)
class RegisteredWorker:
    identity: WorkerIdentity
    hostname: str
    pid: int
    capacity: int
    code_version: str
    role: str


async def register(
    conn: asyncpg.Connection[Any],
    *,
    label_pool: list[str],
    capacity: int,
    code_version: str,
    role: str = "runner",
) -> RegisteredWorker:
    """Claim an identity and insert this process's `workers` row in one
    transaction, so no other process can observe a claimed-but-unregistered
    label.
    """
    async with conn.transaction():
        identity = await claim_identity(conn, label_pool)
        hostname = socket.gethostname()
        pid = os.getpid()
        await conn.execute(
            """
            INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version, role)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            identity.id,
            identity.label,
            identity.incarnation,
            hostname,
            pid,
            capacity,
            code_version,
            role,
        )
    return RegisteredWorker(
        identity=identity,
        hostname=hostname,
        pid=pid,
        capacity=capacity,
        code_version=code_version,
        role=role,
    )


async def mark_stopped(conn: asyncpg.Connection[Any], worker_id: str) -> None:
    """Set `stopped_at` on graceful shutdown.

    Its **absence** after a hard kill is itself informative — the fleet view
    can distinguish a worker that exited cleanly from one that did not.
    """
    await conn.execute(
        "UPDATE workers SET stopped_at = now() WHERE id = $1 AND stopped_at IS NULL",
        worker_id,
    )
