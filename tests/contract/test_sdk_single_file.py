"""Single-file contract integration test (Phase 10, T626 / T630 / T631).

Verifies that a developer can define tools via `@anchor.tool`, define an agent via `@anchor.agent` using `yield`, and execute the run via `anchor.run` all inside one file.
"""

from __future__ import annotations

import pytest

import anchor


@pytest.mark.contract
def test_sdk_single_file_workflow_execution() -> None:
    # 1. Tools registered via decorators
    @anchor.tool(safety="retry_safe", naturally_idempotent=True)
    async def db_search(query: str) -> dict[str, str]:
        return {"result": f"found-{query}"}

    @anchor.tool(safety="unsafe")
    async def send_email(to: str, body: str) -> dict[str, str]:
        return {"status": "delivered", "to": to, "body": body}

    # 2. Agent defined using generator yield syntax
    @anchor.agent(name="single_file_test_agent")
    def decide_next_step(ctx: anchor.StepContext):
        search_res = yield anchor.ToolCall("db_search", {"query": ctx.input["field"]})
        email_res = yield anchor.ToolCall(
            "send_email",
            {
                "to": "user@example.com",
                "body": f"Result: {search_res['result']}",
            },
        )
        yield anchor.Done({"status": "completed", "output": email_res})

    # 3. Execute run via single-line runner helper
    result = anchor.run("single_file_test_agent", input={"field": "Distributed Systems"})

    assert result == {
        "status": "completed",
        "output": {
            "status": "delivered",
            "to": "user@example.com",
            "body": "Result: found-Distributed Systems",
        },
    }
