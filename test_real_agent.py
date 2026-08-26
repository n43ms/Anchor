"""Real Agent Demonstration Script using Anchor Ergonomic SDK."""

import asyncio
import anchor

# 1. Define real tools with crash-safety policies
@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def search_academic_papers(topic: str) -> dict:
    """Searches faculty papers for distributed systems topics."""
    await asyncio.sleep(0.1)
    return {
        "topic": topic,
        "papers": [
            {"title": "Paxos Made Simple", "author": "Lamport"},
            {"title": "In Search of an Understandable Consensus Algorithm (Raft)", "author": "Ongaro & Ousterhout"},
        ],
    }

@anchor.tool(safety="unsafe")
async def send_summary_email(recipient: str, paper_count: int) -> dict:
    """Sends a summary email of search results."""
    await asyncio.sleep(0.1)
    return {
        "status": "delivered",
        "recipient": recipient,
        "summary": f"Sent summary of {paper_count} papers to {recipient}",
    }

# 2. Define real agent decision logic using yield generator syntax
@anchor.agent(name="academic_research_agent")
def decide_next_step(ctx: anchor.StepContext):
    # Step 0: Search academic database
    search_data = yield anchor.ToolCall(
        "search_academic_papers",
        {"topic": ctx.input["topic"]}
    )

    papers = search_data["papers"]

    # Step 1: Send summary email
    email_result = yield anchor.ToolCall(
        "send_summary_email",
        {
            "recipient": ctx.input["email"],
            "paper_count": len(papers),
        }
    )

    # Terminal Step: Done
    yield anchor.Done({
        "status": "completed",
        "topic": ctx.input["topic"],
        "papers_found": len(papers),
        "email_delivery": email_result,
    })

# 3. Execute run
if __name__ == "__main__":
    print("--- Starting Anchor Real Agent Workflow ---")
    result = anchor.run(
        "academic_research_agent",
        input={"topic": "Consensus Protocols", "email": "researcher@stanford.edu"}
    )
    print("\n--- Workflow Completed Successfully! ---")
    print("Final Output Payload:")
    import json
    print(json.dumps(result, indent=2))
