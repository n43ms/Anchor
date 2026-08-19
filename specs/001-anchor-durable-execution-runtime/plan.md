# Implementation Plan: Anchor — Durable Execution Runtime for AI Agents

**Branch**: `001-anchor-durable-execution-runtime` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-anchor-durable-execution-runtime/spec.md`, derived
from [`anchor-spec.md`](../../anchor-spec.md) (§0–§36, Addenda A–F) and governed by
[constitution v1.1.0](../../.specify/memory/constitution.md).

## Summary

Build a durable execution runtime in which agent runs are stored as append-only event logs in
PostgreSQL, so that the machine executing a run may die at any instant and another worker resumes
from the exact step where it stopped without re-executing any side effect that already happened. The
technical approach is fixed by the specification and the constitution: ownership, sequencing, and
idempotency are decided by deterministic database logic inside single transactions; a monotonic epoch
enforced by a database trigger makes split-brain structurally impossible; every crossing of the
determinism boundary is journaled; every side effect is wrapped in a two-phase journal keyed by a
canonically derived idempotency key; and the whole claim is verified continuously by an adversarial
harness rather than asserted.

**Nine build phases plus a foundation phase, fragmented into 92 numbered work packages**, each with
its invariants, required tests, and an exit gate. Phase 2 and phase 4 are hard gates. No console work
before phase 4 completes; no landing surface before phase 8 completes. A tenth section, **Deferred
backlog**, is deliberately not a phase and carries no commitment.

**This plan incorporates the optimality pass** recorded as [research.md](./research.md) §10 (D-41 –
D-55), which closed three correctness holes — a retry cap that reset across a worker handoff, a global
concurrency cap that enforced nothing, and worker identity reused across container restarts — plus two
deployment hazards and four scale decisions. No constitution amendment was required; §10.0 shows the
check per principle.

**It also incorporates the Addendum F intake** of 2026-08-08 ([research.md](./research.md) §11, D-56 –
D-59) and seven coverage gaps closed in the same pass: the framework-adapter shape stated but not
built (FR-139), the absence of cross-run write paths asserted rather than assumed (FR-135), the
authoring surface's lack of server-side draft persistence (FR-136), the validator's stated ceiling
(FR-134, P9.7), the authoring-time-versus-runtime distinction carried out of the API layer (FR-137),
the professor-outreach example required in the README (FR-138), and the footer and exclusion items of
§32.4–§32.5 (FR-109). **The branching cut of §28.3 is now recorded as load-bearing** rather than
merely omitted, because reintroducing it would reopen `I2` and `I3`.

## Technical Context

<!--
  The stack is FIXED by the constitution ("Technology Stack and Toolchain"). Restated here for the
  entries this feature touches; not re-decided. A stack change or a new dependency is a constitution
  amendment plus maintainer approval.
-->

**Language/Version**: Python 3.12 (runtime, worker, API, chaos harness); TypeScript 5.x strict
(console). Python 3.12 specifically for `asyncio.TaskGroup` and `asyncio.timeout`, which are the
primitives the background renewer and the per-step timeout are built on ([research.md](./research.md)
D-02).

**Primary Dependencies**: FastAPI · uvicorn[standard] · asyncpg (explicit SQL, no ORM on the hot
path) · redis · pydantic · pydantic-settings · Alembic + SQLAlchemy (migrations only, confined to
`ops/migrations/` and asserted by a test) · pytest · pytest-asyncio · hypothesis · ruff · mypy ·
Next.js (App Router) / React · Vite · react-router-dom · Tailwind v4. **Nothing else without maintainer approval** (D-04).

**Storage**: PostgreSQL 16, single instance, single writer — the source of truth for the log, the
lease, the epoch, and the journal. Redis 7 for pub/sub fan-out and worker kill delivery only,
**never authoritative** for ownership or liveness.

**Testing**: pytest across seven suites that map one-to-one onto the constitution's required test
classes — `tests/unit`, `tests/property`, `tests/replay`, `tests/concurrency`, `tests/failure`
(one module per row of §9's failure matrix), `tests/boundary`, `tests/contract`, plus `web/` component
tests. Integration tests run against real PostgreSQL and Redis from compose or CI service containers;
no database doubles, because every invariant claimed is enforced by PostgreSQL itself (D-34).

**Target Platform**: Linux containers. Local: Docker Compose — PostgreSQL, Redis, API, **three
workers**, console. Hosted: Render — one web service, one PostgreSQL, one Redis, **three always-on
background workers on a paid tier**. Free tier is disqualifying: a worker that sleeps is not a
fault-tolerant runtime.

**Project Type**: Web application with a background worker fleet — a runtime library (`anchor/core`),
a worker process (`anchor/worker`), a thin HTTP/WebSocket surface (`anchor/api`), an adversarial test
rig (`anchor/chaos`), and an operator console (`web/`).

**Performance Goals**: **Not a throughput project.** The measured goals are correctness-shaped:
zero duplicate side effects and zero stranded runs under sustained adversarial failure; recovery from
worker death within `lease_duration − renewal_interval/2 + reclaim_poll_interval/2` (≈3.75 s demo
profile, ≈18.5 s production); replay overhead reported as mean steps replayed per resumption and mean
replay latency; throughput plotted against an ideal-linear reference so the single-writer ceiling is
visible rather than hidden.

**Constraints**: `lease_duration >= 4 × renewal_interval`, asserted at startup and on every live
configuration change, with the change rejected rather than the fleet. Every external call bounded by
`step_timeout`. Every fan-out bounded. No authentication anywhere. Demonstration mode is the
fail-closed default. Chaos history immutable in every mode.

**Scale/Scope**: 11 tables, 25 HTTP operations across 23 paths, 2 WebSocket channels, 17 event types, 14 console
pages, 5 continuously asserted invariants, 3 agent workloads, 5 demo tools spanning all three safety
categories, 3 identity hues (the validated ceiling), 2 configuration profiles, 2 deployment modes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Answer each gate. A `NO` blocks the plan; a `N/A` must state why the gate does not apply.

| Gate | Principle | Answer |
|---|---|---|
| Invariants touched are named (`I1`–`I8`), with how each is preserved. "None" is stated explicitly, not skipped. | I | **YES** — all eight; see [spec.md](./spec.md) → Invariant Impact, and per-phase in the phase tables below. |
| Any safety property is enforced by a database constraint or trigger, not by application code. | II | **YES** — `PRIMARY KEY (run_id, seq)`, `run_events_epoch_gate`, `tool_journal` PK, `tool_journal_result_once`, immutability triggers, terminal-state `CHECK`, safety-category `CHECK`s, `demo_effects` unique key. Enumerated in [data-model.md](./data-model.md) §10. |
| Correctness logic lands in `core/` only. Nothing in `api/`, `worker/`, or `web/` enforces a safety property. | II, Boundaries | **YES** — `anchor/core` holds events, leases, journal, replay, determinism. `worker/` follows the protocol; `api/` is thin; `web/` has none. The one deliberate exception is documented and is not an enforcement: the operator resolution write in `api/` uses `core.events.append` and is permitted only on a leaseless run (D-24). |
| Every non-deterministic value crosses the boundary through `StepContext` and is journaled. | III | **YES** — five journaled calls, `NONDET_RECORDED` with `call_ordinal`, plus an AST test banning direct `datetime`/`time`/`random`/`uuid` in agent modules (D-27). |
| Every new tool declares a safety category; `reconcilable` tools supply a `reconcile_fn`. | IV | **YES** — enforced at registration *and* as table `CHECK`s, including `retry_safe` requiring a stated reason. |
| Tests planned per Principle V: unit for pure `core/` functions, property for canonical serialization, replay determinism, concurrency, and a failure-injection test for each new failure mode. | V | **YES** — seven suites mirroring the required classes; `tests/failure` has one module per failure-matrix row (D-33). Per-phase test requirements are listed in every phase table. |
| The feature belongs to the current build phase, and no later-phase work is being pulled forward (no console before phase 4; no landing surface before phase 8). | VI | **YES** — phase gates are explicit and the sequencing rules below are normative. Two items are deliberately pulled *earlier* than a naive reading, both sanctioned: `demo_effects` and the demo agent into phase 5 (per §23), and the epoch trigger into phase 0 (see the note in Phase 0, P0.3). |
| No new timing, retry, or concurrency constant lives outside the config module; the startup assertion still holds. | VII | **YES** — one config module, twelve keys, seeded into `runtime_config`, asserted at startup and by an `AFTER` statement trigger as the backstop. |
| Console work states loading, empty, and error handling, and does not render optimistic state as confirmed. | VIII | **YES** — required per component in phase 7, with the five mock states including the currently-orphaned one. |
| Nothing on the cut list is reintroduced; no capability is gated by identity; demonstration mode remains the fail-closed default. | IX, Deployment modes | **YES** — no auth, no accounts, no sessions, no per-user state in any phase. Every restriction is a function of deployment mode. |
| Every new await point and I/O boundary has a stated crash behaviour. | Code Standards | **YES** — required per work package; the `ctx` call boundaries are already enumerated in [contracts/agent-contract.md](./contracts/agent-contract.md). |
| No dependency added without maintainer approval; no schema, constraint, or transaction-boundary change made without raising it first. | Workflow | **YES** — dependency set frozen in D-04. Three schema additions beyond §7 were raised and approved on 2026-07-31 (`chaos_runs`, `chaos_reports`, `runtime_config`); `runs.last_seq` came from Addendum C §25.1. |

**Post-design re-check (after Phase 1 artifacts):** all twelve still pass. The design surfaced three
deviations, each recorded in Complexity Tracking rather than waved through.

## Project Structure

### Documentation (this feature)

```text
specs/001-anchor-durable-execution-runtime/
├── spec.md                     # Feature spec: 9 user stories, 139 FRs, 18 success criteria
├── plan.md                     # This file
├── research.md                 # Phase 0: 59 decisions with rationale and alternatives
├── data-model.md               # Phase 1: 11 tables, every column, triggers, event payloads
├── quickstart.md               # Phase 1: 13 validation scenarios mapped to success criteria
├── contracts/
│   ├── openapi.yaml            # 23 paths / 25 operations, 24 schemas, per-mode availability
│   ├── websocket.md            # /ws/runs/{id} and /ws/fleet framing, backpressure, backfill
│   ├── agent-contract.md       # StepContext, decide_next_step, the one taught constraint
│   ├── tool-contract.md        # Registration, the three safety categories, reconcile_fn
│   └── component-contract.md   # RunDetail / RunThread props and mark specification
└── tasks.md                    # Generated per phase by /speckit-tasks — NOT created here
```

### Source Code (repository root)

The Python packages are wrapped in `anchor/` — a documented one-level deviation from §5.1's tree,
approved 2026-07-31 (D-01). Every directory name and every boundary from §5.1 is preserved.

```text
anchor/
├── core/                       # Protocol logic. Pure, testable, no I/O beyond the database.
│   ├── events/                 #   event types, payload models, the append CTE, sequence handling
│   ├── leases/                 #   claim, renew, expiry, fencing-token enforcement, LeaseFencedError
│   ├── journal/                #   idempotency keys, canonical serialization, uncertainty policies
│   ├── replay/                 #   log → RunContext reconstruction (a pure fold)
│   ├── determinism/            #   journaled clock, randomness, id generation
│   ├── db/                     #   asyncpg pool, explicit SQL, SQLSTATE → typed error mapping
│   └── config/                 #   the twelve settings, two profiles, the startup assertion
├── worker/
│   ├── loop.py                 #   the execution loop — the heart of the project
│   ├── renewer.py              #   the background lease renewer and fencing detector
│   ├── admission/              #   per-worker concurrency limits, backpressure
│   ├── retry/                  #   backoff, jitter, attempt caps, dead-lettering
│   └── registry/               #   self-registration, heartbeat telemetry, kill subscriber
├── runtime/
│   ├── tools/                  #   tool registration and per-tool safety declarations
│   └── agents/                 #   demo_short, demo_long, demo_unsafe  (AST-checked)
├── api/
│   ├── routers/                #   runs, workers, chaos, registry, observability, config, authoring
│   ├── ws/                     #   channel handlers, Redis subscription, bounded fan-out
│   └── serializers/            #   RunTimeline derivation, metric queries
└── chaos/
    ├── harness.py              #   orchestrates workers, runs, and injected failures
    ├── invariants.py           #   the five assertions that constitute the proof
    └── report.py               #   metric computation and the published report

web/
├── app/                        # React operator console route components
├── components/
│   ├── run/                    #   RunDetail, RunThread, timeline track, segments, markers
│   ├── fleet/                  #   worker cards, kill control, deployments
│   ├── chaos/                  #   console, invariant panel, history
│   └── primitives/             #   stat tile, hero figure, chart shells, status pill, table view
├── hooks/                      #   useRunStream, useFleetStream, usePolling fallback
├── lib/                        #   typed API client, token access, canonical formatting
└── styles/                     #   design tokens: dark set and light set, no hardcoded colors

ops/
├── migrations/                 # Alembic; raw SQL for every constraint, trigger, and function
├── compose/                    # docker-compose.yml, Dockerfiles, healthchecks
└── deploy/                     # Render service definitions, scheduled chaos job

tests/
├── unit/  property/  replay/  concurrency/  failure/  boundary/  contract/
└── fixtures/                   # recorded logs, including logs captured from fencing incidents
```

**Structure Decision**: `anchor/` wraps the five Python packages; `web/`, `ops/`, `tests/`, and
`specs/` are siblings at the repository root. `core/` is separated from `worker/` because `core/`
holds the protocol and `worker/` holds the loop that follows it — that separation is what makes the
protocol independently testable, and independently testable protocol logic is what makes the invariant
tests meaningful.

## Complexity Tracking

> Filled because the design has three deviations that must be justified rather than absorbed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `anchor/` package wrapper deviates from §5.1's literal tree | §5.1 places `core/`, `api/`, … at the repository root, making them top-level importable module names that collide with common third-party names and require five package declarations | The literal layout was the simpler alternative and is rejected on namespace grounds only; the deviation is one level, preserves every directory name, and was explicitly approved |
| Three tables beyond §7 (`chaos_runs`, `chaos_reports`, `runtime_config`) | `POST /api/chaos/start`, `GET /api/chaos/{id}/report`, the permanent History page, and the live-editable Environment page are all spec-required and none is expressible against the six specified tables | Folding reports into `chaos_events` as JSONB was considered: it weakens report immutability and the History page's query shape. Keeping configuration in the environment was considered: it deletes §13.3's live-editable page, which the spec argues is what makes the console read as tooling |
| The chaos harness is not itself durable | An API restart mid-run abandons the chaos run, which is recorded as `abandoned` rather than hidden | Making the harness durable means running it on Anchor, which is circular and compromises the independence of the proof. The harness is the test rig, not the system under test |

---

## Phase Sequencing Rules (normative)

These are gates, not guidance. They come from §15, §23, §29, and constitution Principle VI.

1. **Phase 2 is a hard gate.** Nothing proceeds until a worker killed mid-run demonstrably resumes
   from the correct step with correct context. Everything else in the project is elaboration on that
   single behaviour.
2. **No console work before phase 4 completes.** Not tokens, not a shell, not a component. The
   temptation is strong because the console is more immediately satisfying to build, which is exactly
   why the rule is absolute.
3. **No landing surface before phase 8 completes.** Its bands quote live metrics and harness output
   that do not exist earlier, and a landing page written first would contain placeholder figures —
   which have a way of shipping.
4. **Phases 4 and 5 will overrun.** Concurrency bugs are intermittent, resistant to reproduction, and
   hard to reason about. That difficulty is precisely why the project is worth building.
5. **Phase 9 is optional** and begins only after phase 8 is complete. Within it: validator, then
   editor, then generator. If only half is built, the half worth having is the validator.
6. **Every phase ends with its exit gate demonstrated, not asserted.** The gate is a command someone
   else can run, listed per phase and expanded in [quickstart.md](./quickstart.md).

### An honest note about the interim guarantee

Between phase 2 and phase 5 the system resumes correctly at **step granularity** but does **not** yet
handle the uncertainty window: a crash between a tool's execution and the recording of its result can
double-execute. This is the intended sequencing — §15 puts replay at phase 2 and the two-phase journal
at phase 5 — but it means **the product's headline guarantee does not hold until phase 5 completes**,
and no claim about it may be published, demonstrated, or written into a README before then.

---

## Phase 0 — Foundation

Not in §15, which starts at "submit a run". It is separated out because eight things must exist before
any protocol code can be written honestly, and burying them inside phase 1 is how a config constant
ends up hardcoded in a worker loop.

**Goal**: `docker compose up` brings up PostgreSQL, Redis, the API, and three workers that register,
heartbeat, and idle. Configuration refuses to start in a self-fencing state. CI is green.

| # | Work package | Detail |
|---|---|---|
| P0.1 | Repository scaffold | `pyproject.toml` with `uv`, `ruff`, `mypy --strict` config; `anchor/` and its five subpackages; the seven `tests/` suites as empty packages; `ops/`; `web/` as a placeholder only |
| P0.2 | Configuration module | `anchor/core/config`: the twelve settings, the `demo` and `production` profiles, the three-part startup assertion, and the refuse-to-start path that names the violated relationship and the offending values |
| P0.3 | Migration 001 and the invariant DDL | `runs`, `run_events`, `workers`, `runtime_config`; `PRIMARY KEY (run_id, seq)`; `run_events_epoch_gate`; `run_events_immutable`; terminal-state and running-implies-ownership `CHECK`s; the worker identity `CHECK` and label sequences; the claim indexes; `runtime_config_assert`; the seed of the active profile (fifteen keys) |
| P0.4 | Database access layer | `anchor/core/db`: asyncpg pool with bounded size, explicit-SQL module structure, and the SQLSTATE → typed error map (`AN001→LeaseFencedError`, `AN002→ConfigAssertionError`, `AN003→ImmutableRecordError`, `AN004→ResultOverwriteError`) |
| P0.5 | Worker registration and heartbeat | `worker/registry`: claim a fleet-slot label, take the next **incarnation** from that label's sequence, insert `worker-{label}#{n}` with hostname, pid, capacity, code version, role; refresh `last_seen_at`; subscribe to the Redis kill channel and hard-exit on message. **Identity is never reused** (D-42) |
| P0.6 | Compose topology | PostgreSQL, Redis, a one-shot `migrate` service, API and `worker` ×3 with `depends_on: service_completed_successfully` on it, `restart: always` on the workers, healthchecks, `ANCHOR_AUTHORING_EXECUTE=true` set **only** here |
| P0.7 | Schema-version gate | Every process reads the applied Alembic revision at startup, compares it against the revision its code was built against, and **refuses to start** on a mismatch, naming both. No long-running process ever runs `alembic upgrade head` (D-45) |
| P0.8 | CI workflow | `ruff`, `mypy --strict`, pytest with `postgres:16` and `redis:7` service containers, migrations applied by the one-shot step before tests |
| P0.9 | Structured logging | stdlib `logging` with a JSON formatter; every worker line carries `run_id`, `epoch`, `worker_id`, `step_index` where applicable — the epoch is what makes a fencing incident reconstructable from two workers' logs afterwards |

**Invariants in play**: `I5` (the DB clock is the only clock in the SQL from the start), `I7` (fail
closed: no execution path exists yet, and the API returns 503 when PostgreSQL is unreachable).

**Why the epoch trigger lands here rather than in phase 4.** Creating a constraint is cheap now and
expensive to retrofit after four phases of writes exist. The trigger is inert until epochs advance in
phase 3 and behaviourally exercised in phase 4; installing it early costs nothing and means no phase
ever runs without it. This is a deliberate pull-forward, sanctioned by "constraints over
conventions".

**Tests**: config assertion accepts the two profiles and rejects `lease == renewal`; SQLSTATE mapping
round-trips each code to its typed error; `sqlalchemy` confinement (`tests/boundary`); a worker
registers and its row appears with a fresh `last_seen_at`; **a worker restarted with the same hostname
and pid receives a new incarnation and a distinct id**; **a process whose built-against revision differs
from the applied revision refuses to start**.

**Exit gate**: `docker compose up` → `GET /api/health` reports `worker_count: 3`,
`deployment_mode: local`, `degraded: false`, and the applied schema revision. A worker started with
`lease_duration_ms == renewal_interval_ms` refuses to start and names the relationship. CI green.

**Risks**: none material. This phase is where to discover Docker networking and migration-ordering
friction, and discovering it here is the point.

---

## Phase 1 — The log is the spine

**Goal**: submit a run via the API; one worker executes a hardcoded three-step agent; every step is
appended to the event log. Nothing about the run exists anywhere except the log.

| # | Work package | Detail |
|---|---|---|
| P1.1 | Event types and payload models | All 17 types with their payload schemas from [data-model.md](./data-model.md) §11, as pydantic models so a malformed payload fails at construction rather than at replay |
| P1.2 | The append protocol | `core/events.append`: the single-statement CTE that increments `runs.last_seq` and inserts, returning `seq`. Transaction comment states what must be atomic and why. **Payload ceiling** enforced here with a typed `PayloadTooLargeError` — never truncation, which would be replay divergence introduced by a size optimization (D-51) |
| P1.3 | Run submission | `POST /api/runs` with `client_request_key` dedupe via the partial unique index, `RUN_SUBMITTED` appended by `worker_id: 'api'`, and the global concurrency cap read but not yet enforced against workers |
| P1.4 | Minimal worker loop | Poll, take one `pending` run (naive `FOR UPDATE` — `SKIP LOCKED` arrives in phase 3), execute steps, append `STEP_STARTED`/`STEP_COMPLETED`, finalize `RUN_COMPLETED` |
| P1.5 | `StepContext` v1 | `call_tool` and `call_model` executing directly and appending `TOOL_INTENT`/`TOOL_RESULT`/`LLM_CALLED` **as events only** — the journal table and the three-state lookup are phase 5 |
| P1.6 | Hardcoded three-step agent | `runtime/agents/demo_minimal`: search → summarize → notify, with the stub model adapter and its configured latency |
| P1.7 | Read endpoints | `GET /api/runs`, `/{id}`, `/{id}/events` with keyset pagination and `after_seq` |

**Invariants in play**: `I1` (the two-phase *ordering* is established — intent committed before
invocation — even though deduplication is not yet possible), `I2` (append-only, contiguous `seq`),
`I4` (submission and claim each in one transaction), `I7`.

**Crash behaviour to state per package**: P1.2 — a crash before commit leaves no event and no counter
advance; P1.4 — a crash mid-run leaves the run `running` with an expiring lease and no reclaim path
yet, which is the honest interim state phase 2 fixes; P1.5 — a crash after a tool executes but before
`TOOL_RESULT` currently loses the record, which is exactly what phase 5 exists to make safe.

**Tests**: unit tests for append (contiguity, rollback leaves no gap); a submission-dedupe test; an
integration test asserting the full event sequence for a completed run; a test asserting no table
other than `run_events` records step outcomes.

**Exit gate**: [V1](./quickstart.md#v1--the-log-is-the-spine-phase-1) — `seq` contiguous from 1, one
worker, one epoch, complete history reconstructable by eye from the log.

---

## Phase 2 — Replay *(HARD GATE)*

**Goal**: kill the worker mid-run, restart it, and verify it resumes from the correct step with the
correct context. **This is the moment the project becomes real.**

| # | Work package | Detail |
|---|---|---|
| P2.1 | `core/replay.reconstruct` | A pure fold over ordered events producing `RunContext`: accumulated messages, `last_completed_step_index`, journaled results by key, journaled non-deterministic values by `(step_index, kind, call_ordinal)`, **and the per-step attempt count from `STEP_FAILED` counts** (D-43) so the retry cap survives a handoff. No I/O |
| P2.2 | Journaled determinism | `core/determinism`: `ctx.now()`, `ctx.random()`, `ctx.new_id()` accumulating into an ordered per-step buffer, flushed as **one** `NONDET_RECORDED` event in the same transaction as that step's `TOOL_INTENT` — or as `STEP_COMPLETED` when the step has no effect (D-47). Read back in original order on replay |
| P2.3 | The AST determinism ban | The shared checker that walks every module under `runtime/agents/` and fails on `datetime`/`time`/`random`/`uuid` — written once here, reused by the phase-9 validator |
| P2.4 | Replay on claim | The worker replays before executing, emits `REPLAY_COMPLETED` with `steps_replayed` and `replay_ms`, and resumes at `last_completed_step_index + 1` |
| P2.5 | Step-level skip | Steps with a recorded `STEP_COMPLETED` are not re-executed. **Step granularity only** — within-step uncertainty is phase 5 |
| P2.6 | Recorded-log fixtures | `tests/fixtures`: hand-built logs plus logs captured from real runs, including a truncated log that ends mid-step |

**Invariants in play**: `I6` (the whole phase), `I2`, `I5`.

**Tests**: replay determinism against every fixture, compared by canonical-JSON hash of the final
state (D-25); a replay test for a log truncated mid-step; the AST ban test; the kill-and-resume
integration test; a test that two `ctx.now()` calls in one step replay **in order** — the
`call_ordinal` failure is invisible without it.

**Exit gate**: [V2](./quickstart.md#v2--replay-after-death-phase-2--the-hard-gate). All six expected
outcomes, including `steps_replayed` matching and effects showing no duplicates for the *step-skip*
path.

**Risks**: the highest-value risk in the project is a subtly wrong `RunContext` that looks right on a
happy-path log. Mitigation is the truncated-log fixture and the ordinal test, both of which fail
loudly on the mistakes that otherwise surface as an unrelated-looking invariant failure days later.

---

## Phase 3 — Concurrency: skip-locked claiming, leases, background renewal

**Goal**: many identical workers, one shared queue, no central coordinator. Ownership is time-bounded
and extended by a renewer that does not depend on step progress.

| # | Work package | Detail |
|---|---|---|
| P3.1 | The claim statement | The `SKIP LOCKED` CTE handling `pending` and expired-lease runs **in one statement**, incrementing the epoch, setting the owner, extending the lease from `now()`, and returning `(id, epoch)`; then the `RUN_CLAIMED` append in the same transaction. **The global concurrency cap is enforced here** (D-44) — a cap applied at submission enforces nothing and contradicts §9's "new runs stay pending" |
| P3.2 | Claim indexes | The two partial indexes plus the `status` index the global-cap count uses, each with its serving query recorded and its write cost noted |
| P3.3 | Lease renewal | `UPDATE … WHERE id = $1 AND epoch = $2`, with `LEASE_RENEWED` appended **on boundaries and threshold breaches only** — first after claim, latency above `renewal_latency_warn_pct` of the lease, last before terminal (D-48). Every renewal's latency goes to telemetry regardless |
| P3.4 | The `TaskGroup` structure | One group per claimed run: the execution task and the renewer, with the renewer on its own timer, independent of step progress |
| P3.5 | Reclaim polling | Poll interval plus jitter; back off with jitter when no row is returned, so idle workers do not form a polling convoy |
| P3.6 | Fleet telemetry | Heartbeat refresh, `current_run_count`, and the `fleet:telemetry` publish (display only — `last_seen_at` in PostgreSQL remains the only thing anyone reasons about) |
| P3.7 | Multi-worker verification | Three workers competing for real work, with per-worker step throughput visible in the logs |

**Invariants in play**: `I3` (the epoch now advances, making the phase-0 trigger live), `I4`, `I5`.

**Crash behaviour**: a crash between the claim commit and the first step leaves a claimed run with a
live lease that expires normally; a crash inside the renewer's `TaskGroup` cancels the sibling task
via structured concurrency rather than leaving an orphaned writer.

**Tests**: `tests/concurrency` — N workers, one available run, exactly one claim succeeds, repeated
under load; a reclaim test asserting the second claim carries
`reason: reclaimed_after_lease_expiry` and `epoch + 1`; **a step longer than `lease_duration` is not
fenced**, which is the behaviour that makes two profiles possible; a renewal-latency test.

**Exit gate**: [V3](./quickstart.md#v3--claim-contention-phase-3).

**Risks**: the renewal interval and lease are now load-bearing. A too-short lease spuriously fences a
healthy worker — the hardest bug in the system to diagnose after the fact. Mitigation: the assertion
from phase 0, and the fencing-rate metric arriving in phase 6 as the detector.

---

## Phase 4 — Fencing tokens and the epoch write gate *(HARD GATE)*

**Goal**: deliberately construct a zombie worker and prove the stale worker is rejected, withdraws
silently, and writes nothing. **The hardest and most valuable phase.**

| # | Work package | Detail |
|---|---|---|
| P4.1 | Fenced-worker withdrawal | Catch `LeaseFencedError`, discard all in-memory state, **write nothing further — including no error event through that run's log** — do not retry, return to the idle pool |
| P4.2 | The renewer as fencing detector | A rejected renewal cancels the run's execution task; the cancelled task performs no write, enforced by the single append path checking its own cancellation state before issuing SQL |
| P4.3 | `WORKER_FENCED` | Appended by the surviving writer where the fencing is observable, carrying `stale_epoch`, `current_epoch`, and `detected_by` — both epochs, because the console must display both |
| P4.4 | Zombie construction | A test-only stall injection that suspends a worker's event loop while holding a stale epoch, so the scenario is reproducible rather than anecdotal |
| P4.5 | Blocked-loop verification | Assert that a fully blocked event loop results in lease expiry and reclaim, **not** in continued renewal — the renewer must be incapable of signalling liveness that outlives a stalled process |
| P4.6 | Fencing-rate counting | Count rejected writes for the metric that arrives in phase 6, so the series has history by the time the chart exists |

**Invariants in play**: `I3` above all, plus `I2` and `I4`.

**Tests** (all in `tests/failure`): the stale append is rejected by the database with `AN001`; **no
partial write landed** — `runs.last_seq` unchanged; the fenced worker performs no subsequent write of
any kind; it does not retry; a rejected renewal cancels the run task and **no write follows the
cancellation**; a blocked event loop is reclaimed. Each corresponds to a row of §9's failure matrix.

**Exit gate**: [V4](./quickstart.md#v4--the-zombie-worker-is-fenced-phase-4--the-most-valuable-phase).
Plus the non-mechanical gate: **the mechanism can be whiteboarded cold** — the zombie timeline, why
the epoch must be monotonic, and why the check must live in the database.

**Risks**: the cancellation path is a real race on a different task than the one doing the work. It
needs a test rather than an argument, and P4.2's test is that test. Budget generously here.

---

## Phase 5 — The two-phase journal, canonical hashing, and uncertainty policies

**Goal**: the "no double email" guarantee. **The product's headline claim holds from the end of this
phase and not before.**

| # | Work package | Detail |
|---|---|---|
| P5.1 | Canonical serialization | Sorted keys, compact separators, NFC strings, shortest-round-trip floats, and a **raise** on NaN, ±Inf, sets, tuples, `datetime`, `Decimal`, or any non-JSON-native type, carrying the path to the offending value |
| P5.2 | Idempotency key derivation | SHA-256 over `run_id \| step_index \| action_name \| canonical_json(args)`, stored whole; `args_hash` stored separately; the short display form derived for the UI only |
| P5.3 | Migration 002 | `tool_journal`, `tool_registry`, `demo_effects`; the journal PK; `tool_journal_result_once`; the no-delete triggers; the safety-category `CHECK`s; `demo_effects UNIQUE (idempotency_key)` |
| P5.4 | Two-phase `call_tool` | Three-state lookup → skip / execute / apply policy. `TOOL_INTENT` **committed before invocation**; `TOOL_RESULT` after; `STEP_SKIPPED_ON_REPLAY` emitted on the skip path so the console can render it |
| P5.5 | Tool registration and declarations | `register_tool` with the three refusal conditions; **the declaration hash, upsert-on-startup, and per-tool fail-closed on a cross-version conflict** (D-46); the registry table as the source for `GET /api/tools` |
| P5.6 | The three policies | `retry_safe` re-executes with the key passed through; `reconcilable` runs `reconcile_fn` and branches, with `Unknown()` escalating; `unsafe` sets `needs_review`, halts, releases the lease |
| P5.7 | Operator resolution | `POST /api/runs/{id}/resolve` writing as `worker_id: 'operator'` at the run's current epoch, permitted only on a leaseless `needs_review` run; three outcomes, none of them a guess |
| P5.8 | The three demo agents | `demo_short` (8–10 steps, 25–40 s, varied 2–5 s steps), `demo_long` (~40 steps), `demo_unsafe` (crashes inside the uncertainty window); five demo tools spanning all three categories. **Written as reference implementations, not as fixtures** (D-57): `demo_long` is the canonical worked example of the already-done filter pattern and the README points at it by name; all three are §27.4's few-shot examples, so the generator's ceiling is their quality. **This bar is not retrofittable** — they become the chaos harness's workloads in phase 8, and rewriting a workload afterward invalidates the evidence captured with it |
| P5.9 | `demo_effects` writes | One row per execution, surfaced by `GET /api/runs/{id}/effects` — the proof surface, and the constraint that makes a double execution a database error rather than a counted anomaly |

**Invariants in play**: `I1` and `I8` (the whole phase), plus `I2` and `I6`.

**Crash behaviour**: between `TOOL_INTENT` commit and invocation — no effect occurred, policy resolves
conservatively; between invocation and `TOOL_RESULT` — **the uncertainty window**, resolved by declared
policy; between `TOOL_RESULT` and `STEP_COMPLETED` — the result is durable, the step re-completes
harmlessly on replay.

**Tests**: the canonical-serialization property test (key order, nesting traversal, numeric
formatting → identical hash; rejected types raise with a path) — **this is the test that protects the
entire idempotency mechanism**; one uncertainty-window test per category; a `reconcile_fn` returning
`Unknown()` escalates to `needs_review`; the resolve path writes an attributed event; registration
refusal tests for all three conditions; a `demo_effects` uniqueness test asserting a forced double
execution is rejected by the database; **a declaration-conflict test** in which two code versions
register the same tool with different safety fields and that tool — and only that tool — becomes
unexecutable, with both versions recorded.

**Exit gate**: [V5](./quickstart.md#v5--effectively-once-including-the-uncertainty-window-phase-5).

**Risks**: canonical serialization drift is the silent failure mode — it does not error, it
double-executes. Mitigation is the property test plus the invariant checker in phase 8 asserting the
same key never carries two results.

---

## Phase 6 — Production-shaped behaviour

**Goal**: predictable behaviour under load and repeated failure; live configuration; real-time
fan-out; the observability surface the console will render.

| # | Work package | Detail |
|---|---|---|
| P6.1 | Retry | Exponential backoff with ±25% jitter, bounded by a cap, **at step granularity only**; `STEP_FAILED` with `attempt`, `error_type`, `will_retry`, `backoff_ms`. The attempt number comes from the **log-derived** count (D-43), not from memory |
| P6.2 | Dead-lettering | Attempt cap → `RUN_FAILED` with `dead_lettered: true`, status `failed`, lease released, queryable as the dead-letter view. Because the count is log-derived, the cap holds across arbitrary handoffs |
| P6.3 | Cooperative cancellation | `cancel_requested_at` checked **between steps, never mid-step** on a `running` run; a `pending` run is finalized directly by the API, since it is leaseless and no worker can be racing it (D-54) |
| P6.4 | Admission control | Per-worker limit checked before claiming, from the worker's own in-process count. The global cap lives in the claim statement (P3.1); the API **reports** the cap and the running count rather than rejecting submissions |
| P6.5 | Step timeout | `asyncio.timeout` wrapping every external call, and **the renewer stops when a step exceeds its timeout** so a non-progressing worker lapses its lease rather than holding the run |
| P6.6 | Live configuration | `runtime_config` read at startup, bounded re-poll, Redis "version changed" nudge, **new values applied only at a step boundary**; `PATCH /api/config` re-runs the assertion and rejects the change; route unmounted in demonstration mode |
| P6.7 | Redis publish | Every appended event published to the single `anchor:events` firehose **after commit** — after, because a notification about an uncommitted write would be a lie; one channel rather than per-run, so subscribe/unsubscribe is never on the request path (D-50) |
| P6.8 | WebSocket channels | `/ws/runs/{id}` and `/ws/fleet`: one always-on Redis subscription demultiplexed in process; `hello` + `snapshot` then per-event frames carrying `seq`; bounded per-client queue; close `1013` on slow consumer; backfill via `after_seq`; the `lag` frame that starts the orphan countdown immediately |
| P6.9 | Timeline derivation | `GET /api/runs/{id}/timeline` producing exactly the `RunDetail` prop shape, server-side, so the component stays a pure function of props |
| P6.10 | Metrics rollup job | The watermarked periodic job that folds `run_events` into `metrics_rollup` at 10 s and 300 s resolutions, plus the tested `REBUILD` path. **Never a trigger on the append path**, which would make every worker contend on one bucket row and serialize appends across runs that currently never contend (D-49) |
| P6.11 | Metrics and health | Display series served from the rollup; **duplicate-effect count, stranded runs, and every chaos figure computed live from source**; `GET /api/health` reporting degradation, the schema revision, and the global cap with the current running count |
| P6.12 | Rate limiting | Per-IP token bucket for submission and kill, plus the hourly demo cap, with the single-web-instance assumption stated at the code |
| P6.13 | Reset affordance | `POST /api/runs/demo/reset` pruning completed demo runs, structurally unable to touch chaos history or the rollup's source |

**Invariants in play**: `I7` (fail closed on database loss; Redis loss degrades display only), plus
`I2`, `I5`, `I8`.

**Tests**: the **complete** §9 failure matrix in `tests/failure`, one module per row — including
database-unavailable (nothing executes, no unrecorded side effect), Redis-unavailable (execution
unaffected), fleet-saturated (excess stays `pending`), slow WebSocket client (dropped and able to
backfill), clock skew (irrelevant by construction), and worker-registers-then-dies. Plus the
configuration-rejection test at both boundaries, and a step-timeout test asserting the renewer
stopped.

Five tests added by the optimality pass, each guarding a hole that was found by reasoning rather than
by failure:

- **The attempt cap survives handoffs.** A step that fails deterministically, with its worker killed
  between every attempt, reaches `failed` after exactly `max_attempts_per_step` **total** attempts —
  not per incarnation. Without D-43 this test loops forever, which is the whole point of writing it.
- **The global cap actually caps.** Submitting far beyond the cap leaves the running count at the cap
  and the remainder `pending`, with no worker over its own limit.
- **The rollup is rebuildable.** Truncate `metrics_rollup`, run `REBUILD`, and assert every bucket
  matches the live aggregation — which also proves the rollup never became a second source of truth.
- **The payload ceiling dead-letters.** An oversized payload fails the step, exhausts attempts, and
  lands in the dead-letter view with the event type and measured size in the reason. Nothing is
  truncated.
- **A `pending` run cancels immediately**, finalized by the API without a claim, an epoch increment, or
  a replay.

**Exit gate**: [V6](./quickstart.md#v6--load-and-repeated-failure-phase-6) and
[V12](./quickstart.md#v12--configuration-cannot-be-set-to-a-self-fencing-state-phase-6-onward).

---

## Phase 7 — The operator console

**Goal**: make the runtime demonstrable and completely auditable. **Begins only after phase 4 — in
practice after phase 6, since the console renders what phase 6 exposes.** Design tokens first, then
the instrument layer, with the replayed-step encoding as the priority within the phase.

| # | Work package | Detail |
|---|---|---|
| P7.1 | Design tokens | Surfaces, ink, gridlines, the three identity hues, the status set, the strand gold — **dark and light sets both defined**, as CSS custom properties, nothing hardcoded. `serious` deliberately absent (it failed measurement) |
| P7.2 | Typography and figures | Two families only; proportional figures for the hero and stat values, `tabular-nums` only in columns that must align vertically; **text never wears a data color** |
| P7.3 | Shell and navigation | Persistent sidebar: workspace slot, seven groups, docs link pinned at the bottom; the deployment-mode banner |
| P7.4 | API client and stream hooks | Typed `fetch` client; `useRunStream`, `useFleetStream`, polling fallback, staleness state surfaced |
| P7.5 | `RunThread` | Inline SVG, one continuous wavy path, **one gold**, shape-coded markers (circle/square/ring), marker labels dropped rather than clipped, flow animation that **stops at terminal state**, `compact` mode |
| P7.6 | `RunDetail` | Stacked per-worker bars in identity hues, per-segment logs, the handoff divider that is never collapsed, the footer with the duplicate count leading and recovery suppressed at zero handoffs, kill targeting `ended_at === null` |
| P7.7 | The five mock states | Zero handoffs · three-plus handoffs · `needs_review` · 40 steps · **currently orphaned** (the one a reviewer will see and the easiest to forget) |
| P7.8 | Timeline track | Segments sized by duration with a clickable floor, 2px surface gaps, notched leading edge for tool calls, ghosted fill for replayed steps, full-height fencing markers showing both epochs, worker-id rail fallback |
| P7.9 | All runs | Live table with the compact strand per row **and** the owning-worker column retained, status filters, rows updating in place |
| P7.10 | Needs review | Its own page: full log, failing step highlighted, the ambiguous call, the declared policy, and the resolution actions |
| P7.11 | Fleet and Deployments | Worker cards with kill control; version grouping from `workers.code_version` — no new schema |
| P7.12 | Tools and Test run | Registry showing declared safety categories; a one-off submission form (pre-registered agents only, in every mode) |
| P7.13 | Metrics and Logs | The §12 series in their specified forms — one hero figure per view, no dual axes, a table view for every chart, legends only at two-plus series; global log search by type, worker, epoch, time, with `LEASE_RENEWED` excluded by default |
| P7.14 | Environment | Live-editable settings with the assertion's rejection surfaced as a useful message; **absent in demonstration mode** |
| P7.15 | Dashboard | Active runs, live worker count, steps/sec sparkline inside a stat tile, duplicate counter reading zero |
| P7.16 | States and audits | Loading, empty, and error for every live component; the database-unreachable screen stating that execution is halted deliberately; **grayscale audit**; **reduced-motion audit**; a 40-step layout pass |

**Invariants in play**: none directly — and that is the point. `web/` has no correctness
responsibilities and must never appear to. What it must not do is *misrepresent* them, which is what
P7.16 audits.

**Tests**: component tests for all five mock states; a snapshot suite with `now` injected; an
assertion that no status renders as a bare colored dot; a test that the strand's animation stops at
terminal state.

**Exit gate**: [V7](./quickstart.md#v7--the-console-tells-the-truth-phase-7), including the three
manual audits, which cannot be automated and must not be skipped.

---

## Phase 8 — The chaos harness, the proof, and only then the landing surface

**Goal**: convert the guarantee from a claim into a measured, accumulating, regenerating number — and
then present it.

| # | Work package | Detail |
|---|---|---|
| P8.1 | Migration 003 | `chaos_runs`, `chaos_reports`, `chaos_events`; immutability triggers on all three, active in **both** deployment modes |
| P8.2 | Harness core | Launch N workers, submit M runs with a deliberate mix of step counts, tool types, and durations, driving everything **through the public API** so the console button and the CI run share one implementation |
| P8.3 | Injections | Random worker kills at a configurable rate at random points; latency; simulated stalls aimed at the fencing path; tool failures; **crashes inside the uncertainty window** exercising every declared policy. Each recorded as a `chaos_events` row |
| P8.4 | The five invariants | `invariants.py` as SQL-backed assertions: at most one result per key; `seq` strictly increasing with no duplicates and no gaps; no epoch with two worker ids; every run terminal within bound; every completed log replays to an identical final state |
| P8.5 | Report computation | `report.py`: duplicate and stranded counts, recovery percentiles measured from each kill's `chaos_events.created_at` to the reclaiming `RUN_CLAIMED`, replay overhead, throughput, fencing events, uncertainty entries by policy, dead-letter volume — written with the profile and lease in force |
| P8.6 | Chaos API | `start` (bounded per mode), `list`, `latest`, `{id}/report`; `abandoned` detection for a run interrupted by an API restart |
| P8.7 | Chaos console and history | Configuration and live launch with the invariant panel; permanent history. **This page is the project. It is what you show first.** |
| P8.8 | CI and schedule | Bounded chaos smoke on every push; sustained scheduled run against the deployed instance; an automated job refreshing the README's figures from the latest report |
| P8.9 | Landing bands 1–5 | The claim in two sentences with the live status strip; the hand-built SVG/CSS explainer under a few kilobytes with a labelled static fallback; the guided demo inline; the evidence band whose hero is the generated zero with its timestamp; the architecture band stating prior art, the effectively-once framing, and the single-writer ceiling |
| P8.10 | The guided demo | Four steps, one click each, no navigation: submit → watch → **kill the real worker** → the narrated stall with a lease countdown, the new worker id, the replayed steps, and the sentence stating that their tool calls did not run twice |
| P8.11 | Presets and self-sufficiency | Short, long, and unsafe-tool presets; verified automatic respawn; submission and kill rate limits; the reset affordance that cannot touch chaos history |
| P8.12 | Outbound surface | Wordmark, repository link, console link, live evidence badge (**absent when no report exists**), one-line attribution, footer with the self-hosting statement, the license once one exists, and the design-document link if it was written. Nothing excluded by §32.5 appears — **including notification prompts and any analytics modal or cookie banner beyond the legal minimum**, because a modal between an arriving reviewer and the demo costs the whole reviewer, not part of one |

**Invariants in play**: all eight, as subjects of the assertions rather than as implementation.

**Exit gate**: [V8](./quickstart.md#v8--measured-proof-phase-8) and
[V9](./quickstart.md#v9--the-cold-reviewer-path-phase-8-after-the-chaos-console). **The project's
definition is complete at the end of this phase.**

**Risks**: the sustained run is where an intermittent bug from phase 4 or 5 will finally surface —
which is the harness working as intended. Expect to return to earlier phases from here, and treat that
as the process rather than as a setback.

---

## Phase 9 — The authoring surface *(stretch, optional)*

Begins only after phase 8 is complete. Validator, then editor, then generator. **If only half is
built, the half worth having is the validator.**

| # | Work package | Detail |
|---|---|---|
| P9.1 | The validator | Six static checks — determinism imports (reusing P2.3's AST checker), return shape, module-level mutable state, unregistered tool names, missing safety declarations, unbounded self-recursion |
| P9.2 | Teaching error messages | Each finding names the line and the replacement, e.g. "line 14 calls `datetime.now()`. Agent code must use `ctx.now()` so the value is journaled and replay returns the same timestamp." **An error that teaches the invariant is worth more than the feature that produced it** |
| P9.3 | `validate` endpoint and editor | Available in both modes; runs on keystroke pause and on submission; the page states its deployment mode in the header at all times. **No server-side draft persistence** — no saved drafts, no workspaces, nothing surviving the session beyond the browser, which is what keeps §21.7 true once an editor exists |
| P9.4 | The generator | Seeded with the contract, the one taught constraint, the tool registry, and the three demo agents as worked examples; output **always routed through the validator before display**; never registers, never executes; degrades honestly with no provider key |
| P9.5 | `register`, local only | Route mounted only when `ANCHOR_AUTHORING_EXECUTE=true`; **404 in demonstration mode, not 401 or 403** |
| P9.6 | Boundary tests | The five §31.3 assertions, including that no import path in the API package reaches registry-mutation code in demonstration mode |
| P9.7 | The stated ceiling | Adjacent to the results panel: these six checks are mechanical and **cannot** catch wrong business logic — a loop filtered on the wrong key, an unreachable `Done(...)` branch. Rendered as the pre-registration checklist ("these four judgements are yours"), never as a disclaimer, and never as "all checks passed" standing in for "this agent is correct" (D-59). The generator page carries the same honesty: it states that generation happens at **authoring time on text a human then reviews**, which is why it does not contradict the rule forbidding generated behaviour at runtime |

**Exit gate**: [V11](./quickstart.md#v11--the-deployment-boundary-every-phase-that-adds-a-route) plus
a validator that visibly rejects a deliberately wrong draft on the public instance, **and a results
panel that states what it did not check.**

---

## Cross-cutting workstreams

Not phases, because they span them. Each has a gate.

| Workstream | Content | When |
|---|---|---|
| **README** | Screen recording → generated chaos numbers → architecture → the eight-step quickstart → **the professor-outreach agent verbatim, immediately after the one taught constraint** → a pointer to `demo_long` as the canonical already-done-filter example → glossary → the honest weaknesses section. Self-hosting statement in the first paragraph. The example is not optional: it is the only place the constraint is shown to *buy* something rather than merely to cost something | After phase 8; figures refreshed automatically thereafter |
| **The written design document** | Tradeoffs, rejected alternatives, known limitations, the **framework-adapter shape** (one node per `decide_next_step`, framework state rehydrated from `ctx` — stated, never built), and future work: divergence-aware replay, cost-aware recovery, a generic reconciliation protocol, and semantic compensation — the last **refused rather than deferred**, since generating compensating actions at runtime contradicts the governing rule outright. Cheap to produce, rare in student repositories, and **the artifact a senior reviewer is most likely to actually read** | Add-if-early; the sidebar's docs link and the footer link both point at it |
| **Glossary discipline** | Run · step · event · epoch · lease · fencing · zombie worker · idempotency key · uncertainty window · replay · determinism boundary · dead letter — the same words in the code, the log, the interface, and the docs | From phase 1, enforced at review |
| **The interview narrative** | The four cold-defence decisions (Postgres over a broker; Redis excluded from ownership; step-level checkpointing; database-clock expiry), the zombie whiteboard, the single-writer ceiling and its sharding answer, and the preempted weaknesses | Continuous; gated by definition-of-done item 6 |
| **Third-party quickstart run** | Someone other than the author follows the quickstart from a clean clone | Before calling the project done |

---

## Deferred backlog — unscheduled

**This is deliberately not a phase.** It has no phase number, no work-package numbers, no exit gate,
and no traceability row, and `/speckit-tasks` does not decompose it. A phase number would place these
items *in the build order* — "phase 10" reads as "after phase 9", which is exactly the implied
commitment `anchor-spec.md` §36 withholds. A backlog states the same content with the opposite
default: nothing here is scheduled until someone schedules it. See [research.md](./research.md) D-56.

**Addendum F (§34–§36) — agent-authoring boilerplate.** The gap it names is real and is not one the
runtime can close: a developer can write a `decide_next_step` that satisfies every contract rule and
still has wrong business logic — an unfiltered loop, a missing terminal branch, state held in a
variable. The phase-9 validator catches mechanical violations and **cannot** catch these, which is
why P9.7 makes the ceiling visible rather than leaving the panel to imply otherwise.

| Item | Disposition |
|---|---|
| **`_template.py` scaffold** in `anchor/runtime/agents/`, showing the four-step shape | **Deferred.** If ever built it MUST be a valid, registered, no-op agent that passes the P2.3 AST determinism walk and the P9.1 validator — **not an inert skeleton plus a new exclusion in the AST test.** An exclusion list on that walk is an exclusion list on `I6`, and the first entry always looks harmless. Constraint recorded now so the deferral is safe (D-58) |
| **Demo agents as reference implementations** | **Pulled forward into P5.8** (D-57). Zero added scope, and not retrofittable: they are the chaos harness's workloads, so improving them after phase 8 would change the system under test after the evidence was captured |
| **Four-item pre-registration checklist** | **Already recorded** in [contracts/agent-contract.md](./contracts/agent-contract.md). Documentation of an existing contract, not new product surface; four lines, no build cost. P9.7 renders it as the validator's stated next step |
| **README pointer to `demo_long`** | Folded into the README workstream above, alongside FR-138's verbatim example |

**Nothing here is a prerequisite for anything.** If none of it is ever built, no claim in this plan
becomes untrue and the quickstart of §26.3 still works end to end, which is how developers integrate
infrastructure anyway.

---

## Risk register

| Risk | Signal | Mitigation |
|---|---|---|
| Spurious fencing from a too-short lease | Rising fencing rate on the metrics page | The startup assertion; the fencing-rate series; read a rise as "lease too short relative to **renewal latency**", not as unhealthy workers |
| Canonical serialization drift | None — **it does not error, it double-executes** | The property test; invariant 1 asserting no key ever carries two results; `demo_effects UNIQUE` turning a duplicate into a database error |
| A subtly wrong `RunContext` that passes on happy-path logs | Replay divergence surfacing later as an unrelated-looking invariant failure | Truncated-log fixtures; the `call_ordinal` ordering test; replay tests against logs captured from real fencing incidents |
| The renewer/execution cancellation race | A write appearing after cancellation | P4.2's dedicated test; the single append path checking cancellation before issuing SQL |
| `LEASE_RENEWED` volume swamping the log | Renewal events outnumbering step events several to one | **Closed by D-48**: emitted at boundaries and on latency-threshold breaches only, with the full distribution kept in telemetry. `always` mode remains available for debugging |
| Index write cost on `run_events` | Slower appends under load | Every index has its serving query and write cost recorded; the `(type, created_at)` index is the expensive one and is justified by the Logs page and §12. BRIN on `created_at` supports the rollup scan without a second btree |
| **A future "optimization" time-partitioning the log** | A migration adding `PARTITION BY RANGE (created_at)` | **Closed by D-52** and boxed as a warning in the data model: it would force the key to `(run_id, seq, created_at)`, which does not enforce `(run_id, seq)` uniqueness, silently breaking `I2` while looking routine in the diff |
| **A retry cap that resets on handoff** | A poison run retrying forever, indistinguishable from a stranded run | **Closed by D-43**: attempts derived from `STEP_FAILED` counts in the log, plus the dedicated cross-handoff test |
| **A global cap that caps nothing** | A saturated fleet with no ceiling actually applied | **Closed by D-44**: enforced inside the claim transaction, where `I4` already puts ownership decisions |
| **Worker identity reused after a restart** | Two processes sharing an id; Deployments unable to answer its own question | **Closed by D-42**: label plus incarnation, unique per process lifetime |
| **Schema skew across a booting fleet** | Some processes on the new schema, some not | **Closed by D-45**: one-shot migration step plus a startup refusal on mismatch |
| **Ambiguous tool safety across code versions** | The same crash halting on one worker and re-executing on another | **Closed by D-46**: declaration hashing with a per-tool fail-closed refusal |
| Single PostgreSQL writer ceiling | Throughput curve diverging from the ideal-linear reference | **Not mitigated — measured and published.** The chart asks the interview question, and the answer is partition the log by `run_id` or move to a per-shard writer |
| Chaos harness abandoned by an API restart | A `running` chaos row with a stale heartbeat | Marked `abandoned` on startup and displayed as such. The harness is the rig, not the system under test |
| Public instance abuse | Rate-limit rejections, hourly cap hits | Stubbed models mean compute not money; caps on submission and chaos parameters; nothing destructive exposed; workers self-heal |
| Render cost | — | Accepted deliberately: free tier is disqualifying because a sleeping worker is not a fault-tolerant runtime |
| Phase 4 and 5 overrun | — | Expected and budgeted. The difficulty is the reason the project is worth building |
| Building the console early | — | Prohibited by a hard gate, because a beautiful console over an unproven runtime invites scrutiny the system cannot yet survive |
| **Branching / fork-from-checkpoint reintroduced as "a natural extension"** | A proposal to fork a run at step N and re-execute forward on the journaled prefix — it *is* natural for an event-sourced log, and it would render beautifully in the thread view | **Cut in §28.3 and recorded as load-bearing.** A fork produces two histories sharing a prefix, and `I2` (append-only, ordered, gap-free per run) and `I3` (one writer per run per epoch) both assume **one linear history per run**. Reintroducing it reopens the two invariants that constitute the proof, so it is a Principle IX constitution amendment, never a feature request. It also buys no differentiation: it already ships in a widely-used agent framework and a commercial debugging product |
| **The validator read as a correctness guarantee** | A developer registers an agent because "6 checks passed", and it loops forever or re-sends on every replay | **Closed by D-59 / P9.7**: the panel states what it did not check and renders the pre-registration checklist as the next step. Principle VIII — an interface rendering a partial guarantee as a complete one is the same failure as rendering optimistic state as confirmed |

---

## Traceability

Every functional requirement is delivered by exactly one phase. Success criteria are discharged by the
validation scenarios in [quickstart.md](./quickstart.md).

| Phase | Functional requirements | User stories | Validation |
|---|---|---|---|
| 0 | FR-059, FR-060, FR-061, FR-065, FR-067, FR-070, **FR-128, FR-129** | — | V13 |
| 1 | FR-001, FR-002, FR-005, FR-022 – FR-026, FR-039, FR-040, **FR-132** | US1 (partial) | V1 |
| 2 | FR-027 – FR-036 | US1 | V2 |
| 3 | FR-007 – FR-014, FR-066 | US1 | V3 |
| 4 | FR-015 – FR-021 | US2 | V4 |
| 5 | FR-037, FR-038, FR-041 – FR-050, FR-107, FR-118, FR-119, **FR-131** | US3 | V5, V13 |
| 6 | FR-003, FR-004, FR-006, FR-051 – FR-058, FR-062 – FR-064, FR-071 – FR-074, FR-108, FR-115, **FR-130, FR-133** | US4 | V6, V12, V13 |
| 7 | FR-084 – FR-097, FR-120 | US5 | V7 |
| 8 | FR-068, FR-069, FR-075 – FR-083, FR-098 – FR-106, FR-109 – FR-111, FR-116 | US6, US7 | V8, V9 |
| 9 | FR-112, FR-113, FR-114, FR-123 – FR-127, **FR-134, FR-136, FR-137** | US9 | V11 |
| Cross-cutting | FR-117, FR-121, FR-122, **FR-138, FR-139** | US8 | V10 |

**FR-135 has no phase row, and that is the requirement.** It asserts the *absence* of cross-run write
paths, so it is discharged not by building something in a phase but by a standing assertion in
`tests/boundary` — enumerated in [V11](./quickstart.md#v11--the-deployment-boundary-every-phase-that-adds-a-route),
which by its own terms runs at **every phase that adds a route** and is re-run at every phase gate.
The test derives the set of run-id-accepting mutating routes from the OpenAPI document and matches it
against an explicit allowlist, so a new one fails until it is added deliberately. A requirement
satisfied by code that does not exist has to be guarded continuously, because the thing that violates
it is a future addition rather than a present omission.

**Note on FR-068/069 (the kill endpoint and respawn).** They appear in phase 8 in the table because
that is where they become *product surface*. The mechanism itself is built in phase 0 (P0.5, the kill
subscriber) and exercised from phase 2 onward — V2 depends on it. It is listed once, at the phase
where its user-facing requirement is discharged.

---

## Next step

Run `/speckit-tasks` **per phase**, starting with phase 0, so each task list stays executable. The
work packages above are the intended task boundaries; each should decompose into a handful of tasks
with the phase's tests attached.
