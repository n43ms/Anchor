"""T105 — replay determinism, asserted by canonical-JSON hash.

Folding the same ordered log twice must produce bit-identical reconstructed
state. A field-by-field comparison would silently omit whatever field a
future change forgets to add to the assertion; hashing the whole canonical
projection cannot (research.md D-25).
"""

from __future__ import annotations

import pytest

from anchor.core.replay.reconstruct import canonical_state_hash, reconstruct
from tests.fixtures import all_fixture_names, load


@pytest.mark.parametrize("name", all_fixture_names())
def test_folding_the_same_log_twice_is_bit_identical(name: str) -> None:
    events = load(name)
    first = canonical_state_hash(reconstruct(events))
    second = canonical_state_hash(reconstruct(events))
    assert first == second


def test_hash_distinguishes_genuinely_different_final_state() -> None:
    """A hash function that returned the same value for every input would
    make the equality assertion above vacuous. Guard against that using a
    pair that must differ: `completed_short` finishes both of its steps,
    `truncated_mid_step` finishes only the first.

    This is deliberately **not** an all-pairs-distinct assertion:
    `with_skipped_steps` and `reclaimed_after_expiry` describe the same
    completed steps, arguments, and results — the only difference is an
    intervening `STEP_SKIPPED_ON_REPLAY`, which (like `LEASE_RENEWED`,
    T119) carries no reconstructed state by design. Two fixtures producing
    the same canonical hash there is correct, not a collision.
    """
    completed = canonical_state_hash(reconstruct(load("completed_short")))
    truncated = canonical_state_hash(reconstruct(load("truncated_mid_step")))
    assert completed != truncated
