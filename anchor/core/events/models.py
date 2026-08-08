"""The `RunEvent` envelope (data-model.md §2, §11)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from anchor.core.events.types import EventType


class RunEvent(BaseModel):
    run_id: int
    seq: int
    type: EventType
    payload: dict[str, Any]
    epoch: int
    worker_id: str
    step_index: int | None = None
    created_at: datetime
