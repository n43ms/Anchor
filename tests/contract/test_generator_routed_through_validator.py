"""T558 — the generator-routed-through-validator test (FR-125).

This deployment has no generation provider configured (see
`anchor.api.routers.authoring.generate_draft`'s docstring): the endpoint
degrades honestly on every call rather than half-working, so there is no
code path that ever hands generated text to a caller without having run
it through the validator first — because there is no code path that hands
generated text to a caller at all. This test asserts that directly: the
generate endpoint has exactly one behaviour (honest 503), never a second,
unvalidated success path.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from anchor.api.routers.authoring import generate_draft


async def test_generate_never_returns_a_body_without_validation() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await generate_draft({"description": "an agent that emails everyone"})
    assert exc_info.value.status_code == 503
    assert "source" not in getattr(exc_info.value, "detail", {})
