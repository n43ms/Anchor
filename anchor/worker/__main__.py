"""The worker entrypoint.

Phase 0 scope: schema-gate check, registration, heartbeat, and the kill
subscriber — a worker that registers, heartbeats, and idles, per plan.md
Phase 0's exit gate. **Claiming and step execution are added in phase 1**
(plan.md P1.4, tasks.md T084-T088); this module is extended there, not
replaced.
"""

from __future__ import annotations

import asyncio
import logging

import redis.asyncio as redis_asyncio

from anchor.core.config.loader import BootstrapEnv
from anchor.core.db.pool import create_pool
from anchor.core.db.schema_gate import assert_schema_matches
from anchor.core.logging import configure_logging
from anchor.worker.registry.heartbeat import heartbeat_loop
from anchor.worker.registry.kill import subscribe_and_wait_for_kill
from anchor.worker.registry.register import register

logger = logging.getLogger(__name__)

DEFAULT_CAPACITY = 10


async def main() -> None:
    configure_logging()
    env = BootstrapEnv()

    pool = await create_pool(env.database_url)
    async with pool.acquire() as conn:
        await assert_schema_matches(conn)
        registered = await register(
            conn,
            label_pool=env.worker_labels,
            capacity=DEFAULT_CAPACITY,
            code_version=env.code_version,
        )

    worker_id = registered.identity.id
    logger.info("worker registered", extra={"worker_id": worker_id})

    redis_client = redis_asyncio.from_url(env.redis_url)

    current_run_count = 0

    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            heartbeat_loop(pool, worker_id, lambda: current_run_count),
            name="heartbeat",
        )
        tg.create_task(
            subscribe_and_wait_for_kill(redis_client, worker_id),
            name="kill-subscriber",
        )
        # The claim/execute loop joins this TaskGroup in phase 3 (P3.4); in
        # phase 0 and phase 1 the worker idles between the two tasks above.


if __name__ == "__main__":
    asyncio.run(main())
