"""T232 — the same step re-derives an identical idempotency key on replay,
including when `ctx.new_id()` feeds the arguments. Pure: no database
needed, since `ctx.new_id()` only reads back a journaled value already
present in the reconstructed `RunContext`.
"""

from __future__ import annotations

from anchor.core.determinism.context import StepContext
from anchor.core.journal.keys import derive_key
from anchor.core.replay.context import RunContext


def test_new_id_fed_key_is_stable_across_a_simulated_replay() -> None:
    # "Attempt 1": nothing recorded yet, ctx.new_id() generates fresh.
    first_context = RunContext()
    first_ctx = StepContext(
        run_id=42,
        epoch=0,
        worker_id="worker-a#1",
        step_index=0,
        input={},
        run_context=first_context,
    )
    generated_id = first_ctx.new_id()
    args_attempt_1 = {"ticket_ref": generated_id}
    key_attempt_1 = derive_key(42, 0, "create_ticket", args_attempt_1)

    # "Attempt 2": a replay after a crash, with the same value already
    # journaled (this is exactly what `core.replay.reconstruct` would
    # produce by folding the recorded NONDET_RECORDED entry).
    replayed_context = RunContext(nondet_by_step_kind={(0, "id"): [generated_id]})
    second_ctx = StepContext(
        run_id=42,
        epoch=1,  # a different worker/epoch after the handoff — must not matter
        worker_id="worker-b#1",
        step_index=0,
        input={},
        run_context=replayed_context,
    )
    replayed_id = second_ctx.new_id()
    args_attempt_2 = {"ticket_ref": replayed_id}
    key_attempt_2 = derive_key(42, 0, "create_ticket", args_attempt_2)

    assert replayed_id == generated_id, "replay must hand back the recorded id, not a new one"
    assert key_attempt_2 == key_attempt_1, (
        "the idempotency key must be stable across replay even though it is derived from "
        "a generated id — this is the specific failure D-41/FR-033 exist to prevent"
    )


def test_a_regenerated_id_would_have_produced_a_different_key() -> None:
    """Sanity check on the test above: if replay's read-back mechanism did
    *not* exist and `ctx.new_id()` generated a fresh value on the second
    attempt, the derived key would differ — proving the assertion above is
    actually exercising the read-back path rather than being trivially true.
    """
    ctx_a = StepContext(
        run_id=1, epoch=0, worker_id="w#1", step_index=0, input={}, run_context=RunContext()
    )
    ctx_b = StepContext(
        run_id=1, epoch=0, worker_id="w#1", step_index=0, input={}, run_context=RunContext()
    )

    key_a = derive_key(1, 0, "create_ticket", {"ticket_ref": ctx_a.new_id()})
    key_b = derive_key(1, 0, "create_ticket", {"ticket_ref": ctx_b.new_id()})

    assert key_a != key_b
