"""`demo_short` — the guided-demo agent (plan.md P5.8, T283; Addendum F's
quality bar, pulled forward per constitution Governance precedence item 9).

Nine steps, touching every one of the five demo tools and both of the
non-`unsafe` safety categories reachable without deliberately halting: two
reads (`web_search`, `fetch_page`), one `reconcilable` write
(`create_ticket`), one `retry_safe`-because-the-provider-accepts-a-key write
(`charge_card`), and three model calls bracketing the tool calls. Returns
exactly one action per invocation and holds no state across calls —
everything branches on `ctx.step_index` and journaled history, never a
module-level or closure variable (agent-contract.md rule 3).

**Uncertain about step timing**: each demo tool's simulated latency is
currently a small constant shared with the test suite (`runtime/tools/demo.py`
`_LATENCY_S`), not yet tuned to Addendum F's "2-5 s per step, 25-40 s total"
demo-quality bar — tuning it up would make every test and CI run that
exercises these tools proportionally slower. Flagged rather than guessed;
see the phase-5 completion report.
"""

from __future__ import annotations

from anchor.core.determinism.actions import Action, Done, ModelCall, ToolCall
from anchor.core.determinism.context import StepContext


def decide_next_step(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        return ModelCall(
            [{"role": "user", "content": f"Plan research for: {ctx.input.get('topic', 'anchor')}"}]
        )
    if ctx.step_index == 1:
        return ToolCall("web_search", {"query": ctx.input.get("topic", "anchor")})
    if ctx.step_index == 2:
        return ToolCall(
            "fetch_page", {"url": f"https://example.invalid/{ctx.input.get('topic', 'anchor')}"}
        )
    if ctx.step_index == 3:
        return ToolCall(
            "create_ticket", {"title": f"Follow up: {ctx.input.get('topic', 'anchor')}"}
        )
    if ctx.step_index == 4:
        return ModelCall([{"role": "user", "content": "Draft a purchase justification."}])
    if ctx.step_index == 5:
        return ToolCall(
            "charge_card",
            {
                "amount_cents": ctx.input.get("amount_cents", 1999),
                "order_id": f"order-{ctx.run_id}",
            },
        )
    if ctx.step_index == 6:
        return ToolCall("web_search", {"query": f"{ctx.input.get('topic', 'anchor')} follow-up"})
    if ctx.step_index == 7:
        return ToolCall("fetch_page", {"url": "https://example.invalid/follow-up"})
    if ctx.step_index == 8:
        return ModelCall([{"role": "user", "content": "Summarize what was found and done."}])
    return Done({"topic": ctx.input.get("topic", "anchor"), "steps": ctx.step_index})
