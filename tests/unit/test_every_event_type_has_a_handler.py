"""T117 — every one of the 17 `EventType` members has an explicit fold
handler, so a new type added to the enum without one is caught here rather
than silently absorbed by a default branch.
"""

from __future__ import annotations

from anchor.core.events.types import EventType
from anchor.core.replay.handlers import ALL_EVENT_TYPES_HAVE_HANDLERS, handler_for


def test_all_event_types_have_handlers() -> None:
    assert ALL_EVENT_TYPES_HAVE_HANDLERS


def test_handler_for_every_type_is_resolvable() -> None:
    for event_type in EventType:
        assert callable(handler_for(event_type))
