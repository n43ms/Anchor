"""T153 — every renewal records its latency to telemetry regardless of
whether a `LEASE_RENEWED` event was emitted (D-48). The log stays readable
(most renewals emit nothing) while the distribution stays complete
(`caplog` captures a `renewal_latency_ms` on every single tick).
"""

from __future__ import annotations

import json
import logging

import asyncpg
import pytest

from anchor.core.config.profiles import ConfigProfile, profile_settings
from anchor.core.config.settings import LeaseRenewedEmitPolicy
from anchor.core.events.append import append
from anchor.core.events.types import EventType
from anchor.core.leases.claim import claim_one
from anchor.core.leases.renew import renew_once

MAX_PAYLOAD = 1_000_000


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


@pytest.mark.asyncio
async def test_latency_is_logged_even_when_no_event_is_emitted(
    db_pool: asyncpg.Pool, caplog: pytest.LogCaptureFixture
) -> None:
    settings = profile_settings(ConfigProfile.DEMO).model_copy(
        update={"lease_renewed_emit_policy": LeaseRenewedEmitPolicy.BOUNDARIES_AND_SLOW}
    )

    async with db_pool.acquire() as conn:
        run_id = await _insert_run(conn)
        await conn.execute(
            "INSERT INTO workers (id, label, incarnation, hostname, pid, capacity, code_version) "
            "VALUES ('worker-a#1', 'worker-a', 1, 'test', 1, 10, 'dev') ON CONFLICT DO NOTHING"
        )
        claimed = await claim_one(
            conn,
            worker_id="worker-a#1",
            lease_duration_ms=settings.lease_duration_ms,
            global_concurrency_cap=50,
            max_payload_bytes=MAX_PAYLOAD,
        )
        assert claimed is not None

        with caplog.at_level(logging.INFO, logger="anchor.core.leases.renew"):
            # is_first=False, force_final=False, and latency will be tiny —
            # this renewal is expected to emit NO event under the default
            # policy, yet the telemetry line must still appear.
            outcome = await renew_once(
                conn,
                run_id=run_id,
                epoch=claimed.epoch,
                worker_id="worker-a#1",
                settings=settings,
                is_first=False,
                force_final=False,
                max_payload_bytes=MAX_PAYLOAD,
            )

        assert outcome.emitted is False
        event_count = await conn.fetchval(
            "SELECT count(*) FROM run_events WHERE run_id = $1 AND type = 'LEASE_RENEWED'", run_id
        )
        assert event_count == 0, "the default policy must not emit this renewal as an event"

    telemetry_lines = [r for r in caplog.records if r.message == "lease renewed"]
    assert len(telemetry_lines) == 1
    assert hasattr(telemetry_lines[0], "renewal_latency_ms")
    assert telemetry_lines[0].renewal_latency_ms >= 0
