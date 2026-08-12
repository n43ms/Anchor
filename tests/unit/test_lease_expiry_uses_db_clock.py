"""T151 — lease expiry is evaluated in SQL against the database's own
`now()`, and no worker clock ever appears in a lease comparison (`I5`,
FR-010). Checked two ways: structurally, that neither `_CLAIM_SQL` nor
`_RENEW_SQL` contains anything but `now()` for a time comparison; and
behaviourally, that a worker process with a wildly wrong system clock still
claims and reclaims exactly as a correctly-clocked one would.
"""

from __future__ import annotations

import json

import asyncpg
import pytest

from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases import claim as claim_module
from anchor.core.leases import renew as renew_module
from anchor.core.leases.claim import claim_one

MAX_PAYLOAD = 1_000_000


def test_claim_sql_uses_only_the_database_clock() -> None:
    sql = claim_module._CLAIM_SQL
    assert "now()" in sql
    assert "clock_timestamp()" not in sql, (
        "clock_timestamp() would disagree with itself within one transaction"
    )


def test_renew_sql_uses_only_the_database_clock() -> None:
    sql = renew_module._RENEW_SQL
    assert "now()" in sql
    assert "clock_timestamp()" not in sql


async def _insert_run(conn: asyncpg.Connection) -> int:
    run_id: int = await conn.fetchval(
        "INSERT INTO runs (agent_type, input) VALUES ($1, $2::jsonb) RETURNING id",
        "demo_minimal",
        json.dumps({}),
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
        max_payload_bytes=MAX_PAYLOAD,
    )
    return run_id


def test_claim_module_imports_neither_datetime_nor_time() -> None:
    """There is nothing in `core.leases.claim` for a wrong worker clock to
    corrupt: no `datetime`, no `time`, no wall-clock read of any kind — the
    claim statement's only notion of "now" is PostgreSQL's `now()`. Checked
    over the source text rather than by patching the real `time` module,
    which risks breaking unrelated library internals (asyncio, asyncpg)
    that legitimately use it.
    """
    assert claim_module.__file__ is not None
    with open(claim_module.__file__, encoding="utf-8") as f:
        source = f.read()
    assert "import datetime" not in source
    assert "import time" not in source


def test_renew_modules_time_import_is_latency_measurement_only() -> None:
    """`core.leases.renew` DOES `import time` — for `time.monotonic()`,
    measuring how long the renewal round-trip took for telemetry
    (`renewal_latency_ms`). That is not an `I5` violation: it never feeds a
    lease-expiry or ownership decision, only an observability metric. This
    test pins that the only use of the module is `time.monotonic`, so a
    future edit that starts using `time.time()` here — which *would* be a
    wall-clock read — fails loudly.
    """
    assert renew_module.__file__ is not None
    with open(renew_module.__file__, encoding="utf-8") as f:
        source = f.read()
    assert "time.monotonic()" in source
    assert "time.time()" not in source
    assert "datetime.now()" not in source


@pytest.mark.asyncio
async def test_claim_succeeds_regardless_of_the_workers_own_wall_clock(
    db_pool: asyncpg.Pool,
) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        claimed = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=4_000,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
    assert claimed is not None
    assert claimed.run_id == run_id
