"""T072 — the stub returns deterministic completions with configured latency,
and `LLM_CALLED.stubbed` is `true` (FR-036, D-55)."""

from __future__ import annotations

import time

import pytest

from anchor.runtime.tools.model import StubAdapter


@pytest.mark.asyncio
async def test_stub_is_deterministic_and_reports_stubbed() -> None:
    adapter = StubAdapter(latency_ms=10)
    messages = [{"role": "user", "content": "hello"}]

    first = await adapter.complete(messages, None)
    second = await adapter.complete(messages, None)

    assert first.text == second.text
    assert first.stubbed is True


@pytest.mark.asyncio
async def test_stub_respects_configured_latency() -> None:
    adapter = StubAdapter(latency_ms=30)
    start = time.monotonic()
    await adapter.complete([{"role": "user", "content": "x"}], None)
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms >= 25
