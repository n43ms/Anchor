/**
 * Worked examples preloaded into the authoring editor (plan.md P9.1, T576).
 * The professor-outreach example is the one taught constraint's canonical
 * illustration (contracts/agent-contract.md); the other two mirror the
 * shape of `anchor/runtime/agents/demo_long.py` and `demo_unsafe.py`
 * without depending on Python source at build time — this is TypeScript
 * text a developer edits, not an import of the real modules.
 */
export interface AuthoringExample {
  id: string;
  label: string;
  source: string;
}

export const AUTHORING_EXAMPLES: AuthoringExample[] = [
  {
    id: "professor-outreach",
    label: "Professor outreach (the one taught constraint)",
    source: `def decide_next_step(ctx):
    if not ctx.has_result("search_professors"):
        return ToolCall("search_professors", {"field": ctx.input["field"]})

    professors = ctx.result_of("search_professors")
    done = ctx.completed_tool_args("send_email")  # from the log
    remaining = [p for p in professors if p["email"] not in done]

    if not remaining:
        return Done({"contacted": len(done)})

    p = remaining[0]
    if not ctx.has_result("fetch_page", {"url": p["url"]}):
        return ToolCall("fetch_page", {"url": p["url"]})

    return ToolCall("send_email", {"to": p["email"], "body": ctx.result_of("draft")})
`,
  },
  {
    id: "already-done-filter",
    label: "Already-done filter (demo_long's pattern)",
    source: `_TOPICS = ["topic-0", "topic-1", "topic-2"]

def decide_next_step(ctx):
    # "What remains" is computed fresh from the journal on every call —
    # never cached, never a counter, never derived from ctx.step_index.
    searched = {args["query"] for args in ctx.completed_tool_args("web_search")}
    for topic in _TOPICS:
        if topic not in searched:
            return ToolCall("web_search", {"query": topic})

    return Done({"topics_covered": len(_TOPICS)})
`,
  },
  {
    id: "unsafe-tool-halt",
    label: "Unsafe tool, needs_review halt (demo_unsafe's pattern)",
    source: `def decide_next_step(ctx):
    if not ctx.has_result("web_search"):
        return ToolCall("web_search", {"query": ctx.input["topic"]})

    if not ctx.has_result("send_email"):
        # send_email is declared safety="unsafe": a crash in the
        # uncertainty window here halts the run for needs_review rather
        # than guessing whether the email went out.
        return ToolCall("send_email", {"to": ctx.input["recipient"], "body": "done"})

    return Done({"notified": True})
`,
  },
];
