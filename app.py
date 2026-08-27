# app.py - Single-File Anchor Agent
import anchor

# 1. Define Tools with explicit crash safety policies
@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def search_academic_papers(topic: str) -> dict:
    """Read-only paper search."""
    return {"papers": ["Paxos Made Simple", "Raft Consensus"]}

@anchor.tool(safety="unsafe")
async def send_summary_email(to: str, count: int) -> dict:
    """Sends live email summary (non-idempotent side effect)."""
    return {"status": "delivered", "recipient": to}

# 2. Define Agent using line-by-line yield syntax
@anchor.agent(name="my_first_agent")
def decide_next_step(ctx: anchor.StepContext):
    search_data = yield anchor.ToolCall("search_academic_papers", {"topic": ctx.input["topic"]})
    papers = search_data["papers"]

    email_res = yield anchor.ToolCall("send_summary_email", {
        "to": ctx.input["email"],
        "count": len(papers)
    })

    yield anchor.Done({"status": "completed", "email_delivery": email_res})

# 3. Execution Trigger
if __name__ == "__main__":
    result = anchor.run(
        "my_first_agent",
        input={"topic": "Consensus Protocols", "email": "user@stanford.edu"}
    )
    print("Workflow Output Payload:", result)
