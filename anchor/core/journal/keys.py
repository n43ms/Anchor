"""Idempotency key derivation (plan.md P5.2, T250-T252; research.md D-12, D-41).

`idempotency_key = sha256(canonical_json([run_id, step_index, action_name, args]))`.

**Framing is an array, never a delimited string** (D-41). Hashing
`f"{run_id}:{step_index}:{action_name}:{args_json}"` would make the framing
ambiguous by construction — a tool named `"a:1"` and one named `"a"` called
with an argument set that happens to canonicalize to `'1"` could collide, and
the fix would be an argument about which characters are legal in a tool
name. A JSON array has no such ambiguity: `canonical_json` already gives
each element an unambiguous boundary, so two structurally different
4-tuples cannot canonicalize to the same array text.
"""

from __future__ import annotations

import hashlib
from typing import Any

from anchor.core.journal.canonical import canonical_json

_DISPLAY_FORM_LENGTH = 12


def derive_key(run_id: int, step_index: int, action_name: str, args: dict[str, Any]) -> str:
    """The full SHA-256 hex digest — the only value ever used for lookup,
    comparison, or the `tool_journal` primary key.
    """
    framed = canonical_json([run_id, step_index, action_name, args])
    return hashlib.sha256(framed.encode("utf-8")).hexdigest()


def derive_args_hash(args: dict[str, Any]) -> str:
    """SHA-256 over the canonical arguments alone, independent of run,
    step, or tool name. Backs the registry's "last used" display and any
    cross-step comparison of "were these the same arguments" — a question
    the full idempotency key cannot answer, because it is deliberately
    scoped to one run and one step.
    """
    return hashlib.sha256(canonical_json(args).encode("utf-8")).hexdigest()


def display_form(idempotency_key: str) -> str:
    """A truncated form for the UI only. **Never** used as an identity**:
    no lookup, comparison, or constraint may key on this value
    (`tests/unit/test_key_display_form_never_identity.py`, T252) — two
    distinct full keys sharing a truncated prefix must never be treated as
    the same effect.
    """
    return idempotency_key[:_DISPLAY_FORM_LENGTH]
