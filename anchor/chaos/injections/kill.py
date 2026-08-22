"""Random worker kills (plan.md P8.3, T499; FR-076).

Driven entirely through the public API (D-36): the harness never touches
Redis or a worker process directly, the same path `POST
/api/workers/{worker_id}/kill` already serves for a console operator. The
endpoint itself records the `chaos_events` row and returns its id
(`anchor.api.routers.workers.kill_worker`) — this module just picks a
target and calls it, passing `chaos_run_id` through so the event is
attributed to this harness run rather than looking like a manual kill.
"""

from __future__ import annotations

import random

import httpx


class KillInjectionError(Exception):
    """Raised when the kill endpoint refuses or fails. Distinct from a bare
    `httpx.HTTPStatusError` so callers can log a chaos-specific message.
    """


async def inject_random_kill(
    client: httpx.AsyncClient, *, chaos_run_id: int, candidate_worker_ids: list[str]
) -> tuple[str, int] | None:
    """Pick one worker uniformly at random from `candidate_worker_ids` and
    hard-kill it. Returns `(worker_id, chaos_event_id)`, or `None` if no
    candidate was available (e.g. every worker is already mid-restart) —
    not an error, since a kill attempt finding nothing to kill is a timing
    fact about the fleet, not a harness malfunction.
    """
    if not candidate_worker_ids:
        return None
    worker_id = random.choice(candidate_worker_ids)
    response = await client.post(
        f"/api/workers/{worker_id}/kill",
        json={"graceful": False, "chaos_run_id": chaos_run_id},
    )
    if response.status_code == 404:
        # The worker already respawned under a new incarnation between
        # candidate selection and this call — a timing fact, not a failure.
        return None
    if response.status_code == 429:
        # The same per-IP kill rate limit a console operator is bound by
        # (`anchor.api.middleware`, T359) — the harness backs off for this
        # tick rather than treating a shared bound as a harness failure.
        return None
    if response.status_code != 202:
        raise KillInjectionError(
            f"kill of {worker_id!r} failed: {response.status_code} {response.text}"
        )
    body = response.json()
    return worker_id, int(body["chaos_event_id"])
