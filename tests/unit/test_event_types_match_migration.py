"""T073 — `EventType` matches the migration's `CHECK` constraint list
exactly, so the two cannot drift (FR-025)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from anchor.core.events.types import EventType

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "ops" / "migrations" / "versions" / "001_foundation.py"
)


def _load_migration_module():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("_migration_001_foundation", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_event_type_enum_matches_migration_check_list() -> None:
    module = _load_migration_module()
    assert {t.value for t in EventType} == set(module._EVENT_TYPES)
