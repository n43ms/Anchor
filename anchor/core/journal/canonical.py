"""Canonical JSON serialization (plan.md P5.1, T247-T249).

This module is the mechanism the entire idempotency scheme rests on: two
structurally identical tool-call argument sets — in any mapping key order,
any nesting traversal order, any numeric formatting a caller happened to
construct them in — must serialize to **exactly** the same bytes, so that
`core.journal.keys.derive` hashes them to the same idempotency key. Protected
by a `hypothesis` property test (`tests/property/test_canonical_serialization.py`,
T229) rather than by examples, because the failure mode this guards against is
not "the function is wrong" but "the function is right for every case anyone
thought to write down and wrong for the one nobody did."

**Serialization drift does not error — it double-executes.** If two
structurally equivalent argument sets ever serialized differently, the
derived idempotency keys would differ too, `tool_journal`'s three-state
lookup would see `NeverAttempted` on what is actually a retried step, and the
side effect would run again. There is no exception raised anywhere in that
path; the only symptom is a `demo_effects` row count that should not exist.
That is why this module rejects every type it cannot canonicalize
deterministically rather than serializing it "as best it can" (T230): a
`NaN`, an `Infinity`, a `set` (unordered by definition), a `tuple` (JSON does
not distinguish it from a list, so accepting it would let list-shaped and
tuple-shaped arguments collide or diverge depending on which one is JSON
already round-tripped), a `datetime` (whose string form depends on a
formatting choice this module does not get to make on the caller's behalf),
and a `Decimal` (whose textual precision is not preserved by the float it
would otherwise become) all raise **at call time**, carrying the JSON path to
the offending value, rather than being coerced into something that merely
looks plausible.
"""

from __future__ import annotations

import json
import math
import unicodedata
from typing import Any

# JSON-native scalar types this module accepts without complaint. `bool` is
# listed explicitly even though it is a subclass of `int` in Python, so that
# `isinstance(x, int)` below never has to special-case it — `bool` already
# round-trips through `json.dumps` as `true`/`false`.
_JSON_SCALARS = (str, int, float, bool, type(None))


class CanonicalizationError(TypeError):
    """Raised when a value cannot be canonicalized deterministically.

    Carries `path`, the JSON-path-like breadcrumb to the offending value
    (e.g. `args.recipients[2]`), because "somewhere in this argument tree"
    is not an actionable error message and the whole point of raising here
    instead of downstream is to be actionable.
    """

    def __init__(self, path: str, value: Any) -> None:
        self.path = path
        self.value = value
        super().__init__(
            f"cannot canonicalize value of type {type(value).__name__} at {path!r}: {value!r}"
        )


def _walk(value: Any, path: str) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, str):
        # NFC normalization: two strings that render identically but differ
        # in Unicode composition (e.g. "é" as one codepoint vs "e" + a
        # combining accent) must hash identically — they are the same
        # argument to any tool that receives them.
        return unicodedata.normalize("NFC", value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise CanonicalizationError(path, value)
        return value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(f"{path}.<key {key!r}>", key)
            out[key] = _walk(item, f"{path}.{key}" if path else key)
        return out
    if isinstance(value, list):
        return [_walk(item, f"{path}[{i}]") for i, item in enumerate(value)]
    # Everything else — tuple, set, frozenset, datetime, Decimal, bytes,
    # arbitrary objects — is rejected explicitly rather than falling through
    # to a generic serializer that would guess at a representation.
    raise CanonicalizationError(path, value)


def canonicalize(value: Any) -> Any:
    """Validate and normalize `value` into a structure containing only
    JSON-native types, with every string NFC-normalized. Raises
    `CanonicalizationError` naming the path to the first offending value
    found, depth-first.
    """
    return _walk(value, "")


def canonical_json(value: Any) -> str:
    """Canonical JSON text for `value`: sorted keys at every nesting level,
    compact separators, ASCII-safe, NFC-normalized strings.

    `sort_keys=True` on `json.dumps` sorts recursively at every level, so
    mapping key order and nesting traversal order both collapse to the same
    output regardless of how the caller built the structure. Float
    formatting collapses too, but for a different reason: once a numeral
    has been parsed into a Python `float`, `json.dumps` renders it with
    `float.__repr__`, which is shortest-round-trip and therefore identical
    for any two numerals that parsed to the same value — the canonicalizer
    does not need its own float formatter, because Python's already is one.
    """
    normalized = canonicalize(value)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
