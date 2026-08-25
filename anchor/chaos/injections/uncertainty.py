"""Uncertainty-window crash injection (plan.md P8.3, T503; FR-079).

Exercises all three declared policies by targeting the one demo agent whose
tool is declared `unsafe` (`demo_unsafe`'s `send_email`) — the same
scenario `demo_unsafe`'s own module docstring names as its reason for
existing. This module submits the run, watches its event log through the
public API (D-36 — no direct database or worker access) for the
`TOOL_INTENT` that has not yet been followed by a `TOOL_RESULT`, and kills
the run's current owner at exactly that moment, landing the crash inside
the uncertainty window rather than at an arbitrary point in the run.

**Why this targets `send_email` and not a `retry_safe`/`reconcilable`
tool.** `demo_short`/`demo_long` exercise `retry_safe` and `reconcilable`
tools as part of the harness's ordinary workload mix already (every kill
injection lands inside *some* run's uncertainty window purely by chance,
across enough runs and enough kills). This injection exists specifically
to *guarantee* at least one crash lands inside the `unsafe` window every
harness run, because that is the policy with the fewest other chances to
be exercised — `unsafe` halts to `needs_review` rather than resolving
automatically, so it never shows up unless something crashes inside it.
"""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg
import httpx

from anchor.chaos.recorder import record_chaos_event

_TERMINAL_EVENT_TYPES = frozenset(
    {"RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELLED", "RUN_NEEDS_REVIEW"}
)


class UncertaintyInjectionTimeout(Exception):
    """Raised when the targeted `TOOL_INTENT` never appears within the
    poll budget — e.g. the run dead-lettered on an earlier step, or the
    fleet is saturated and never claimed it. Not swallowed: the caller
    decides whether a missed injection should fail the harness run.
    """


async def inject_uncertainty_crash(
    client: httpx.AsyncClient,
    conn: asyncpg.Connection[Any],
    *,
    chaos_run_id: int,
    target_tool_name: str = "send_email",
    poll_interval_s: float = 0.25,
    timeout_s: float = 30.0,
) -> tuple[int, str] | None:
    """Submit a `demo_unsafe` run, wait for `target_tool_name`'s
    `TOOL_INTENT` to commit without a matching `TOOL_RESULT`, then hard-kill
    the run's current owner. Returns `(run_id, killed_worker_id)`, or
    `None` if the run reached a terminal state before the targeted call
    ever started (nothing to crash inside — not an error).
    """
    submit = await client.post("/api/runs", json={"agent_type": "demo_unsafe", "input": {}})
    submit.raise_for_status()
    run_id = int(submit.json()["id"])

    deadline = asyncio.get_running_loop().time() + timeout_s
    after_seq = 0
    intent_seen = False
    while asyncio.get_running_loop().time() < deadline:
        events_resp = await client.get(
            f"/api/runs/{run_id}/events", params={"after_seq": after_seq}
        )
        events_resp.raise_for_status()
        body = events_resp.json()
        reached_terminal = False
        for item in body["items"]:
            after_seq = item["seq"]
            if item["type"] == "TOOL_INTENT" and item["payload"]["tool_name"] == target_tool_name:
                intent_seen = True
            elif item["type"] == "TOOL_RESULT" and item["payload"]["tool_name"] == target_tool_name:
                # The call already completed before this poll caught it —
                # the window closed; nothing to crash inside anymore.
                return None
            elif item["type"] in _TERMINAL_EVENT_TYPES:
                reached_terminal = True

        if intent_seen:
            run_resp = await client.get(f"/api/runs/{run_id}")
            run_resp.raise_for_status()
            owner_worker_id = run_resp.json()["owner_worker_id"]
            if owner_worker_id is None:
                raise UncertaintyInjectionTimeout(
                    f"run {run_id} has no owner immediately after {target_tool_name}'s "
                    "TOOL_INTENT — the window may have already closed"
                )
            kill_resp = await client.post(
                f"/api/workers/{owner_worker_id}/kill",
                json={"graceful": False, "chaos_run_id": chaos_run_id},
            )
            if kill_resp.status_code == 202:
                # The kill endpoint already recorded its own `worker_kill`
                # row (data-model.md §6); this second row records *why* —
                # the semantic fact that the kill landed inside a specific
                # tool's uncertainty window, which `worker_kill` alone does
                # not distinguish from an ordinary random kill.
                await record_chaos_event(
                    conn,
                    chaos_run_id=chaos_run_id,
                    type="uncertainty_crash_injected",
                    target_worker_id=owner_worker_id,
                    affected_run_ids=[run_id],
                    params={"target_tool_name": target_tool_name},
                )
                return run_id, owner_worker_id
            if kill_resp.status_code in (404, 429):
                # Owner already gone or the kill rate limit was hit — try
                # again on the next poll tick rather than failing outright.
                intent_seen = False
                await asyncio.sleep(poll_interval_s)
                continue
            kill_resp.raise_for_status()

        if reached_terminal and not intent_seen:
            # The run finished (or halted, or was cancelled) without the
            # targeted tool ever starting — nothing to crash inside.
            return None

        await asyncio.sleep(poll_interval_s)

    raise UncertaintyInjectionTimeout(
        f"{target_tool_name}'s TOOL_INTENT never appeared for run {run_id} within {timeout_s}s"
    )
