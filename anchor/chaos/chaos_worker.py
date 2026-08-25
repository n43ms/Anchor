"""The harness's own in-process worker (plan.md P8.2/P8.3, T494/T501).

`anchor.chaos.injections.stall.block_event_loop` blocks whichever process
calls it — there is no HTTP endpoint for "go stall yourself" on a real
fleet worker, nor should there be (that module's own docstring: reachable
only from tests and "the chaos harness"). To produce a genuine
`stall_injected` event against a live database, the harness runs **one**
ordinary worker loop (`anchor.worker.loop.poll_and_execute_forever`, the
exact code every fleet worker runs — not a mock) as a background task
inside its own process, registered with `role='chaos'` so the fleet view
can tell it apart from a real executor (data-model.md §5). Stalling it is
then a matter of blocking the event loop they share, which blocks this
in-process worker's execution and renewer tasks exactly as it would a real
process wedged on a blocking call.

**This is the one deliberate exception to "the harness drives the system
only through the public API."** Every other injection and all workload
submission goes through HTTP; this single worker exists solely so the
fencing path can be demonstrated against the live fleet on demand, and it
never claims work on the harness's behalf — `poll_and_execute_forever`
claims whatever is next in the shared queue, same as any other worker, so
its presence adds one more competing worker rather than a privileged one.

Registers under the reserved `chaos` label pool, distinct from the fleet's
own `ANCHOR_WORKER_LABEL_POOL` — a collision there would make this worker
indistinguishable from (and contend for the same incarnation counter as) a
real one.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

import asyncpg

from anchor.chaos.injections.stall import block_event_loop
from anchor.core.config.live import LiveSettings
from anchor.worker.loop import RunCounter, poll_and_execute_forever
from anchor.worker.registry.register import mark_stopped, register

logger = logging.getLogger(__name__)

_CHAOS_LABEL_POOL = ["chaos"]


class ChaosWorker:
    """One in-process worker, started and stopped by the harness. Not
    reachable outside `anchor.chaos` (`tests/boundary/test_stall_injection_not_reachable.py`
    excludes `anchor.api`, `anchor.worker.__main__`, and `anchor.runtime` —
    not `anchor.chaos`, which this module lives in).
    """

    def __init__(self, pool: asyncpg.Pool, *, worker_id: str, live: LiveSettings) -> None:
        self._pool = pool
        self.worker_id = worker_id
        self._live = live
        self._task: asyncio.Task[None] | None = None

    @classmethod
    async def start(
        cls, pool: asyncpg.Pool, *, live: LiveSettings, code_version: str
    ) -> ChaosWorker:
        async with pool.acquire() as conn:
            registered = await register(
                conn,
                label_pool=_CHAOS_LABEL_POOL,
                capacity=live.current.per_worker_concurrency,
                code_version=code_version,
                role="chaos",
            )
        worker = cls(pool, worker_id=registered.identity.id, live=live)
        worker._task = asyncio.create_task(
            poll_and_execute_forever(
                pool, worker_id=worker.worker_id, live=live, run_counter=RunCounter()
            ),
            name=f"chaos-worker-{worker.worker_id}",
        )
        logger.info("chaos worker started", extra={"worker_id": worker.worker_id})
        return worker

    def stall(self, duration_s: float) -> None:
        """Block the event loop this worker's tasks run on — see the
        module docstring. Synchronous and blocking by construction: there
        is no `await` here for the caller to schedule around, exactly like
        the real stall it reproduces.
        """
        block_event_loop(duration_s)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        async with self._pool.acquire() as conn:
            await mark_stopped(conn, self.worker_id)
        logger.info("chaos worker stopped", extra={"worker_id": self.worker_id})
