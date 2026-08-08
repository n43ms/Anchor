"""The worker entrypoint.

Phase 0 scope: schema-gate check, registration, heartbeat, the kill
subscriber, and graceful-shutdown handling — a worker that registers,
heartbeats, and idles, per plan.md Phase 0's exit gate. **Claiming and step
execution are added in phase 1** (plan.md P1.4, tasks.md T084-T088); this
module is extended there, not replaced.
"""

from __future__ import annotations

import asyncio
import logging
import signal

import redis.asyncio as redis_asyncio

from anchor.core.config.loader import BootstrapEnv, load_runtime_settings
from anchor.core.db.pool import create_pool
from anchor.core.db.schema_gate import assert_schema_matches
from anchor.core.logging import configure_logging
from anchor.runtime.agents import register_all
from anchor.worker.loop import poll_and_execute_forever
from anchor.worker.registry.heartbeat import heartbeat_loop
from anchor.worker.registry.kill import subscribe_and_wait_for_kill
from anchor.worker.registry.register import mark_stopped, register

logger = logging.getLogger(__name__)


async def main() -> None:
    configure_logging()
    register_all()
    env = BootstrapEnv()  # type: ignore[call-arg]  # see anchor/api/app.py's lifespan

    pool = await create_pool(env.database_url)
    async with pool.acquire() as conn:
        await assert_schema_matches(conn)
        # Per-worker capacity is `per_worker_concurrency` from
        # `runtime_config` (FR-004, FR-059) — never a module-level
        # constant. It is read here, once, at registration; live changes
        # are applied at the next step boundary from phase 6 onward
        # (plan.md P6.6), not retroactively to an already-registered
        # worker's row.
        settings = await load_runtime_settings(conn)
        registered = await register(
            conn,
            label_pool=env.worker_labels,
            capacity=settings.per_worker_concurrency,
            code_version=env.code_version,
        )

    worker_id = registered.identity.id
    logger.info("worker registered", extra={"worker_id": worker_id})

    redis_client = redis_asyncio.from_url(env.redis_url)

    current_run_count = 0
    shutdown_requested = asyncio.Event()

    def _handle_shutdown_signal() -> None:
        # A graceful shutdown is a *cooperative* stop, distinct from the
        # kill subscriber's hard os._exit — it releases the lease
        # (once claiming exists, from phase 1 onward) and records
        # `stopped_at`, so the fleet history can tell the two apart
        # (data-model.md §5: "the absence of `stopped_at` after a hard
        # kill is itself informative").
        logger.info("shutdown signal received", extra={"worker_id": worker_id})
        shutdown_requested.set()

    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGTERM, _handle_shutdown_signal)
        loop.add_signal_handler(signal.SIGINT, _handle_shutdown_signal)
    except NotImplementedError:
        # add_signal_handler is POSIX-only; this worker runs in Linux
        # containers in every real deployment (docker-compose.yml, Render),
        # so this fallback exists only so `python -m anchor.worker` doesn't
        # crash outright when run directly on Windows during development.
        signal.signal(signal.SIGINT, lambda *_: shutdown_requested.set())

    async def _shutdown_waiter() -> None:
        await shutdown_requested.wait()
        async with pool.acquire() as conn:
            await mark_stopped(conn, worker_id)
        raise SystemExit(0)

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                heartbeat_loop(pool, worker_id, lambda: current_run_count),
                name="heartbeat",
            )
            tg.create_task(
                subscribe_and_wait_for_kill(redis_client, worker_id),
                name="kill-subscriber",
            )
            tg.create_task(_shutdown_waiter(), name="shutdown-waiter")
            # Sequential, one run at a time — the per-run TaskGroup with an
            # independent background renewer is phase 3 (P3.4).
            tg.create_task(
                poll_and_execute_forever(pool, worker_id=worker_id, settings=settings),
                name="claim-execute-loop",
            )
    except* SystemExit:
        logger.info("worker shut down gracefully", extra={"worker_id": worker_id})


if __name__ == "__main__":
    asyncio.run(main())
