"""The agent registry (plan.md P1.6).

Rejects an unregistered `agent_type` at submission — `POST /api/runs`
validates against this registry — rather than at execution, where a typo
would only surface once a worker claimed the run.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from anchor.core.determinism.actions import Action
from anchor.core.determinism.context import StepContext

DecideNextStep = Callable[[StepContext], Awaitable[Action] | Action]

_REGISTRY: dict[str, DecideNextStep] = {}


def register(name: str, fn: DecideNextStep) -> None:
    _REGISTRY[name] = fn


def resolve(name: str) -> DecideNextStep | None:
    return _REGISTRY.get(name)


def is_registered(name: str) -> bool:
    return name in _REGISTRY
