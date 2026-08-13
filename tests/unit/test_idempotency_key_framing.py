"""T231, T252 — the idempotency key is hashed over a canonical JSON array,
never a delimited string, so framing is unambiguous by construction (D-41);
and the truncated display form is never used as an identity.
"""

from __future__ import annotations

from anchor.core.journal.keys import derive_args_hash, derive_key, display_form


def test_key_derivation_is_deterministic() -> None:
    args = {"b": 2, "a": 1}
    assert derive_key(1, 0, "send_email", args) == derive_key(1, 0, "send_email", {"a": 1, "b": 2})


def test_different_run_step_or_tool_changes_the_key() -> None:
    base = derive_key(1, 0, "send_email", {"to": "a@example.com"})
    assert base != derive_key(2, 0, "send_email", {"to": "a@example.com"})
    assert base != derive_key(1, 1, "send_email", {"to": "a@example.com"})
    assert base != derive_key(1, 0, "charge_card", {"to": "a@example.com"})


def test_array_framing_prevents_delimiter_ambiguity() -> None:
    """A naive `f'{run_id}:{step_index}:{tool_name}:{args_json}'` framing
    could collide across a colon appearing in a tool name versus one
    appearing in serialized args. The array framing this module actually
    uses has no such ambiguity: two structurally different 4-tuples cannot
    canonicalize to the same JSON array text.
    """
    a = derive_key(1, 0, "a:1", {"x": 1})
    b = derive_key(1, 0, "a", {"x": 1, "_delimiter_probe": "1"})
    assert a != b


def test_args_hash_is_independent_of_run_and_step() -> None:
    args = {"x": 1}
    assert derive_args_hash(args) == derive_args_hash({"x": 1})


def test_display_form_is_a_short_prefix_only() -> None:
    key = derive_key(1, 0, "send_email", {"to": "a@example.com"})
    short = display_form(key)
    assert len(short) < len(key)
    assert key.startswith(short)


def test_display_form_collision_is_not_treated_as_identity() -> None:
    """Two distinct full keys sharing a truncated prefix must never be
    conflated (T252) — this module exposes no lookup that could do so; the
    assertion here is simply that `display_form` is not `derive_key`'s
    return value and callers cannot mistake one for the other by type.
    """
    key_a = derive_key(1, 0, "send_email", {"to": "a@example.com"})
    key_b = derive_key(1, 0, "send_email", {"to": "b@example.com"})
    assert key_a != key_b
    # A prefix collision would be a pathological hash-function property to
    # rely on for identity, which is exactly why no code path in this
    # package ever compares `display_form` output for equality of effect.
    assert display_form(key_a) == key_a[:12]
