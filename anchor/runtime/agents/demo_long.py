"""`demo_long` — the canonical worked example of the already-done filter
pattern (plan.md P5.8, T284, D-57). The README points at this file by name
(FR-138).

Roughly 40 steps: one opening model call, two tool calls per topic across
19 topics (`web_search` then `fetch_page`), and one closing model call.
**The loop's progress lives in the journal, never in a counter.** A naive
version of this agent would hold `next_topic_index` in a Python variable or
derive it as `ctx.step_index // 2` — both break the moment a step is
retried or a handoff changes how many raw steps something took, because
`step_index` then no longer lines up with "which topic am I on." Instead,
every decision asks the journal directly: `ctx.completed_tool_args(name)`
returns the argument sets of every call to `name` that has a *recorded
result* — genuinely completed, including across replay and worker handoff
— and the agent computes "what remains" by set difference against the full
topic list, every single invocation. This is what makes the pattern resume
correctly regardless of how many attempts, replays, or handoffs it took to
get partway through: the state that matters was never anywhere except the
log.
"""

from __future__ import annotations

from anchor.core.determinism.actions import Action, Done, ModelCall, ToolCall
from anchor.core.determinism.context import StepContext

_TOPIC_COUNT = 19
_TOPICS = [f"topic-{i}" for i in range(_TOPIC_COUNT)]


def _url_for(topic: str) -> str:
    return f"https://example.invalid/{topic}"


def decide_next_step(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        return ModelCall([{"role": "user", "content": f"Plan a survey of {_TOPIC_COUNT} topics."}])

    # "What remains" is computed fresh from the journal on every call — not
    # cached, not counted, and not derived from `ctx.step_index` (D-57).
    searched = {args["query"] for args in ctx.completed_tool_args("web_search")}
    for topic in _TOPICS:
        if topic not in searched:
            return ToolCall("web_search", {"query": topic})

    fetched = {args["url"] for args in ctx.completed_tool_args("fetch_page")}
    for topic in _TOPICS:
        url = _url_for(topic)
        if url not in fetched:
            return ToolCall("fetch_page", {"url": url})

    closing_step_index = 1 + 2 * _TOPIC_COUNT
    if ctx.step_index == closing_step_index:
        return ModelCall([{"role": "user", "content": "Summarize the survey of all topics."}])

    return Done({"topics_covered": _TOPIC_COUNT})
