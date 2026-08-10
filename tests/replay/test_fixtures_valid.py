"""T140 — every fixture log parses against the payload models.

A malformed fixture must fail here, at fixture-validation time, not deep
inside a replay test's assertion where the failure is hard to attribute.
"""

from __future__ import annotations

import pytest

from anchor.core.events.payloads import PAYLOAD_MODELS
from tests.fixtures import all_fixture_names, load


@pytest.mark.parametrize("name", all_fixture_names())
def test_fixture_parses_and_every_payload_matches_its_model(name: str) -> None:
    events = load(name)
    assert events, f"fixture {name!r} is empty — a fixture that parses zero events proves nothing"
    for event in events:
        model = PAYLOAD_MODELS[event.type.value]
        model.model_validate(event.payload)


def test_the_walk_actually_covers_fixtures() -> None:
    names = all_fixture_names()
    assert len(names) >= 5, f"expected at least 5 fixtures, found {len(names)} — check logs/ glob"
