"""Demo agents: demo_minimal, demo_short, demo_long, demo_unsafe.

Every module in this package is walked by the AST determinism checker
(anchor.core.determinism.ast_check) and MUST NOT reference `datetime`,
`time`, `random`, or `uuid` directly.
"""

from __future__ import annotations

from anchor.runtime.agents import demo_long, demo_minimal, demo_short, demo_unsafe
from anchor.runtime.agents.registry import register


def register_all() -> None:
    """Register every demo agent. Idempotent — safe to call from both the
    API process (submission validates `agent_type` against this registry)
    and the worker process (which resolves it at claim time).

    Contract metadata (P6.11, T370) is declared here rather than guessed at
    `GET /api/agents` read time, for the same reason a tool's safety is
    declared rather than inferred (contracts/tool-contract.md): the agent
    module itself is the only thing that knows its own step count and tool
    usage with certainty.
    """
    register(
        "demo_minimal",
        demo_minimal.decide_next_step,
        description="Phase-1 placeholder agent: search, then summarize, then notify.",
        expected_step_count=3,
        tools_used=("search", "summarize", "notify"),
        stubbed_model=False,
    )
    register(
        "demo_short",
        demo_short.decide_next_step,
        description="The guided-demo agent: nine steps touching every demo tool and "
        "both non-unsafe safety categories.",
        expected_step_count=9,
        tools_used=("web_search", "fetch_page", "create_ticket", "charge_card"),
        stubbed_model=True,
    )
    register(
        "demo_long",
        demo_long.decide_next_step,
        description="The already-done-filter worked example: a 19-topic survey "
        "resumable from the journal alone, never a step counter (D-57).",
        expected_step_count=1 + 2 * demo_long._TOPIC_COUNT + 1,
        tools_used=("web_search", "fetch_page"),
        stubbed_model=True,
    )
    register(
        "demo_unsafe",
        demo_unsafe.decide_next_step,
        description="Deliberately reaches needs_review via an unsafe-declared tool "
        "(send_email), so an uncertainty-window crash demonstrably halts rather "
        "than guesses.",
        expected_step_count=3,
        tools_used=("web_search", "send_email"),
        stubbed_model=True,
    )
