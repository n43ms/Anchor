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
    """
    register("demo_minimal", demo_minimal.decide_next_step)
    register("demo_short", demo_short.decide_next_step)
    register("demo_long", demo_long.decide_next_step)
    register("demo_unsafe", demo_unsafe.decide_next_step)
