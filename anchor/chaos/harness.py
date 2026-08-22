"""The chaos harness orchestrator (plan.md P8.2, T494-T498).

Drives the system exclusively through the public HTTP API (D-36) for
workload submission and every injection except the stall (see
`anchor.chaos.chaos_worker`'s module docstring for that one deliberate
exception) — the console's "launch" button and a scheduled CI run invoke
this same function, so the two can never silently diverge in what they
actually exercise.

**Deliberately not durable.** A crash mid-run leaves `chaos_runs.status`
at `'running'` with a stale `heartbeat_at`; `mark_abandoned_chaos_runs`
(called at API startup) reconciles that to `'abandoned'` rather than
resuming it. Making this durable would mean running the harness *on*
Anchor, which is circular and would compromise the independence of the
proof it produces (`anchor/chaos/__init__.py`).
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

import asyncpg
import httpx

from anchor.api.middleware import CHAOS_HARNESS_HEADER
from anchor.chaos.chaos_worker import ChaosWorker
from anchor.chaos.injections.kill import inject_random_kill
from anchor.chaos.injections.latency import inject_latency
from anchor.chaos.injections.tool_failure import inject_tool_failure
from anchor.chaos.injections.uncertainty import inject_uncertainty_crash
from anchor.chaos.recorder import record_chaos_event
from anchor.chaos.report import compute_report, persist_report
from anchor.chaos.workload import submit_workload
from anchor.core.config.live import LiveSettings
from anchor.runtime.agents import register_all
from anchor.runtime.tools.demo import register_demo_tools

logger = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL_S = 5.0
_TICK_INTERVAL_S = 2.0
_TERMINAL_GRACE_MULTIPLE = 4  # multiples of lease_duration_ms to wait for drain


@dataclass(frozen=True, slots=True)
class ChaosConfig:
    worker_count: int
    duration_seconds: int
    run_count: int = 10
    kill_rate_per_minute: float = 0.0
    latency_injection_ms: int = 0
    stall_injection_rate: float = 0.0
    tool_failure_rate: float = 0.0
    uncertainty_crash_rate: float = 0.0
    step_mix: dict[str, int] | None = None

    def as_params(self) -> dict[str, Any]:
        return {
            "worker_count": self.worker_count,
            "duration_seconds": self.duration_seconds,
            "run_count": self.run_count,
            "kill_rate_per_minute": self.kill_rate_per_minute,
            "latency_injection_ms": self.latency_injection_ms,
            "stall_injection_rate": self.stall_injection_rate,
            "tool_failure_rate": self.tool_failure_rate,
            "uncertainty_crash_rate": self.uncertainty_crash_rate,
            "step_mix": self.step_mix,
        }


@dataclass(slots=True)
class _RunState:
    run_ids: list[int] = field(default_factory=list)


async def mark_abandoned_chaos_runs(conn: asyncpg.Connection[Any], *, stale_after_s: float = 60.0) -> int:
    """Called once at API startup (T497, T483): a `chaos_runs` row still
    `running` with a `heartbeat_at` older than `stale_after_s` means the
    process that owned it (this harness is not durable, per the module
    docstring) died without finishing. Marking it `abandoned` — rather than
    leaving it `running` forever, or silently resuming it — is the honest
    outcome; a stale `running` row would otherwise look like a hung harness
    to an operator forever.
    """
    rows = await conn.fetch(
        """
        UPDATE chaos_runs
        SET status = 'abandoned', ended_at = now()
        WHERE status = 'running'
          AND (heartbeat_at IS NULL OR heartbeat_at < now() - ($1 * interval '1 second'))
        RETURNING id
        """,
        stale_after_s,
    )
    return len(rows)


def build_http_client(
    base_url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> httpx.AsyncClient:
    """The one client constructor every caller of `run_harness` uses —
    console-triggered (`anchor.api.routers.chaos`, an ASGI-transport client
    that never opens a real socket to itself) and the standalone scheduled
    job (P8.8, a real network client against the deployed URL) alike — so
    `CHAOS_HARNESS_HEADER` (the rate-limit exemption, `anchor.api.middleware`)
    is set in exactly one place rather than at every call site.
    """
    return httpx.AsyncClient(
        base_url=base_url,
        headers={CHAOS_HARNESS_HEADER: "internal"},
        timeout=30.0,
        transport=transport,
    )


async def create_chaos_run(
    pool: asyncpg.Pool,
    *,
    config: ChaosConfig,
    deployment_mode: str,
    config_profile: str,
    lease_duration_ms: int,
    renewal_interval_ms: int,
) -> int:
    """Insert the `chaos_runs` row and return its id, synchronously —
    called from the request handler itself (`anchor.api.routers.chaos`),
    never from the background task, so `POST /api/chaos/start`'s 202
    response can report the real id immediately rather than a caller
    racing a background task's own insert to find it (T517).
    """
    async with pool.acquire() as conn:
        chaos_run_id = await conn.fetchval(
            """
            INSERT INTO chaos_runs
                (status, params, deployment_mode, config_profile,
                 lease_duration_ms, renewal_interval_ms, heartbeat_at)
            VALUES ('running', $1::jsonb, $2, $3, $4, $5, now())
            RETURNING id
            """,
            json.dumps(config.as_params()),
            deployment_mode,
            config_profile,
            lease_duration_ms,
            renewal_interval_ms,
        )
    return int(chaos_run_id)


async def run_harness(
    pool: asyncpg.Pool,
    *,
    chaos_run_id: int,
    client: httpx.AsyncClient,
    config: ChaosConfig,
    lease_duration_ms: int,
    live: LiveSettings,
    code_version: str = "chaos-harness",
) -> None:
    """Run the workload/injection/report phases for an already-created
    `chaos_run_id` (`create_chaos_run`). Raises nothing on an invariant
    violation — that is a *result*, recorded in the report, not a harness
    failure; only a genuine harness-internal error (an unreachable API, a
    database error) propagates, and is reflected as `status = 'failed'`.

    `client` is supplied by the caller, built via `build_http_client`: an
    ASGI-transport client for the console-triggered path (`anchor.api.routers.chaos`)
    or a real network client for the standalone scheduled job against a
    deployed instance (P8.8) — this function does not care which.
    """
    register_all()
    async with pool.acquire() as conn:
        await register_demo_tools(conn, code_version=code_version)

    state = _RunState()
    chaos_worker: ChaosWorker | None = None
    if config.stall_injection_rate > 0:
        chaos_worker = await ChaosWorker.start(pool, live=live, code_version=code_version)

    try:
        state.run_ids.extend(
            await submit_workload(client, run_count=config.run_count, step_mix=config.step_mix)
        )
        await _sustain(pool, client, config, state, chaos_run_id, chaos_worker)

        async with pool.acquire() as conn:
            await _wait_for_drain(conn, run_ids=state.run_ids, lease_duration_ms=lease_duration_ms)
            report = await compute_report(
                conn,
                chaos_run_id=chaos_run_id,
                run_ids=state.run_ids,
                duration_seconds=config.duration_seconds,
            )
            async with conn.transaction():
                await persist_report(conn, report)
                await conn.execute(
                    "UPDATE chaos_runs SET status = 'completed', ended_at = now() WHERE id = $1",
                    chaos_run_id,
                )
    except Exception:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE chaos_runs SET status = 'failed', ended_at = now() WHERE id = $1",
                chaos_run_id,
            )
        raise
    finally:
        if chaos_worker is not None:
            await chaos_worker.stop()


_TERMINAL_STATUSES = ("completed", "failed", "cancelled", "needs_review")
_TERMINAL_STATUSES_SQL = "(" + ", ".join(f"'{s}'" for s in _TERMINAL_STATUSES) + ")"


async def _wait_for_drain(
    conn: asyncpg.Connection[Any], *, run_ids: list[int], lease_duration_ms: int
) -> None:
    """After the injection window closes, give every submitted run one
    more chance to reach a terminal state before the report is computed —
    otherwise a run still legitimately in flight when the clock ran out
    would be counted as stranded for no reason other than bad timing.
    Bounded to `_TERMINAL_GRACE_MULTIPLE` lease durations: long enough to
    cover one full reclaim-and-resume cycle, not indefinite — a run still
    not terminal after that really is what invariant 4 exists to catch.
    """
    if not run_ids:
        return
    deadline = time.monotonic() + (lease_duration_ms / 1000) * _TERMINAL_GRACE_MULTIPLE
    while time.monotonic() < deadline:
        remaining = await conn.fetchval(
            f"SELECT count(*) FROM runs WHERE id = ANY($1) AND status NOT IN {_TERMINAL_STATUSES_SQL}",
            run_ids,
        )
        if int(remaining) == 0:
            return
        await asyncio.sleep(1.0)


async def _sustain(
    pool: asyncpg.Pool,
    client: httpx.AsyncClient,
    config: ChaosConfig,
    state: _RunState,
    chaos_run_id: int,
    chaos_worker: ChaosWorker | None,
) -> None:
    """The sustained-operation loop (T496): ticks every `_TICK_INTERVAL_S`
    for `config.duration_seconds`, rolling each configured injection's
    per-tick probability independently, and heartbeats `chaos_runs` on its
    own slower cadence so an API restart mid-run can tell a live harness
    from an abandoned one (T497).
    """
    deadline = time.monotonic() + config.duration_seconds
    last_heartbeat = 0.0
    kill_probability_per_tick = (config.kill_rate_per_minute / 60.0) * _TICK_INTERVAL_S

    while time.monotonic() < deadline:
        tick_start = time.monotonic()

        if tick_start - last_heartbeat >= _HEARTBEAT_INTERVAL_S:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE chaos_runs SET heartbeat_at = now() WHERE id = $1", chaos_run_id
                )
            last_heartbeat = tick_start

        if kill_probability_per_tick > 0 and random.random() < kill_probability_per_tick:
            workers_resp = await client.get("/api/workers")
            workers_resp.raise_for_status()
            candidates = [w["id"] for w in workers_resp.json()["items"] if w["stopped_at"] is None]
            await inject_random_kill(client, chaos_run_id=chaos_run_id, candidate_worker_ids=candidates)

        if config.latency_injection_ms > 0 and random.random() < 0.3:
            async with pool.acquire() as conn:
                state.run_ids.append(
                    await inject_latency(
                        client, conn, chaos_run_id=chaos_run_id, latency_ms=config.latency_injection_ms
                    )
                )

        if config.tool_failure_rate > 0 and random.random() < 0.3:
            async with pool.acquire() as conn:
                state.run_ids.append(
                    await inject_tool_failure(
                        client, conn, chaos_run_id=chaos_run_id, fail_rate=config.tool_failure_rate
                    )
                )

        if config.uncertainty_crash_rate > 0 and random.random() < config.uncertainty_crash_rate:
            async with pool.acquire() as conn:
                outcome = await inject_uncertainty_crash(client, conn, chaos_run_id=chaos_run_id)
            if outcome is not None:
                state.run_ids.append(outcome[0])

        if chaos_worker is not None and random.random() < config.stall_injection_rate:
            async with pool.acquire() as conn:
                await record_chaos_event(
                    conn,
                    chaos_run_id=chaos_run_id,
                    type="stall_injected",
                    target_worker_id=chaos_worker.worker_id,
                )
            # Synchronous and blocking (see ChaosWorker.stall's docstring):
            # this tick, and only this tick, pauses the whole harness loop
            # for the stall's duration — the same thing a real stalled
            # process does to everything sharing its event loop.
            chaos_worker.stall(min(5.0, config.duration_seconds / 4))

        elapsed = time.monotonic() - tick_start
        await asyncio.sleep(max(0.0, _TICK_INTERVAL_S - elapsed))
