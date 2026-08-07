# Quickstart and validation guide

**Feature**: 001-anchor-durable-execution-runtime
**Purpose**: the runnable scenarios that prove each phase works end to end. Every scenario names the
commands, the expected outcome, and the success criterion from [`spec.md`](./spec.md) it discharges.

This is a validation guide, not an implementation guide. Schemas live in
[`data-model.md`](./data-model.md), interfaces in [`contracts/`](./contracts/), and decisions in
[`research.md`](./research.md).

---

## Prerequisites

| Requirement | Version | Note |
|---|---|---|
| Docker + Compose | current | Brings up PostgreSQL, Redis, API, three workers, console |
| Python | 3.12 | Only needed to run tests or the harness outside Docker |
| `uv` | current | `uv sync` installs the locked dependency set |
| Node | 22 LTS | Only needed to run the console outside Docker |
| `pnpm` | current | |

No API keys. No accounts. No external service. Model calls are stubbed on every path that matters, so
the demo, chaos, and test paths cost compute and nothing else.

## Setup

```bash
git clone <repo> && cd anchor
docker compose up            # migrate (one-shot) → postgres · redis · api · worker×3 · web
```

Console at `http://localhost:3000`, API at `http://localhost:8000`. **Migrations run in a one-shot
`migrate` service that the API and workers wait on** — no long-running process applies migrations
itself, and every process refuses to start if the applied revision differs from the one its code was
built against (D-45). **`docker compose up` sets `ANCHOR_AUTHORING_EXECUTE=true`, which is what makes
this local mode**; every other deployment leaves it unset and is therefore demonstration mode
(fail-closed).

Verify the fleet before anything else:

```bash
curl -s localhost:8000/api/health | jq '{database_reachable, worker_count, deployment_mode, degraded, schema_revision}'
# → database_reachable: true, worker_count: 3, deployment_mode: "local", degraded: false
curl -s localhost:8000/api/workers | jq -r '.items[] | "\(.id)\t\(.label)#\(.incarnation)\t\(.code_version)"'
# → worker-a#1  worker-a#1  <sha>   — ids are unique per process lifetime, never reused
```

If `worker_count` is below 3, stop and fix it. **A single-worker environment hides every bug this
project exists to solve**, and every scenario below assumes three.

---

## V1 — The log is the spine *(phase 1)*

```bash
RUN=$(curl -sX POST localhost:8000/api/runs \
      -H 'content-type: application/json' \
      -d '{"agent_type":"demo_short","input":{},"is_demo":true}' | jq -r .id)
curl -s "localhost:8000/api/runs/$RUN/events" | jq -r '.items[] | "\(.seq)\t\(.type)\t\(.worker_id)\tepoch=\(.epoch)"'
```

**Expected**: `seq` starts at 1 and increases by exactly 1 with no gaps. `RUN_SUBMITTED` is written by
`api`; everything after it by one `worker-*` id at one epoch. Each step shows `STEP_STARTED` →
(`TOOL_INTENT` → `TOOL_RESULT` | `LLM_CALLED`) → `STEP_COMPLETED`. The run ends `RUN_COMPLETED`.

**Also assert nothing lives outside the log**: no table other than `run_events`, `tool_journal`, and
`demo_effects` records what happened during the run.

→ discharges **SC-004** (partially; the chaos corpus discharges it fully).

## V2 — Replay after death *(phase 2 — the hard gate)*

```bash
RUN=$(curl -sX POST localhost:8000/api/runs -H 'content-type: application/json' \
      -d '{"agent_type":"demo_short","is_demo":true}' | jq -r .id)
sleep 8                                                    # let it get several steps in
OWNER=$(curl -s localhost:8000/api/runs/$RUN | jq -r .owner_worker_id)
curl -sX POST "localhost:8000/api/workers/$OWNER/kill"     # hard kill: no cleanup, like a crash
```

**Expected, in order**:

1. Appends stop. `GET /api/runs/$RUN` shows `orphaned: true` once the lease elapses.
2. A different worker appends `RUN_CLAIMED` with `reason: "reclaimed_after_lease_expiry"` and an
   epoch one higher than before.
3. `REPLAY_COMPLETED` records `steps_replayed` equal to the number of steps that had completed, plus
   `journal_entries_loaded` and `nondet_values_loaded`.
4. Execution continues from `last_completed_step_index + 1` — **not** from step 1.
5. `GET /api/runs/$RUN/effects` shows **exactly one row per logical side effect**, no duplicates.
6. The killed worker is back in `GET /api/workers` within seconds — **as a new id**, `worker-a#2`,
   with the same label and a higher incarnation. The old row remains, so the restart is visible in the
   fleet history rather than overwritten.

**Do not proceed to phase 3 until this is clean.** Everything else in the project is elaboration on
this behaviour.

→ discharges **SC-001** (single-kill case), **SC-016**.

## V3 — Claim contention *(phase 3)*

```bash
uv run pytest tests/concurrency -q
```

**Expected**: with N workers contending for one available run, exactly one claim succeeds, repeated
under load. No test asserts "usually" or "eventually" — the property is exact, because `SKIP LOCKED`
in one transaction makes it exact.

Also verify renewal is independent of step duration:

```bash
uv run pytest tests/failure/test_long_step_not_fenced.py -q
```

**Expected**: a step lasting longer than `lease_duration` is **not** fenced, because the background
renewer keeps extending. This is the behaviour that makes two configuration profiles possible at all.

## V4 — The zombie worker is fenced *(phase 4 — the most valuable phase)*

```bash
uv run pytest tests/failure/test_zombie_worker_fenced.py -q
```

**Expected**: a worker holding a stale epoch attempts an append and

1. the database raises `SQLSTATE AN001` — the rejection comes from the trigger, not from Python;
2. **no partial write landed** — the run's `last_seq` is unchanged;
3. the fenced worker performs **no subsequent write of any kind**, including no error event through
   that run's log;
4. it does not retry;
5. it returns to the idle pool and claims other work normally.

Then verify the renewer path, which is a different race:

```bash
uv run pytest tests/failure/test_renewal_rejected_cancels_run_task.py -q
uv run pytest tests/failure/test_blocked_event_loop_is_reclaimed.py -q
```

**Expected**: a rejected renewal cancels the execution task and **no write follows the
cancellation**; and a simulated blocked event loop results in lease expiry and reclaim, **not** in
continued renewal — the renewer is incapable of signalling liveness that outlives a stalled process.

→ discharges **SC-005**, and it is the phase behind **SC-018**.

## V5 — Effectively-once, including the uncertainty window *(phase 5)*

```bash
uv run pytest tests/property/test_canonical_serialization.py -q      # the test that protects everything
uv run pytest tests/failure/test_uncertainty_window.py -q            # one case per declared policy
```

**Expected from the property test**: structurally identical arguments in any key order, any nesting
traversal, and any numeric formatting hash **identically**; non-JSON-native types raise at call time
with the path to the offending value.

**Expected from the uncertainty tests**, one per category:

| Injected | Tool safety | Outcome |
|---|---|---|
| Crash between intent and result | `retry_safe` | Re-executed with the key passed through; one effect row |
| Crash between intent and result | `reconcilable` | Reconciliation query runs; branch taken; `resolution` recorded on the journal row |
| Crash between intent and result | `unsafe` | Run becomes `needs_review`, halts, holds **no lease**, and appears on the Needs review page with the ambiguous call named |

Then the honest-resolution path:

```bash
curl -sX POST localhost:8000/api/runs/$RUN/resolve \
     -H 'content-type: application/json' -d '{"resolution":"mark_not_executed","note":"checked inbox"}'
```

**Expected**: an event attributed to `worker_id: "operator"` at the run's current epoch, the journal
row marked unexecuted, and the run returned to `pending` for a worker to pick up.

The ground truth, which needs no trust in the log:

```bash
curl -s localhost:8000/api/runs/$RUN/effects | jq '.total'      # → exactly the expected count
```

→ discharges **SC-001**, **SC-007** (the uncertainty rows).

## V6 — Load and repeated failure *(phase 6)*

```bash
uv run pytest tests/failure -q            # one module per row of the §9 failure matrix
```

**Expected**: every row of the failure matrix has a module, it induces the failure deliberately, and
it asserts the documented handling. Specifically verify the two that are easiest to get wrong:

- **Database unavailable** → nothing executes, workers back off, and **no side effect occurred without
  a durable record**. Failing closed is the correct behaviour and the test asserts it as such.
- **Fleet saturated** → excess runs stay `pending`; no worker exceeds its capacity; nothing degrades
  uniformly.

→ discharges **SC-007**.

## V7 — The console tells the truth *(phase 7)*

```bash
pnpm --dir web test          # includes the five required mock states
pnpm --dir web dev           # then open the preview route
```

**Manual checks that cannot be automated and must not be skipped:**

1. **Grayscale.** Set the display to grayscale and confirm replayed segments are still
   distinguishable from executed ones. → **SC-010**
2. **Reduced motion.** Enable `prefers-reduced-motion` and confirm no information is lost: the
   explainer falls back to a labelled static frame, the pulse becomes a static state color, and the
   orphaned gap keeps its countdown as plain changing text. → **SC-011**
3. **The orphaned mock.** Confirm the state where no segment has `ended_at === null` renders the gap,
   the hairline, and the countdown — not an error and not an empty state.
4. **No bare colored dots** anywhere. Every status carries an icon and a label.
5. **Render it and look at it.** Open every view at 40 steps and check for label collisions, overflow,
   and a timeline that still reads.

## V8 — Measured proof *(phase 8)*

```bash
uv run python -m anchor.chaos.harness --workers 3 --duration 120 --kill-rate 12 \
                                      --tool-failure-rate 0.1 --uncertainty-crash-rate 0.05
curl -s localhost:8000/api/chaos/latest | jq '.report.invariants, .report.duplicate_effect_count,
                                              .report.stranded_run_count, .report.recovery_ms,
                                              .report.config_profile, .report.lease_duration_ms'
```

**Expected**: all five invariants `true`, `duplicate_effect_count: 0`, `stranded_run_count: 0`, a
recovery distribution inside the derived bound for the active profile, and **the profile and lease
reported alongside the figures**. `violations` is `[]` — returned explicitly, never `null`.

Then confirm the evidence is durable and the reset affordance respects it:

```bash
curl -sX POST localhost:8000/api/runs/demo/reset
curl -s localhost:8000/api/chaos | jq '.items | length'      # unchanged
```

**Expected**: chaos history is untouched. Attempting to `UPDATE` or `DELETE` a `chaos_reports` row
directly in `psql` raises `AN003` — immutability is a database property, in both deployment modes.

→ discharges **SC-001**, **SC-002**, **SC-003**, **SC-004**, **SC-005**, **SC-006**, **SC-014**,
**SC-017**.

## V9 — The cold-reviewer path *(phase 8, after the chaos console)*

Against the deployed instance, in a **fresh private window**:

1. The first viewport states the claim and shows a live status strip with three real numbers. No
   scrolling required to understand what this is. → **SC-009**
2. One click runs the example agent. No form, no options, no modal.
3. Mid-run, one highlighted control offers to kill the worker executing the current step, labelled
   with the endpoint it calls.
4. The timeline stalls **visibly**, labelled `orphaned — lease expiring`, with a countdown.
5. A new worker id appears, prior steps are marked replayed, and one sentence states that their tool
   calls did not run a second time.
6. The evidence band's hero figure is the harness-generated zero with its timestamp.
7. Cross-check: the killed worker is gone from the fleet page and then back.

**Timebox the whole sequence to sixty seconds**, without reading the README, without an account, and
without navigating away. → **SC-008**

## V10 — The developer path *(documentation gate)*

Have **someone other than the author** follow the eight-step quickstart from a clean clone on a
machine that has never run the project: clone and start · write the agent · write the tools · declare
each tool's safety category · register the agent · rebuild · submit a run · watch it, then break it.

**Expected**: every step works as written, or the step is corrected. A quickstart that has only ever
been executed by its author is a quickstart that does not work. → **SC-012**

**Also checked in the same pass**, because the same reader is the only one who will notice:

- The professor-outreach agent appears **verbatim** in the README, immediately after the one taught
  constraint, and the README names `demo_long` as the canonical already-done-filter example (FR-138).
  Ask the reader whether the constraint reads as a cost or as a benefit; if it reads as a cost, the
  example is in the wrong place or is not there.
- The design document states the **framework-adapter shape** — one node per `decide_next_step`, the
  framework's state object rehydrated from `ctx` on each call — and no adapter is built (FR-139).
- The pre-registration checklist is reachable from the authoring documentation, and the reader can say
  which of its four items the validator does *not* check (FR-134). If they cannot, P9.7 has failed.

## V11 — The deployment boundary *(every phase that adds a route)*

```bash
uv run pytest tests/boundary -q
```

**Expected**:

- With `ANCHOR_AUTHORING_EXECUTE` unset, `POST /api/authoring/register` returns **404, not 401 or
  403** — the response must not imply that a credential would help.
- With it unset, **no import path in the API package reaches registry-mutation code.**
- `PATCH /api/config` returns 404 in demonstration mode.
- `/api/authoring/validate` and `/api/authoring/generate` succeed in **both** modes.
- Submission and kill endpoints enforce their rate limits under concurrent load.
- The reset affordance leaves `chaos_events` and `chaos_reports` untouched.
- `sqlalchemy` is imported nowhere outside `ops/migrations/`.
- **No cross-run write path exists.** Every route that accepts a run id and can mutate it is
  enumerated by the test from the OpenAPI document and matched against an explicit allowlist —
  cancel, resolve, and kill — each of which is a deployment-wide affordance scoped per §31.1, not a
  per-caller one. A new mutating route on a run id fails this test until it is added to the allowlist
  deliberately. This is the one assertion whose subject is **code that does not exist**, so it guards
  a future addition rather than a present omission (FR-135).
- **No authoring draft is persisted server-side** — no table, no cache key, no filesystem path holds a
  draft after the response is written (FR-136).

→ discharges **SC-015**.

## V12 — Configuration cannot be set to a self-fencing state *(phase 6 onward)*

```bash
curl -sX PATCH localhost:8000/api/config -H 'content-type: application/json' \
     -d '{"lease_duration_ms":1000,"renewal_interval_ms":1000}'
```

**Expected**: `422`, naming the violated relationship and the offending values. **The configuration is
unchanged and the fleet is unaffected** — the change is rejected, never the workers. The same
assertion runs at worker startup, where a violation makes the worker refuse to start and say exactly
why.

## V13 — Fleet and deployment integrity *(phases 0, 5, 6)*

The six checks added by the optimality pass ([research.md](./research.md) §10). Each guards a hole
found by reasoning rather than by failure, so each test must be seen to **fail** against the
pre-pass behaviour before it is trusted.

```bash
uv run pytest tests/failure/test_attempt_cap_survives_handoff.py -q
```

**Expected**: a deterministically failing step, with its worker killed between every attempt, reaches
`failed` after exactly `max_attempts_per_step` **total** attempts — not per worker incarnation.
**Against an in-memory attempt counter this test does not fail, it hangs**, which is precisely the
production symptom it exists to prevent. → FR-130

```bash
uv run pytest tests/boundary/test_schema_version_gate.py -q
```

**Expected**: a process whose built-against revision differs from the applied revision **refuses to
start** and names both revisions. No long-running process applies migrations. → FR-128

```bash
docker compose restart worker && curl -s localhost:8000/api/workers | jq -r '.items[] | .id'
```

**Expected**: new ids with the same labels and higher incarnations. **Not** the same ids with
overwritten `started_at` — hostname and pid are both reused by the platform, so an identity built from
them would alias two different processes and quietly falsify "which worker executed each step".
→ FR-129

```bash
uv run pytest tests/failure/test_tool_declaration_conflict.py -q
```

**Expected**: two code versions registering one tool with different safety fields makes **that tool,
and only that tool**, unexecutable fleet-wide, with both dissenting versions recorded and surfaced.
The uncertainty window is never resolved from an ambiguous declaration. → FR-131

```bash
uv run pytest tests/failure/test_payload_ceiling.py -q
uv run pytest tests/unit/test_global_cap_enforced_at_claim.py -q
```

**Expected**: an oversized payload fails the step, exhausts attempts, and dead-letters with the event
type and measured size in the reason — **nothing truncated**, because a truncated payload would replay
to different messages than the original execution. And submitting far beyond the global cap leaves the
running count at the cap with the remainder `pending`, with no submission rejected. → FR-132, FR-003

```bash
uv run pytest tests/unit/test_rollup_rebuild_matches_live.py -q
```

**Expected**: truncating `metrics_rollup` and running `REBUILD` reproduces every bucket exactly as the
live aggregation computes it — which is what proves the rollup is derived rather than a second source
of truth. Separately assert that the duplicate-effect count, stranded-run count, and chaos-report
figures are **never** read from the rollup. → FR-133

---

## Full gate, before calling the project done

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict .
uv run pytest -q                        # unit · property · replay · concurrency · failure · boundary · contract
pnpm --dir web lint && pnpm --dir web test
uv run python -m anchor.chaos.harness --workers 3 --duration 1800    # sustained
```

Then the eight per-project items in the constitution's Definition of Done, of which two cannot be
checked by a machine and are the ones that actually matter:

- **A reviewer reaches the deployed URL and is convinced in sixty seconds** (V9).
- **The fencing token mechanism can be whiteboarded cold, without notes** — the zombie timeline, why
  the epoch must be monotonic, and why the check must live in the database. → **SC-018**
