"""T559 — the honest-degradation test (FR-126).

With no provider key configured, the editor and validator work and the
generate control is disabled with a plain statement of why.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from anchor.api.authoring.validator import validate
from anchor.api.routers.authoring import generate_draft, validate_draft


async def test_generate_reports_unavailable_with_a_plain_reason() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await generate_draft({"description": "anything"})
    assert exc_info.value.status_code == 503
    body = exc_info.value.detail
    assert isinstance(body, dict)
    assert body["error"] == "generation_unavailable"
    assert "no generation provider is configured" in body["message"]


async def test_validate_keeps_working_when_generation_is_unavailable() -> None:
    result = await validate_draft({"source": "def decide_next_step(ctx):\n    return Done({})\n"})
    assert result["valid"] is True


def test_validator_itself_is_unaffected_by_provider_configuration() -> None:
    report = validate("def decide_next_step(ctx):\n    return Done({})\n")
    assert report.valid is True
