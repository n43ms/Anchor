"""The `ModelAdapter` protocol and the stub adapter (D-55).

The stub is the default on every path — demo, chaos, and tests — and a real
provider adapter is unreachable from any test by construction (tasks.md
"No test may make a real model-provider call").
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

STUB_LATENCY_MS = 50


@dataclass(frozen=True, slots=True)
class ModelResponse:
    text: str
    model: str
    stubbed: bool


class StubAdapter:
    """Deterministic, latency-configured completions with no network call.

    The completion is derived from a hash of the prompt, so the same
    messages always produce the same stubbed text — useful for the demo
    agents' behaviour to be reproducible without a provider key.
    """

    def __init__(self, *, latency_ms: int = STUB_LATENCY_MS, model: str = "stub-v1") -> None:
        self._latency_ms = latency_ms
        self._model = model

    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> ModelResponse:
        import asyncio

        await asyncio.sleep(self._latency_ms / 1000)
        digest = hashlib.sha256(
            json.dumps(messages, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:12]
        return ModelResponse(
            text=f"stubbed-completion-{digest}",
            model=model or self._model,
            stubbed=True,
        )
