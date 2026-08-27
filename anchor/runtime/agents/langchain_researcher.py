"""LangChain Autonomous Research & Synthesis Agent.

Demonstrates executing a real LangChain agent (using ChatPromptTemplate,
LCEL chains, and message schemas) through Anchor's deterministic state machine.
"""

from __future__ import annotations

import os
from typing import Any

from anchor.core.determinism.actions import Action, Done, ModelCall, ToolCall
from anchor.core.determinism.context import StepContext

# ─── 1. LangChain Framework Components (LCEL & Prompts) ──────────────────────
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.messages import SystemMessage, HumanMessage

    LANGCHAIN_INSTALLED = True
    
    # LangChain Prompt Template for Step 0 (Planning)
    plan_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an autonomous LangChain research director. Formulate a search plan."),
        ("human", "Research topic: {topic}"),
    ])

    # LangChain Prompt Template for Step 3 (Synthesis)
    synth_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a technical analyst synthesizing raw search and scrape results."),
        ("human", "Topic: {topic}\n\nSearch Results:\n{search_data}\n\nPage Data:\n{page_data}"),
    ])
except ImportError:
    LANGCHAIN_INSTALLED = False
    plan_prompt = None  # type: ignore
    synth_prompt = None  # type: ignore


def decide_next_step(ctx: StepContext) -> Action:
    """LangChain Agent State Machine step.

    Step 0: LangChain ChatPromptTemplate formats the planning prompt.
    Step 1: Executes `web_search` tool via Anchor Two-Phase Journal.
    Step 2: Executes `fetch_page` tool to scrape technical documentation.
    Step 3: LangChain ChatPromptTemplate formats the synthesis prompt.
    Step 4: Completes workflow and emits final research brief.
    """
    topic: str = str(ctx.input.get("topic", "Durable Execution Runtimes"))

    # ─── STEP 0: Plan with LangChain Prompt Template ──────────────────────────
    if ctx.step_index == 0:
        if LANGCHAIN_INSTALLED and plan_prompt:
            # Use LangChain's PromptTemplate to format messages
            formatted = plan_prompt.format_messages(topic=topic)
            messages = [{"role": msg.type if msg.type != "human" else "user", "content": str(msg.content)} for msg in formatted]
        else:
            messages = [
                {"role": "system", "content": "You are an autonomous LangChain research director. Formulate a search plan."},
                {"role": "user", "content": f"Research topic: {topic}"},
            ]

        return ModelCall(messages=messages, model=None)

    # ─── STEP 1: Search the Web (Tool Call - retry_safe) ──────────────────────
    if ctx.step_index == 1:
        return ToolCall("web_search", {"query": f"{topic} architecture and reliability"})

    # ─── STEP 2: Fetch Deep Technical Page (Tool Call - retry_safe) ───────────
    if ctx.step_index == 2:
        slug = topic.lower().replace(" ", "_")
        return ToolCall(
            "fetch_page",
            {"url": f"https://docs.anchor.dev/concepts/{slug}"},
        )

    # ─── STEP 3: Synthesize with LangChain Prompt Template ────────────────────
    if ctx.step_index == 3:
        search_result: dict[str, Any] = ctx.tool_results.get(1, {})
        page_result: dict[str, Any] = ctx.tool_results.get(2, {})

        if LANGCHAIN_INSTALLED and synth_prompt:
            formatted = synth_prompt.format_messages(
                topic=topic,
                search_data=str(search_result),
                page_data=str(page_result),
            )
            messages = [{"role": msg.type if msg.type != "human" else "user", "content": str(msg.content)} for msg in formatted]
        else:
            messages = [
                {"role": "system", "content": "You are a technical analyst synthesizing raw search and scrape results."},
                {"role": "user", "content": f"Topic: {topic}\n\nSearch Results:\n{search_result}\n\nPage Data:\n{page_result}"},
            ]

        return ModelCall(messages=messages, model=None)

    # ─── STEP 4: Complete Workflow ────────────────────────────────────────────
    last_message = ctx.messages[-1]["content"] if ctx.messages else f"Research completed for {topic}"

    return Done(
        output={
            "status": "completed",
            "framework": "LangChain",
            "topic": topic,
            "synthesis": last_message,
            "total_steps": ctx.step_index + 1,
        }
    )
