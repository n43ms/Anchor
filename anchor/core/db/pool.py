"""The asyncpg connection pool: bounded size, explicit acquire timeout, and
automatic SQLSTATE translation for anchor's own error codes.

Crash behaviour: if the pool is exhausted, `acquire()` raises
`asyncpg.exceptions.TooManyConnectionsError`-adjacent `TimeoutError` after
`acquire_timeout_s`, rather than queuing indefinitely — a caller that cannot
get a connection within a bounded time should fail loudly (I7) rather than
accumulate as a growing queue of blocked coroutines.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from anchor.core.db.errors import translate_postgres_error

DEFAULT_MIN_SIZE = 0
DEFAULT_MAX_SIZE = 20
DEFAULT_ACQUIRE_TIMEOUT_S = 10.0


async def create_pool(
    dsn: str,
    *,
    min_size: int = DEFAULT_MIN_SIZE,
    max_size: int = DEFAULT_MAX_SIZE,
) -> asyncpg.Pool:
    """Create the bounded pool. Call once per process; share the returned
    pool rather than creating one per request.

    `min_size` defaults to 0, deliberately: asyncpg establishes `min_size`
    connections *during* `create_pool()` and raises if it cannot, which
    would mean a PostgreSQL outage at process boot prevents the pool from
    ever existing. With `min_size=0`, `create_pool()` always succeeds
    immediately and connections are opened lazily on first `acquire()` —
    which is what lets the API start and serve `GET /api/health` (reporting
    the outage as 503) even while the database it depends on is down (I7).
    """
    return await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)


@asynccontextmanager
async def acquire(
    pool: asyncpg.Pool, *, timeout: float = DEFAULT_ACQUIRE_TIMEOUT_S
) -> AsyncIterator[asyncpg.Connection[Any]]:
    """Acquire a connection, translating any anchor-raised SQLSTATE on exit.

    Every statement issued through this context manager benefits from the
    translation without repeating the try/except at each call site. A
    PostgresError whose SQLSTATE this module does not own propagates
    unchanged (FR-018).
    """
    async with pool.acquire(timeout=timeout) as conn:
        try:
            yield conn
        except asyncpg.PostgresError as exc:
            translated = translate_postgres_error(exc)
            if translated is not None:
                raise translated from exc
            raise
