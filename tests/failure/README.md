# Failure matrix coverage

Maps each row of `anchor-spec.md` §9's failure matrix to the test that induces it and asserts the
documented handling.

| Failure mode | Test | Assertion |
|---|---|---|
| Worker killed mid-step | [`test_kill_and_resume.py`](./test_kill_and_resume.py) | A different worker claims, replays, and resumes from the last completed step |
| Worker stalls but is alive (zombie) | [`test_zombie_worker_fenced.py`](./test_zombie_worker_fenced.py) | The zombie's write is rejected by epoch fencing and it withdraws without retrying |
| Crash between tool intent and result | [`test_uncertainty_window.py`](./test_uncertainty_window.py) | Each tool's declared safety policy resolves the uncertainty window correctly |
| Two workers race to claim the same run | [`test_two_workers_race_same_run.py`](./test_two_workers_race_same_run.py) | `SELECT ... FOR UPDATE SKIP LOCKED` admits exactly one claim |
| Duplicate event append | [`test_duplicate_seq_under_contention.py`](./test_duplicate_seq_under_contention.py) | The `UNIQUE (run_id, seq)` constraint rejects the second write |
| Database unavailable | [`test_health_db_unreachable.py`](./test_health_db_unreachable.py) | `/api/health` reports `503` and the API degrades rather than crashing |
| Renewal rejected mid-lease | [`test_renewal_rejected_cancels_run_task.py`](./test_renewal_rejected_cancels_run_task.py) | A fenced renewal cancels the run's task immediately rather than continuing to execute |
| Sibling task must be cancelled together | [`test_taskgroup_cancels_sibling.py`](./test_taskgroup_cancels_sibling.py) | Cancelling one task in the run's task group cancels the other |
| Append attempted after cancellation | [`test_append_checks_cancellation.py`](./test_append_checks_cancellation.py) | A cancelled run's task cannot append a further event |
| Worker incarnation identity | [`test_worker_incarnation_never_reused.py`](./test_worker_incarnation_never_reused.py) | A restarted worker process never reuses a prior incarnation id |
| Chaos run abandoned mid-restart | [`test_chaos_run_abandoned_on_restart.py`](./test_chaos_run_abandoned_on_restart.py) | A chaos run left `running` with a stale heartbeat is reconciled at the next startup check |
| Long step exceeding the lease | [`test_long_step_not_fenced.py`](./test_long_step_not_fenced.py) | A step that legitimately runs long is not fenced while its renewal keeps succeeding |
| Event loop blocked | [`test_blocked_event_loop_is_reclaimed.py`](./test_blocked_event_loop_is_reclaimed.py) | A worker whose event loop is blocked past its lease is reclaimed by another worker |
| Effect recorded with unrecorded inputs | [`test_no_effect_with_unrecorded_inputs.py`](./test_no_effect_with_unrecorded_inputs.py) | A side effect cannot commit unless its inputs were already journaled |
| Duplicate demo effect | [`test_demo_effects_unique.py`](./test_demo_effects_unique.py) | `demo_effects`' `UNIQUE (idempotency_key)` constraint rejects a second execution |
| Tool declaration conflict across a rolling deploy | [`test_tool_declaration_conflict.py`](./test_tool_declaration_conflict.py) | A tool re-registered with a different declaration hash is refused fleet-wide, not silently overwritten |
| Oversized payload | [`test_payload_ceiling.py`](./test_payload_ceiling.py) | A payload past the configured ceiling is rejected before it reaches the log |
| Intent must precede invocation | [`test_intent_committed_before_invocation.py`](./test_intent_committed_before_invocation.py) | `TOOL_INTENT` commits before the tool function is ever called |

Rows resolved by pure log-derived reconstruction rather than a fault-injection scenario (e.g. "step
fails permanently") are covered by the replay and unit suites instead — see
[`tests/README.md`](../README.md) for the full suite layout.
