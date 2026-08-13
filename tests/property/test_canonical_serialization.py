"""T229-T230 — canonical serialization stability, the property test that
protects the entire idempotency mechanism (FR-038). No database needed: this
is a pure function of its input.
"""

from __future__ import annotations

import json
import math
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from anchor.core.journal.canonical import CanonicalizationError, canonical_json

# A recursive JSON-native value strategy: dict / list / str / int / float /
# bool / None, nested a few levels deep — exactly the universe
# `canonicalize` accepts without complaint.
_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**12), max_value=10**12),
    st.floats(allow_nan=False, allow_infinity=False, width=64),
    st.text(min_size=0, max_size=20),
)
_json_values = st.recursive(
    _scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
    ),
    max_leaves=20,
)


@given(value=_json_values)
def test_canonical_json_is_a_pure_function_of_structure(value: object) -> None:
    """Calling twice on the same structure (independent of Python object
    identity) always produces byte-identical output — the baseline
    determinism property everything else in this module composes on top of.
    """
    assert canonical_json(value) == canonical_json(json.loads(json.dumps(value)))


@given(d=st.dictionaries(st.text(min_size=1, max_size=10), _json_values, min_size=1, max_size=6))
def test_mapping_key_order_is_irrelevant(d: dict[str, object]) -> None:
    """Any permutation of a mapping's key order canonicalizes identically —
    the property FR-038 exists to name directly."""
    shuffled = dict(reversed(list(d.items())))
    assert canonical_json(d) == canonical_json(shuffled)


def test_nesting_traversal_order_is_irrelevant() -> None:
    a = {"outer": {"a": 1, "b": 2}, "z": [1, 2, 3]}
    b = {"z": [1, 2, 3], "outer": {"b": 2, "a": 1}}
    assert canonical_json(a) == canonical_json(b)


@pytest.mark.parametrize(
    "numerals",
    [
        (1.5, 1.50, 1.500000),
        (0.1, 0.10),
        (100.0, 1e2),
    ],
)
def test_numeric_formatting_is_irrelevant(numerals: tuple[float, ...]) -> None:
    """Different literal spellings that parse to the same float hash
    identically — Python's shortest-round-trip float repr is what makes
    this true without a bespoke formatter (FR-038)."""
    outputs = {canonical_json({"x": n}) for n in numerals}
    assert len(outputs) == 1


def test_unicode_nfc_normalization() -> None:
    composed = "é"  # "e" + combining acute accent
    precomposed = "é"  # "é" as one codepoint
    assert composed != precomposed  # sanity: genuinely different code points
    assert unicodedata.normalize("NFC", composed) == precomposed  # sanity: NFC unifies them
    assert canonical_json({"name": composed}) == canonical_json({"name": precomposed})


@pytest.mark.parametrize(
    "bad_value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        (1, 2, 3),
        {1, 2, 3},
        frozenset({1, 2}),
        datetime.now(UTC),
        Decimal("1.5"),
        b"raw bytes",
    ],
)
def test_non_canonical_types_raise_with_a_path(bad_value: object) -> None:
    """T230: every non-JSON-native type raises at call time, carrying the
    JSON path to the offending value — never coerced into something that
    merely looks plausible."""
    with pytest.raises(CanonicalizationError) as excinfo:
        canonical_json({"args": {"nested": [bad_value]}})
    assert excinfo.value.path == "args.nested[0]"


def test_nan_and_infinity_are_rejected_even_though_math_module_agrees_they_are_floats() -> None:
    assert math.isnan(float("nan"))
    with pytest.raises(CanonicalizationError):
        canonical_json(float("nan"))
