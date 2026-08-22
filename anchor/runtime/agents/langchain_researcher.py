"""Autonomous research agent built with LangChain patterns for Anchor.

Adheres strictly to Anchor determinism rules (no direct datetime/time/random/uuid).
"""

from __future__ import annotations

from typing import Any

from anchor.core.determinism.actions import Action, Done, ModelCall, ToolCall
from anchor.core.determinism.context import StepContext


def decide_next_step(ctx: StepContext) -> Action:
    """Multi-step research and synthesis state machine.

    Step 0: Model Call -> Generate research strategy for topic.
    Step 1: Tool Call  -> Execute web_search via two-phase durable journal.
    Step 2: Model Call -> Synthesize search results into findings.
    Step 3: Done       -> Emit final structured brief.
    """
    topic: str = str(ctx.input.get("topic", "Durable Execution Runtimes"))

    # Step 0: Plan strategy with LLM
    if ctx.step_index == 0:
        return ModelCall(
            messages=[
                {
                    "role": "system",
                    "content": "You are a research analyst. Formulate a search query for the topic.",
                },
                {"role": "user", "content": f"Topic: {topic}"},
            ],
            model=None,
        )

    # Step 1: Execute web search tool (idempotent / retry_safe)
    if ctx.step_index == 1:
        return ToolCall("web_search", {"query": f"{topic} overview and core principles"})

    # Step 2: Synthesize findings with LLM
    if ctx.step_index == 2:
        search_data: Any = (
            ctx.result_of("web_search") if ctx.has_result("web_search") else {}
        )
        return ModelCall(
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical writer. Summarize the research findings clearly.",
                },
                {
                    "role": "user",
                    "content": f"Topic: {topic}\n\nSearch Results:\n{search_data}",
                },
            ],
            model=None,
        )

    # Step 3: Complete execution
    final_text = f"Research complete for {topic}."
    if ctx.messages:
        last_msg = ctx.messages[-1]
        if isinstance(last_msg, dict):
            final_text = str(last_msg.get("content", final_text))
        else:
            final_text = str(last_msg)
    return Done(
        output={
            "status": "completed",
            "topic": topic,
            "summary": final_text,
            "steps_executed": ctx.step_index + 1,
        }
    )
