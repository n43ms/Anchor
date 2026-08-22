"""The agent registry (plan.md P1.6, extended P6.11/T370; FR-120).

Rejects an unregistered `agent_type` at submission — `POST /api/runs`
validates against this registry — rather than at execution, where a typo
would only surface once a worker claimed the run.

**The contract metadata is optional at the call site, not just at the
schema level.** `register`'s five metadata keywords all default to values
meaning "not declared" (`""`, `()`, `None`, `False`) precisely because
several tests register a throwaway `decide_next_step` purely to exercise a
worker-loop code path and have no contract worth describing — requiring
every call site to state a `tools_used` list it doesn't care about would
be exactly the kind of unjustified ceremony the constitution's scope
discipline forbids. `GET /api/agents` (T370) still returns a well-formed
`AgentDescriptor` for those, because every field it requires
(`agent_type`, `contract_version`, `tools_used`) has a default.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from anchor.core.determinism.actions import Action
from anchor.core.determinism.context import StepContext

DecideNextStep = Callable[[StepContext], Awaitable[Action] | Action]

_DEFAULT_CONTRACT_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class AgentDescriptor:
    """`contracts/openapi.yaml` `AgentDescriptor` — everything `GET /api/agents`
    (T370) reports about one registered agent.
    """

    agent_type: str
    contract_version: str = _DEFAULT_CONTRACT_VERSION
    description: str = ""
    expected_step_count: int | None = None
    tools_used: tuple[str, ...] = field(default_factory=tuple)
    stubbed_model: bool = False


_REGISTRY: dict[str, DecideNextStep] = {}
_DESCRIPTORS: dict[str, AgentDescriptor] = {}


def register(
    name: str,
    fn: DecideNextStep,
    *,
    description: str = "",
    contract_version: str = _DEFAULT_CONTRACT_VERSION,
    expected_step_count: int | None = None,
    tools_used: tuple[str, ...] = (),
    stubbed_model: bool = False,
) -> None:
    _REGISTRY[name] = fn
    _DESCRIPTORS[name] = AgentDescriptor(
        agent_type=name,
        description=description,
        contract_version=contract_version,
        expected_step_count=expected_step_count,
        tools_used=tools_used,
        stubbed_model=stubbed_model,
    )


def resolve(name: str) -> DecideNextStep | None:
    return _REGISTRY.get(name)


def is_registered(name: str) -> bool:
    return name in _REGISTRY


def list_agents() -> list[AgentDescriptor]:
    """`GET /api/agents` (T370). Sorted by name so the response is stable
    across calls regardless of registration order.
    """
    if not _DESCRIPTORS:
        from anchor.runtime.agents import register_all

        register_all()
    return [_DESCRIPTORS[name] for name in sorted(_DESCRIPTORS)]
