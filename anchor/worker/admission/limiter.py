"""Per-worker admission control (plan.md P6.4, T298, T326; FR-004).

Checked from the worker's own in-process count — `RunCounter` in
`anchor.worker.loop` — never from `workers.current_run_count`, which is
telemetry only (T174, data-model.md §5): using that column to decide
admission would be a second source of truth for something the worker
already knows about itself without asking the database. This module takes
plain integers rather than importing `RunCounter` directly, so it has
nothing to import from `anchor.worker.loop` and `loop.py` can import this
module without a cycle.
"""

from __future__ import annotations


def has_capacity(*, current_count: int, capacity: int) -> bool:
    """Whether this worker may attempt another claim right now."""
    return current_count < capacity
