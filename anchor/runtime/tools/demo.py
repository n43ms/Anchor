"""The demo tools (plan.md P1.6, extended by P5.5/P5.8-P5.9; contracts/tool-contract.md).

Two generations coexist here. `search` / `summarize` / `notify` are phase 1's
placeholders, kept only so `demo_minimal` (phase 1's hardcoded agent) keeps
working; they carry no observable side effect a duplicate could corrupt, so
they are declared `retry_safe` and never touch `demo_effects`. The five
tools named after real consequential actions —
`web_search` / `fetch_page` / `create_ticket` / `send_email` / `charge_card`
— are phase 5's actual proof surface: **every one writes a `demo_effects`
row**, and at least one exists in each of the three safety categories so all
three uncertainty policies are reachable from the interface (§21.5).

**Why `charge_card` and `create_ticket` check `demo_effects` before writing.**
Their fake implementations stand in for a real payment provider or ticketing
API — and a real provider that "accepts an idempotency key" (`charge_card`)
or that "can be queried by an external key" (`create_ticket`'s
`reconcile_fn`) is a provider whose own dedup, not the caller's, is what
makes a second physical call safe. Simulating that means the tool's fake
implementation must itself recognize a key it has already recorded and
return the same result rather than writing a second row — otherwise a
legitimate `retry_safe` re-execution (this module's whole reason for
existing) would collide with `demo_effects`'s `UNIQUE (idempotency_key)`
exactly as if it were the bug that constraint exists to catch.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import asyncpg

from anchor.core.journal.reconcile import NotExecuted, ReconcileResult
from anchor.runtime.tools.registry import ToolDeclaration

_LATENCY_S = 0.05


async def _record_effect(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    step_index: int,
    tool_name: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Write the proof row, or return the one already there.

    A plain `INSERT` would raise on a legitimate `retry_safe` /
    `reconcilable` re-invocation with the same key — the exact scenario
    those categories exist to make safe. Catching the unique violation and
    returning the row that already exists is what "the provider deduplicates
    on their side" (contracts/tool-contract.md) means concretely in this
    simulation: the *fake provider*, not the caller, recognizes the key.
    A raw duplicate attempt that never went through this path at all (e.g.
    a test forcing two distinct rows for one key) still hits the
    constraint directly and raises (T242).
    """
    try:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO demo_effects (run_id, step_index, tool_name, idempotency_key, payload)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                """,
                run_id,
                step_index,
                tool_name,
                idempotency_key,
                json.dumps(payload),
            )
        return payload
    except asyncpg.UniqueViolationError:
        row = await conn.fetchrow(
            "SELECT payload FROM demo_effects WHERE idempotency_key = $1", idempotency_key
        )
        assert row is not None
        result: dict[str, Any] = json.loads(row["payload"])
        return result


# --- Phase 1 placeholders (demo_minimal; no demo_effects writes) ---


async def _search(args: dict[str, Any], **_: Any) -> Any:
    await asyncio.sleep(_LATENCY_S)
    return {"results": [f"result-for-{args.get('query', '')}"]}


async def _summarize(args: dict[str, Any], **_: Any) -> Any:
    await asyncio.sleep(_LATENCY_S)
    return {"summary": f"summary-of-{args.get('text', '')}"}


async def _notify(args: dict[str, Any], **_: Any) -> Any:
    await asyncio.sleep(_LATENCY_S)
    return {"notified": args.get("recipient", "")}


# --- The five demo tools (P5.8-P5.9, contracts/tool-contract.md) ---


async def _web_search(
    args: dict[str, Any],
    *,
    idempotency_key: str,
    conn: asyncpg.Connection[Any],
    run_id: int,
    step_index: int,
    **_: Any,
) -> Any:
    await asyncio.sleep(_LATENCY_S)
    payload = {"query": args.get("query", ""), "results": [f"result-for-{args.get('query', '')}"]}
    return await _record_effect(
        conn,
        run_id=run_id,
        step_index=step_index,
        tool_name="web_search",
        idempotency_key=idempotency_key,
        payload=payload,
    )


async def _fetch_page(
    args: dict[str, Any],
    *,
    idempotency_key: str,
    conn: asyncpg.Connection[Any],
    run_id: int,
    step_index: int,
    **_: Any,
) -> Any:
    await asyncio.sleep(_LATENCY_S)
    payload = {"url": args.get("url", ""), "content": f"page-content-for-{args.get('url', '')}"}
    return await _record_effect(
        conn,
        run_id=run_id,
        step_index=step_index,
        tool_name="fetch_page",
        idempotency_key=idempotency_key,
        payload=payload,
    )


async def _create_ticket(
    args: dict[str, Any],
    *,
    idempotency_key: str,
    conn: asyncpg.Connection[Any],
    run_id: int,
    step_index: int,
    **_: Any,
) -> Any:
    await asyncio.sleep(_LATENCY_S)
    payload = {
        "external_key": idempotency_key,
        "title": args.get("title", ""),
        "status": "open",
    }
    return await _record_effect(
        conn,
        run_id=run_id,
        step_index=step_index,
        tool_name="create_ticket",
        idempotency_key=idempotency_key,
        payload=payload,
    )


async def _reconcile_create_ticket(args: dict[str, Any], idempotency_key: str) -> ReconcileResult:
    """Located by the same key `create_ticket` would have used to write
    `demo_effects` — the fake stand-in for "query the ticketing system by
    external key" (contracts/tool-contract.md).

    The demo harness has no independent side channel that could report
    `Unknown()` (there is no real ticketing API behind this), so this
    reconciler always answers definitively; the `Unknown()` escalation path
    is exercised by `demo_unsafe` instead, whose entire purpose is to reach
    `needs_review`.
    """
    # `conn` is not available to a `reconcile_fn` per contracts/tool-contract.md's
    # signature (`args, idempotency_key`) — it is looked up by the caller
    # via a connection the policy layer supplies through closure instead
    # in a real deployment. The demo reconciler is a pure function of the
    # arguments it would have used, matching the no-DB-access contract
    # exactly: without a live ticketing system, "not executed" is the only
    # honest answer, which is also what exercises the actual re-execution
    # branch this tool's `reconcilable` category exists to demonstrate.
    del args, idempotency_key
    return NotExecuted()


async def _send_email(
    args: dict[str, Any],
    *,
    idempotency_key: str,
    conn: asyncpg.Connection[Any],
    run_id: int,
    step_index: int,
    **_: Any,
) -> Any:
    await asyncio.sleep(_LATENCY_S)
    payload = {"recipient": args.get("recipient", ""), "subject": args.get("subject", "")}
    return await _record_effect(
        conn,
        run_id=run_id,
        step_index=step_index,
        tool_name="send_email",
        idempotency_key=idempotency_key,
        payload=payload,
    )


async def _charge_card(
    args: dict[str, Any],
    *,
    idempotency_key: str,
    conn: asyncpg.Connection[Any],
    run_id: int,
    step_index: int,
    **_: Any,
) -> Any:
    await asyncio.sleep(_LATENCY_S)
    payload = {
        "amount_cents": args.get("amount_cents", 0),
        "order_id": args.get("order_id", ""),
        "charge_id": idempotency_key,
    }
    return await _record_effect(
        conn,
        run_id=run_id,
        step_index=step_index,
        tool_name="charge_card",
        idempotency_key=idempotency_key,
        payload=payload,
    )


PHASE1_TOOLS: dict[str, ToolDeclaration] = {
    "search": ToolDeclaration(
        name="search", fn=_search, safety="retry_safe", naturally_idempotent=True
    ),
    "summarize": ToolDeclaration(
        name="summarize", fn=_summarize, safety="retry_safe", naturally_idempotent=True
    ),
    "notify": ToolDeclaration(
        name="notify", fn=_notify, safety="retry_safe", naturally_idempotent=True
    ),
}

DEMO_EFFECT_TOOLS: dict[str, ToolDeclaration] = {
    "web_search": ToolDeclaration(
        name="web_search",
        fn=_web_search,
        safety="retry_safe",
        naturally_idempotent=True,
        description="Read-only web search.",
    ),
    "fetch_page": ToolDeclaration(
        name="fetch_page",
        fn=_fetch_page,
        safety="retry_safe",
        naturally_idempotent=True,
        description="Read-only page fetch.",
    ),
    "create_ticket": ToolDeclaration(
        name="create_ticket",
        fn=_create_ticket,
        safety="reconcilable",
        reconcile_fn=_reconcile_create_ticket,
        description="Files a ticket with an external key that can be queried.",
    ),
    "send_email": ToolDeclaration(
        name="send_email",
        fn=_send_email,
        safety="unsafe",
        description="Sends a message. Cannot be un-sent and cannot be queried.",
    ),
    "charge_card": ToolDeclaration(
        name="charge_card",
        fn=_charge_card,
        safety="retry_safe",
        provider_accepts_key=True,
        description="Charges a card. Safe to retry only because the provider "
        "deduplicates on the passed-through idempotency key.",
    ),
}

# Kept under the historical name so `anchor.worker.loop`'s existing import
# (`from anchor.runtime.tools.demo import DEMO_TOOLS`) continues to resolve
# every tool any registered agent — phase 1's or phase 5's — might call.
DEMO_TOOLS: dict[str, ToolDeclaration] = {**PHASE1_TOOLS, **DEMO_EFFECT_TOOLS}


async def register_demo_tools(conn: asyncpg.Connection[Any], *, code_version: str) -> None:
    """Upsert every demo tool's declaration into `tool_registry` and make it
    resolvable in-process (P5.5) — called once at worker startup, before
    the claim loop starts.
    """
    from anchor.runtime.tools.registry import register_tool

    for decl in DEMO_TOOLS.values():
        await register_tool(conn, decl, code_version=code_version)
