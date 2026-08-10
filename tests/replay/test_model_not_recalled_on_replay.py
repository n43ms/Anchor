"""T114 — a journaled `LLM_CALLED` returns the recorded completion on
replay with **no provider call at all** (FR-034).

A step that reached `LLM_CALLED` but crashed before `STEP_COMPLETED` is
retried at the same step_index. `ctx.call_model` must return the recorded
response without invoking the model adapter again — proven here by an
adapter that raises if it is ever called a second time.
"""

from __future__ import annotations

from typing import Any

import pytest

from anchor.core.determinism.context import StepContext
from anchor.core.replay.context import ModelCompletion, RunContext


class _FailIfCalledAdapter:
    async def complete(self, messages: list[dict[str, Any]], model: str | None) -> Any:
        raise AssertionError(
            "the provider must not be called when a completion is already journaled"
        )


@pytest.mark.asyncio
async def test_call_model_returns_recorded_response_without_calling_the_adapter() -> None:
    run_context = RunContext()
    run_context.model_calls_by_step[0] = ModelCompletion(
        step_index=0, response="stubbed-completion-abc123", model="stub-v1", stubbed=True
    )

    ctx = StepContext(
        run_id=1,
        epoch=1,
        worker_id="worker-b#1",
        step_index=0,
        input={},
        run_context=run_context,
        model_adapter=_FailIfCalledAdapter(),
    )

    result = await ctx.call_model([{"role": "user", "content": "hello"}])

    assert result == "stubbed-completion-abc123"
