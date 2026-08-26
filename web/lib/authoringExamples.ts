/**
 * Worked examples preloaded into the authoring editor (plan.md P9.1, T576).
 * Updated to feature ergonomic @anchor.tool and @anchor.agent generator syntax.
 */
export interface AuthoringExample {
  id: string;
  label: string;
  source: string;
}

export const AUTHORING_EXAMPLES: AuthoringExample[] = [
  {
    id: "professor-outreach-sdk",
    label: "Single-file SDK Agent (@anchor.tool & yield)",
    source: `import anchor

@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def search_professors(field: str) -> dict:
    """Read-only search tool."""
    return {"results": [{"name": "Dr. Ousterhout", "email": "ouster@cs.stanford.edu"}]}

@anchor.tool(safety="unsafe")
async def send_email(to: str, body: str) -> dict:
    """Sends email summary."""
    return {"status": "delivered", "recipient": to}

@anchor.agent(name="outreach_agent")
def decide_next_step(ctx: anchor.StepContext):
    search_data = yield anchor.ToolCall("search_professors", {"field": ctx.input["field"]})
    professors = search_data["results"]

    if professors:
        p = professors[0]
        email_res = yield anchor.ToolCall("send_email", {
            "to": p["email"],
            "body": f"Reaching out regarding {ctx.input['field']}"
        })
        yield anchor.Done({"status": "completed", "emailed": email_res})

    yield anchor.Done({"status": "no_professors_found"})
`,
  },
  {
    id: "professor-outreach",
    label: "Classic State-Machine Agent (decide_next_step)",
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
    searched = {args["query"] for args in ctx.completed_tool_args("web_search")}
    for topic in _TOPICS:
        if topic not in searched:
            return ToolCall("web_search", {"query": topic})

    return Done({"topics_covered": len(_TOPICS)})
`,
  },
];
