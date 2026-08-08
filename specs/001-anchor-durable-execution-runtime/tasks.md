# Tasks: Anchor — Durable Execution Runtime for AI Agents

**Input**: Design documents from `specs/001-anchor-durable-execution-runtime/`
**Source of intent**: [`anchor-spec.md`](../../anchor-spec.md) §0–§36, Addenda A–F
**Governance**: [constitution v1.1.0](../../.specify/memory/constitution.md)
**Date**: 2026-08-08

---

## How this file is organized, and why it is not organized by user story

> **Read this before the first task.** It records the one structural decision made here, so it is not
> mistaken for a template error.

The task template organizes phases by user story and states that once the foundational phase
completes, *"all user stories can start in parallel."* **For this project that is false, and stating
it would be a governance violation** — constitution Principle VI ("Build Order Is a Dependency
Graph") and [plan.md](./plan.md) → *Phase Sequencing Rules* make the build order normative:

- **Phase 2 is a hard gate.** Nothing proceeds until a killed worker demonstrably resumes correctly.
- **Phase 4 is a hard gate**, and **no console work may begin before it completes** — not tokens, not
  a shell, not a component.
- **No landing surface before phase 8 completes**, because its bands quote figures that do not exist
  earlier and placeholder figures have a way of shipping.
- US2 (fencing) presupposes US1's leases. US3 (the journal) presupposes US2's epoch. US5 (console)
  and US7 (landing) are *prohibited* early rather than merely inconvenient.

**Therefore: the build phase is the sequencing axis, and the user story is a label.** Phases below
are Anchor's phases 0–9, named identically to [plan.md](./plan.md) so the two documents diff cleanly.
Every task that discharges a user story's requirements carries its `[US*]` tag, from plan.md's
traceability table. Phase 0 and the cross-cutting phase carry no story tag, exactly as the template
requires of setup and polish work.

The template's format contract is honored in full on every task: checkbox, sequential ID, `[P]` where
genuinely parallelizable, `[Story]` where applicable, and an exact file path.

### Tests are mandatory, and they are written first

Per constitution Principle V, tests are not optional and are not a separate phase. Each phase below
opens with its test tasks. **Write them, watch them fail, then implement.** Six of the tests in this
file guard holes found by reasoning rather than by failure ([research.md](./research.md) §10) —
[quickstart.md](./quickstart.md) V13 is explicit that each *must be seen to fail against the
pre-pass behaviour before it is trusted*. A test that has never been red has proven nothing.

**No test may make a real model-provider call.** The stub adapter (D-55) is the default on every
path — demo, chaos, and tests — and a real adapter is unreachable from any test by construction.

### Task ID map

| Phase | Task range | Work packages | Stories |
|---|---|---|---|
| 0 — Foundation | T001 – T062 | P0.1 – P0.9 | — |
| 1 — The log is the spine | T063 – T104 | P1.1 – P1.7 | US1 (partial) |
| 2 — Replay *(HARD GATE)* | T105 – T144 | P2.1 – P2.6 | US1 |
| 3 — Concurrency and leases | T145 – T190 | P3.1 – P3.7 | US1 |
| 4 — Fencing *(HARD GATE)* | T191 – T228 | P4.1 – P4.6 | US2 |
| 5 — The two-phase journal | T229 – T292 | P5.1 – P5.9 | US3 |
| 6 — Production-shaped behaviour | T293 – T378 | P6.1 – P6.13 | US4 |
| 7 — The operator console | T379 – T473 | P7.1 – P7.16 | US5 |
| 8 — Chaos, proof, landing | T474 – T551 | P8.1 – P8.12 | US6, US7 |
| 9 — Authoring surface *(stretch)* | T552 – T592 | P9.1 – P9.7 | US9 |
| Cross-cutting | T593 – T622 | — | US8 |

**622 tasks.** The deferred backlog of Addendum F is deliberately absent — see plan.md → *Deferred
backlog*, and D-56 for why giving it tasks would place it in the build order that §36 withholds.

---

## Phase 0 — Foundation *(Setup + Foundational)*

**Goal**: `docker compose up` brings up PostgreSQL, Redis, the API, and three workers that register,
heartbeat, and idle. Configuration refuses to start in a self-fencing state. CI is green.

**Invariants in play**: `I5` (the database clock is the only clock in the SQL from the first
migration), `I7` (fail closed — no execution path exists yet, and the API returns 503 when
PostgreSQL is unreachable).

**⚠️ CRITICAL**: No phase-1 work begins until this phase's exit gate passes. A configuration constant
that lands in a worker loop here is a constant that is still there in phase 6.

### Tests for Phase 0 (MANDATORY) ⚠️

- [x] T001 [P] Write the config-assertion test in `tests/unit/test_config_assertion.py`: both named profiles are accepted; `lease_duration_ms == renewal_interval_ms` is rejected; `lease_duration_ms < 4 × renewal_interval_ms` is rejected; `step_timeout_ms == 0` is rejected; each rejection names the violated relationship and both offending values
- [x] T002 [P] Write the SQLSTATE round-trip test in `tests/unit/test_sqlstate_error_map.py` asserting `AN001→LeaseFencedError`, `AN002→ConfigAssertionError`, `AN003→ImmutableRecordError`, `AN004→ResultOverwriteError`, and that an unmapped SQLSTATE raises the generic database error rather than being swallowed
- [x] T003 [P] Write the dependency-confinement test in `tests/boundary/test_sqlalchemy_confined.py` asserting `sqlalchemy` is imported nowhere outside `ops/migrations/`, by walking the AST of every module under `anchor/`
- [x] T004 [P] Write the epoch-gate trigger test in `tests/unit/test_epoch_gate_trigger.py`: an insert with `epoch <` the run's current epoch raises `AN001`; an insert with `epoch >` the current epoch also raises (a writer inventing an epoch); an insert at the current epoch succeeds
- [x] T005 [P] Write the log-immutability test in `tests/unit/test_run_events_immutable.py` asserting `UPDATE` and `DELETE` on `run_events` both raise `AN003`
- [x] T006 [P] Write the terminal-state constraint test in `tests/unit/test_runs_terminal_check.py`: a row in any terminal status holding `owner_worker_id` or `lease_expires_at` is rejected; a `running` row without both is rejected
- [x] T007 [P] Write the worker-identity constraint test in `tests/unit/test_worker_identity_check.py` asserting `id = label || '#' || incarnation` is enforced by the database and that `(label, incarnation)` is unique
- [x] T008 [P] Write the config-trigger backstop test in `tests/unit/test_runtime_config_assert_trigger.py` asserting a direct `UPDATE` on `runtime_config` that violates the lease relationship raises `AN002` — proving the property holds even when the API is bypassed
- [x] T009 [P] Write the worker-registration test in `tests/unit/test_worker_registration.py`: a worker inserts its row with a fresh `last_seen_at`, a claimed label, and incarnation `1` on an empty slot
- [x] T010 [P] Write the incarnation test in `tests/failure/test_worker_incarnation_never_reused.py`: a worker restarted with **the same hostname and pid** receives a new incarnation and a distinct id, and the prior row survives unmodified (D-42, FR-129)
- [x] T011 [P] Write the schema-version gate test in `tests/boundary/test_schema_version_gate.py`: a process whose built-against revision differs from the applied revision **refuses to start** and names both revisions; no long-running process invokes `alembic upgrade` (D-45, FR-128)
- [x] T012 [P] Write the fail-closed health test in `tests/failure/test_health_db_unreachable.py` asserting `GET /api/health` returns 503 with `database_reachable: false` when PostgreSQL is unreachable, and never reports a cached healthy state

### Implementation for Phase 0

#### P0.1 — Repository scaffold

- [x] T013 Create `pyproject.toml` declaring the frozen dependency set from plan.md → Technical Context, targeting Python 3.12, managed by `uv`; add `uv.lock`. **No dependency outside this set without maintainer approval** (D-04)
- [x] T014 [P] Configure `ruff` (lint + format) in `pyproject.toml` with the rule set enabled repo-wide and no per-file ignores at this stage
- [x] T015 [P] Configure `mypy --strict` in `pyproject.toml` covering all of `anchor/`, with `ops/migrations/` excluded and that exclusion justified in a comment
- [x] T016 [P] Create the `anchor/` package skeleton — `core/{events,leases,journal,replay,determinism,db,config}/`, `worker/{admission,retry,registry}/`, `runtime/{tools,agents}/`, `api/{routers,ws,serializers}/`, `chaos/` — each with an `__init__.py` carrying a one-line statement of that package's responsibility and its boundary
- [x] T017 [P] Create the seven test suites as packages — `tests/{unit,property,replay,concurrency,failure,boundary,contract}/` plus `tests/fixtures/` — each `__init__.py` naming the constitution's test class it maps to (D-33)
- [x] T018 [P] Create `tests/conftest.py` with the PostgreSQL and Redis fixtures that bind to real service containers, an autouse truncation fixture, and **no database double** — every invariant claimed is enforced by PostgreSQL itself (D-34)
- [x] T019 [P] Create `ops/` skeleton — `ops/migrations/`, `ops/compose/`, `ops/deploy/` — with a `README.md` in each stating what belongs there
- [x] T020 [P] Create `web/` as a placeholder directory containing only a `README.md` stating that **no console work may begin before phase 4 completes**, citing the sequencing rule
- [x] T021 [P] Create `.gitignore`, `.env.example` documenting every environment variable including `ANCHOR_AUTHORING_EXECUTE` with its fail-closed default, and `.dockerignore`

#### P0.2 — Configuration module

- [x] T022 Implement the settings model in `anchor/core/config/settings.py` as a `pydantic-settings` model carrying the **fifteen** keys of data-model.md §9, each with its type, unit suffix in the name, and a docstring naming what breaks if it is wrong (FR-059)
- [x] T023 Implement the two named profiles in `anchor/core/config/profiles.py` — `demo` and `production` — with the concrete values for each and a comment stating the recovery bound each profile implies (FR-061)
- [x] T024 Implement the three-part startup assertion in `anchor/core/config/assertion.py`: `lease_duration >= 4 × renewal_interval`, `margin == lease_duration − renewal_interval`, `step_timeout > 0` (FR-060)
- [x] T025 Implement the refuse-to-start path in `anchor/core/config/assertion.py` raising `ConfigAssertionError` that names the violated relationship **and both offending values** — a message that says only "invalid configuration" costs an hour at the worst possible time
- [x] T026 Implement configuration load precedence in `anchor/core/config/loader.py`: `runtime_config` table is authoritative, environment supplies the profile selection and the bootstrap DSN, and **no timing constant is readable from anywhere else** (FR-059)
- [x] T027 Add `tests/boundary/test_no_hardcoded_constants.py` walking the AST of `anchor/` and failing on any numeric literal used as a timeout, interval, or cap outside `anchor/core/config/`

#### P0.3 — Migration 001 and the invariant DDL

- [x] T028 Initialize Alembic in `ops/migrations/` with `env.py` configured **forward-only** — no `downgrade()` bodies, enforced by a test — and a comment stating why reversibility is refused (D-05)
- [x] T029 Write migration 001 in `ops/migrations/versions/001_foundation.py` creating `runs` per data-model.md §1: every column, `CHECK (status IN …)`, `CHECK (epoch >= 0)`, `CHECK (last_seq >= 0)`, `CHECK (attempts >= 0)`
- [x] T030 Add the terminal-state `CHECK` to `runs` in `ops/migrations/versions/001_foundation.py` — terminal status implies `owner_worker_id IS NULL AND lease_expires_at IS NULL AND finished_at IS NOT NULL` (D-23). This is "illegal states unrepresentable" expressed structurally
- [x] T031 Add the running-implies-ownership `CHECK` to `runs` in `ops/migrations/versions/001_foundation.py` — `status = 'running'` implies `owner_worker_id IS NOT NULL AND lease_expires_at IS NOT NULL`
- [x] T032 Add the partial unique index on `runs.client_request_key WHERE client_request_key IS NOT NULL` in `ops/migrations/versions/001_foundation.py` (FR-002)
- [x] T033 Create `run_events` in `ops/migrations/versions/001_foundation.py` with **`PRIMARY KEY (run_id, seq)`** — the single most important constraint in the schema, made the primary key so no DDL ordering exists in which the table lacks it (FR-023)
- [x] T034 Add `run_events` column constraints in `ops/migrations/versions/001_foundation.py`: `CHECK (type IN …)` over all 17 event types, `CHECK (seq > 0)`, `CHECK (epoch >= 0)`, and the `run_id` foreign key
- [x] T035 Write the `run_events_epoch_gate` function and `BEFORE INSERT` trigger in `ops/migrations/versions/001_foundation.py` as raw SQL: `SELECT epoch FROM runs WHERE id = NEW.run_id FOR UPDATE`, raise `AN001` when `NEW.epoch <` current **and** when `NEW.epoch >` current. **The trigger takes the lock itself** so the guarantee does not depend on the caller (D-08, FR-017)
- [x] T036 Write the `run_events_immutable` `BEFORE UPDATE OR DELETE` trigger raising `AN003`, so append-only is a database property rather than a coding convention (FR-022)
- [x] T037 Create `workers` in `ops/migrations/versions/001_foundation.py` per data-model.md §5, including `CHECK (id = label || '#' || incarnation)`, `UNIQUE (label, incarnation)`, `CHECK (role IN ('runner','chaos'))`, `CHECK (current_run_count >= 0 AND current_run_count <= capacity)`, `CHECK (incarnation >= 1)`
- [x] T038 Create one PostgreSQL sequence per fleet-slot label in `ops/migrations/versions/001_foundation.py`, so an incarnation is allocated without a read-modify-write and two racing restarts cannot collide (D-42). **Deviation, documented in the migration**: fleet-slot labels are operator-configurable (`ANCHOR_WORKER_LABEL_POOL`) and unknown at migration time, so a literal per-label `CREATE SEQUENCE` isn't expressible without dynamic DDL. Implemented instead as a `worker_label_incarnations (label PK, next_incarnation)` table, incremented by a single atomic `INSERT ... ON CONFLICT DO UPDATE ... RETURNING`, giving the same per-label-atomic guarantee without requiring labels in advance
- [x] T039 Create `runtime_config` in `ops/migrations/versions/001_foundation.py` with `PRIMARY KEY (key)` and `CHECK (version >= 1)`
- [x] T040 Write the `runtime_config_assert` **statement-level** `AFTER INSERT OR UPDATE` trigger raising `AN002`, re-reading all timing keys. Comment states the reason it is a trigger and not a `CHECK`: the invariant spans rows, and PostgreSQL cannot express a cross-row invariant as a `CHECK`
- [x] T041 Create the `runs` indexes in `ops/migrations/versions/001_foundation.py` — `(status, priority, created_at)` partial on pending, `(lease_expires_at)` partial on running, `(status, created_at DESC)`, `(is_demo, status)` partial, `(chaos_run_id)` partial — each with its serving query and write cost in a SQL comment
- [x] T042 Create the `run_events` indexes in `ops/migrations/versions/001_foundation.py` — `(type, created_at DESC)`, `(worker_id, created_at DESC)`, `(run_id, epoch)` — with the note that `(type, created_at DESC)` is the most expensive index in the schema and is justified by the Logs page and §12 both being spec-required
- [x] T043 Seed the fifteen `runtime_config` keys from the active profile in `ops/migrations/versions/001_foundation.py` with `updated_by = 'seed'`
- [x] T044 Add the partitioning-prohibition warning as a block comment in `ops/migrations/versions/001_foundation.py`: `run_events` MUST NOT be range-partitioned by `created_at`, because the partition key would have to join the unique constraint and `(run_id, seq, created_at)` **does not enforce uniqueness of `(run_id, seq)`** (D-52)
- [x] T045 Add `tests/boundary/test_migrations_forward_only.py` asserting no migration defines a non-empty `downgrade()`

#### P0.4 — Database access layer

- [x] T046 Implement the asyncpg pool in `anchor/core/db/pool.py` with a bounded size read from configuration, an explicit acquire timeout, and a documented crash behaviour for pool exhaustion
- [x] T047 Implement the typed error hierarchy in `anchor/core/db/errors.py`: `LeaseFencedError`, `ConfigAssertionError`, `ImmutableRecordError`, `ResultOverwriteError`, `PayloadTooLargeError`, each a distinct type so a caller can never catch one intending another
- [x] T048 Implement the SQLSTATE → typed error map in `anchor/core/db/errors.py` covering `AN001`–`AN004`, raising a generic database error for anything unmapped rather than swallowing it (FR-018)
- [x] T049 Implement the explicit-SQL module convention in `anchor/core/db/__init__.py`: every statement is a named constant beside the function that issues it, **no ORM on the hot path**, and a docstring rule that each transaction states what must be atomic and why
- [x] T050 Implement `GET /api/health` in `anchor/api/routers/health.py` returning `database_reachable`, `worker_count`, `deployment_mode`, `degraded`, and `schema_revision` — **503 when PostgreSQL is unreachable**, never a cached healthy state (`I7`, FR-072)

#### P0.5 — Worker registration and heartbeat

- [x] T051 Implement fleet-slot label claiming in `anchor/worker/registry/identity.py`: take a label from the configured pool, draw the next value from that label's sequence, and form `{label}#{incarnation}` (D-42, FR-129)
- [x] T052 Implement worker self-registration in `anchor/worker/registry/register.py` inserting hostname, pid, capacity, `code_version`, and `role`, as a **new row per process lifetime** — rows are never updated across incarnations, so fleet history is append-only in practice as well as in principle (FR-065)
- [x] T053 Implement the heartbeat task in `anchor/worker/registry/heartbeat.py` refreshing `last_seen_at` on its own timer, with the crash behaviour stated: a stopped heartbeat is indistinguishable from a dead worker, **which is the intended semantics** (FR-067)
- [x] T054 Implement the Redis kill subscriber in `anchor/worker/registry/kill.py` that hard-exits the process on message with no cleanup — modelling a crash, not a shutdown (FR-068)
- [x] T055 Implement graceful-shutdown handling in `anchor/worker/registry/register.py` setting `stopped_at`, so its **absence** after a hard kill is itself informative

#### P0.6 — Compose topology

- [x] T056 Write `ops/compose/docker-compose.yml` with `postgres:16`, `redis:7`, a **one-shot `migrate` service**, `api`, `worker` scaled to three, and `web`; API and workers carry `depends_on: {migrate: {condition: service_completed_successfully}}` (D-37, D-45)
- [x] T057 Set `restart: always` on the worker service in `ops/compose/docker-compose.yml` so the fleet self-heals after a kill, and add healthchecks for `postgres`, `redis`, and `api` (FR-069, FR-070)
- [x] T058 Set `ANCHOR_AUTHORING_EXECUTE=true` **only** in `ops/compose/docker-compose.yml`, with a comment stating that every other deployment leaves it unset and is therefore demonstration mode by default (§31, FR-111)
- [x] T059 [P] Write the Dockerfiles in `ops/compose/` for the API, worker, and migrate images, each stamping `code_version` from the build SHA into the image environment. **Consolidated, documented in the file**: one shared `Dockerfile.python`, since the three roles run identical code with only the `command:` differing per compose service — which is also what makes the schema-version gate (T060) meaningful, since the code every process compares itself against really is the same code

#### P0.7 — Schema-version gate

- [x] T060 Implement the schema-version gate in `anchor/core/db/schema_gate.py`: read the applied Alembic revision at startup, compare against the revision the code was built against, and **refuse to start on a mismatch, naming both**. Wire it into the API and worker entrypoints, and assert no long-running process invokes `alembic upgrade` (D-45, FR-128)

#### P0.8 — CI workflow

- [x] T061 Write `.github/workflows/ci.yml` running `ruff check`, `ruff format --check`, `mypy --strict`, and `pytest` against `postgres:16` and `redis:7` service containers, with **migrations applied by the one-shot step before tests** and the schema gate active (D-35)

#### P0.9 — Structured logging

- [x] T062 Implement structured logging in `anchor/core/logging.py` — stdlib `logging` with a JSON formatter — where every worker line carries `run_id`, `epoch`, `worker_id`, and `step_index` where applicable. **The epoch is what makes a fencing incident reconstructable from two workers' logs afterwards**, which is the entire reason it is in the log line rather than only in the event (D-40)

**Exit gate**: `docker compose up` → `GET /api/health` reports `worker_count: 3`,
`deployment_mode: local`, `degraded: false`, and the applied schema revision. A worker started with
`lease_duration_ms == renewal_interval_ms` refuses to start and names the relationship. CI green.
→ [V13](./quickstart.md#v13--fleet-and-deployment-integrity-phases-0-5-6)

**Checkpoint**: Foundation ready. Phase 1 may begin. Nothing else may.

---

## Phase 1 — The log is the spine *(US1, partial)*

**Goal**: submit a run via the API; one worker executes a hardcoded three-step agent; every step is
appended to the event log. **Nothing about the run exists anywhere except the log.**

**Invariants in play**: `I1` (the two-phase *ordering* is established — intent committed before
invocation — even though deduplication is not yet possible), `I2` (append-only, contiguous `seq`),
`I4` (submission and claim each in one transaction), `I7`.

**Independent test**: submit a run, read `GET /api/runs/{id}/events`, and reconstruct the complete
history by eye from the log alone.

### Tests for Phase 1 (MANDATORY) ⚠️

- [x] T063 [P] [US1] Write the append-contiguity unit test in `tests/unit/test_append_contiguous.py`: `seq` starts at 1 and increases by exactly 1 across many appends, with no gaps (FR-024)
- [x] T064 [P] [US1] Write the append-rollback test in `tests/unit/test_append_rollback_leaves_no_gap.py` asserting a transaction that rolls back after appending leaves `runs.last_seq` unchanged and no orphaned `seq` — allocation from the run row is what makes this true rather than a sequence, which would gap
- [x] T065 [P] [US1] Write the duplicate-seq test in `tests/unit/test_duplicate_seq_rejected.py` asserting a hand-crafted duplicate `(run_id, seq)` is rejected by the primary key **loudly**, never silently overwritten
- [x] T066 [P] [US1] Write the payload-ceiling test in `tests/failure/test_payload_ceiling.py` asserting a payload above `max_event_payload_bytes` raises `PayloadTooLargeError` carrying the event type and the measured size, and that **nothing is truncated** (D-51, FR-132)
- [x] T067 [P] [US1] Write the submission-dedupe test in `tests/unit/test_client_request_key_dedupe.py` asserting a second submission with the same `client_request_key` returns the existing run rather than creating a second (FR-002)
- [x] T068 [P] [US1] Write the payload-model tests in `tests/unit/test_event_payload_models.py`: each of the 17 event types constructs from a valid payload and **fails at construction** on a missing required field, so a malformed payload never reaches replay
- [x] T069 [P] [US1] Write the full-sequence integration test in `tests/contract/test_completed_run_event_sequence.py` asserting `RUN_SUBMITTED` (by `api`) → per step `STEP_STARTED` → (`TOOL_INTENT`→`TOOL_RESULT` | `LLM_CALLED`) → `STEP_COMPLETED` → `RUN_COMPLETED`, all at one epoch by one worker id
- [x] T070 [P] [US1] Write the nothing-outside-the-log test in `tests/boundary/test_no_state_outside_log.py` asserting no table other than `run_events`, `tool_journal`, and `demo_effects` records what happened during a run
- [x] T071 [P] [US1] Write the keyset-pagination contract test in `tests/contract/test_events_pagination.py` asserting `after_seq` returns exactly the events above that sequence, in order, with a stable page boundary under concurrent appends
- [x] T072 [P] [US1] Write the stub-adapter test in `tests/unit/test_stub_model_adapter.py` asserting the stub returns deterministic completions with configured latency and that `LLM_CALLED.stubbed` is `true` (FR-036, D-55)

### Implementation for Phase 1

#### P1.1 — Event types and payload models

- [x] T073 [US1] Define the 17 event types as a `StrEnum` in `anchor/core/events/types.py`, matching the `CHECK` constraint in `ops/migrations/versions/001_foundation.py` exactly, with a test asserting the two lists cannot drift (FR-025)
- [x] T074 [US1] Implement the 17 payload models in `anchor/core/events/payloads.py` as pydantic models per data-model.md §11, with every ● field required — **a malformed payload fails at construction rather than at replay**, which is the difference between a loud error now and a divergence later
- [x] T075 [US1] Implement the `RunEvent` envelope model in `anchor/core/events/models.py` carrying `run_id`, `seq`, `type`, `payload`, `epoch`, `worker_id`, `step_index`, `created_at`, with the payload discriminated on `type`

#### P1.2 — The append protocol

- [x] T076 [US1] Implement `core.events.append` in `anchor/core/events/append.py` as **one CTE statement** that increments `runs.last_seq` and inserts the event, returning the allocated `seq` (D-07, FR-024)
- [x] T077 [US1] Add the transaction comment to `anchor/core/events/append.py` stating what must be atomic and why: the counter increment and the insert must not be separable, because a gap in `seq` is indistinguishable from a lost event to every reader downstream
- [x] T078 [US1] Enforce the payload ceiling in `anchor/core/events/append.py`, raising `PayloadTooLargeError` before the statement is issued. Comment states why it is not a `CHECK`: the size test requires a `jsonb→text` cast, that cast is `stable` not `immutable`, and PostgreSQL rejects non-immutable expressions in `CHECK` (D-51)
- [x] T079 [US1] Make `anchor/core/events/append.py` the **single append path** for the entire system, and add `tests/boundary/test_single_append_path.py` asserting no module outside it issues an `INSERT INTO run_events`

#### P1.3 — Run submission

- [x] T080 [US1] Implement `POST /api/runs` in `anchor/api/routers/runs.py` per `contracts/openapi.yaml`, validating `agent_type` against the agent registry and returning the run identifier (FR-001)
- [x] T081 [US1] Implement `client_request_key` deduplication in `anchor/api/routers/runs.py` against the partial unique index, returning the existing run on conflict rather than raising (FR-002)
- [x] T082 [US1] Append `RUN_SUBMITTED` attributed to `worker_id: 'api'` inside the submission transaction in `anchor/api/routers/runs.py`, so **even submission is recoverable from the log** (FR-005)
- [x] T083 [US1] Read and report the global concurrency cap and the current running count from `GET /api/health` in `anchor/api/routers/health.py` — **reported, not enforced here**; enforcement lands in the claim statement in phase 3 (FR-003, D-44)

#### P1.4 — Minimal worker loop

- [x] T084 [US1] Implement the worker entrypoint in `anchor/worker/__main__.py` wiring configuration, the schema gate, registration, heartbeat, and the kill subscriber, then entering the loop
- [x] T085 [US1] Implement the naive claim in `anchor/worker/loop.py` taking one `pending` run under `FOR UPDATE`, with a comment marking it as **deliberately naive** — `SKIP LOCKED` arrives in phase 3 and the interim behaviour is stated rather than assumed
- [x] T086 [US1] Implement the step execution loop in `anchor/worker/loop.py` appending `STEP_STARTED` before each action and `STEP_COMPLETED` after, driven by repeated `decide_next_step` invocations
- [x] T087 [US1] Implement run finalization in `anchor/worker/loop.py` appending `RUN_COMPLETED` with `output`, `total_steps`, `total_duration_ms`, and `handoff_count`, and transitioning `runs` to `completed` with the lease released in the same transaction
- [x] T088 [US1] Record the crash behaviour of every await point added by P1.2 and P1.4 in the module docstrings of `anchor/core/events/append.py` and `anchor/worker/loop.py`: a crash before commit leaves no event and no counter advance; a crash mid-run leaves the run `running` with an expiring lease and **no reclaim path yet**, which is the honest interim state phase 2 fixes

#### P1.5 — `StepContext` v1

- [x] T089 [US1] Implement the `StepContext` v1 surface in `anchor/core/determinism/context.py` exposing `input`, `step_index`, `messages`, and `attempt`, per `contracts/agent-contract.md`
- [x] T090 [US1] Implement `ctx.call_tool` in `anchor/core/determinism/context.py` appending `TOOL_INTENT`, **committing it, then invoking** — establishing the ordering that phase 5 will make load-bearing — then appending `TOOL_RESULT` (FR-039, FR-040)
- [x] T091 [US1] Implement `ctx.call_model` in `anchor/core/determinism/context.py` appending `LLM_CALLED` with `prompt_hash`, `response`, `model`, `latency_ms`, and `stubbed`
- [x] T092 [US1] Implement the `ModelAdapter` protocol and `StubAdapter` in `anchor/runtime/tools/model.py`, selected by configuration, with the stub as the default on **every** path — demo, chaos, and tests (D-55)
- [x] T093 [US1] Implement the three action types `ToolCall`, `ModelCall`, `Done` in `anchor/core/determinism/actions.py`, with a runtime rejection of any other return value naming what was returned
- [x] T094 [US1] Document in `anchor/core/determinism/context.py` that the journal table and the three-state lookup are **phase 5** — this version records events only and cannot yet deduplicate, so a crash after a tool executes but before `TOOL_RESULT` currently loses the record

#### P1.6 — The hardcoded agent

- [x] T095 [US1] Implement `anchor/runtime/agents/demo_minimal.py` as search → summarize → notify, returning exactly one action per invocation and holding no state across calls
- [x] T096 [US1] Implement the agent registry in `anchor/runtime/agents/registry.py` with `register(name, fn)` and resolution at claim time, rejecting an unregistered `agent_type` at submission rather than at execution
- [x] T097 [US1] Implement the three placeholder tools used by `demo_minimal` in `anchor/runtime/tools/demo.py` with their configured stub latencies

#### P1.7 — Read endpoints

- [ ] T098 [US1] Implement `GET /api/runs` in `anchor/api/routers/runs.py` with status filtering and keyset pagination, newest first, per `contracts/openapi.yaml`
- [x] T099 [US1] Implement `GET /api/runs/{id}` in `anchor/api/routers/runs.py` returning the run with `orphaned` **derived** as `status = 'running' AND lease_expires_at < now()` — never stored, because storing it would require a writer at the exact moment nobody owns the run (data-model.md §12)
- [x] T100 [US1] Implement `GET /api/runs/{id}/events` in `anchor/api/routers/runs.py` with `after_seq` keyset pagination, ordered by `seq` (FR-026)
- [ ] T101 [P] [US1] Implement the run serializers in `anchor/api/serializers/runs.py` producing exactly the response schemas in `contracts/openapi.yaml`, with a contract test asserting each response validates against its schema
- [x] T102 [P] [US1] Add the FastAPI application factory in `anchor/api/app.py` with router registration, the typed-error exception handlers mapping each database error to its documented status code, and the deployment-mode banner value
- [x] T103 [P] [US1] Add request logging middleware in `anchor/api/middleware.py` emitting the structured JSON line with `run_id` where the route carries one
- [ ] T104 [US1] Run `tests/unit tests/contract tests/boundary` and confirm every phase-1 test now passes that was previously red

**Exit gate**: [V1](./quickstart.md#v1--the-log-is-the-spine-phase-1) — `seq` contiguous from 1, one
worker, one epoch, complete history reconstructable by eye from the log.

**Checkpoint**: US1 is partially delivered — a run executes and is fully recorded, but does not yet
survive a death. That is phase 2.

---

## Phase 2 — Replay *(HARD GATE)* *(US1)*

**Goal**: kill the worker mid-run, restart it, and verify it resumes from the correct step with the
correct context. **This is the moment the project becomes real.**

**Invariants in play**: `I6` (the whole phase), `I2`, `I5`.

> **⚠️ HARD GATE.** Do not proceed to phase 3 until [V2](./quickstart.md#v2--replay-after-death-phase-2--the-hard-gate)
> is clean. Everything else in the project is elaboration on this single behaviour.

### Tests for Phase 2 (MANDATORY) ⚠️

- [ ] T105 [P] [US1] Write the replay-determinism test in `tests/replay/test_replay_determinism.py` folding every fixture log and comparing the final state by **canonical-JSON hash**, not by field-by-field assertion — a field-wise comparison silently omits the field someone forgot to add (D-25, FR-030)
- [ ] T106 [P] [US1] Write the truncated-log replay test in `tests/replay/test_truncated_log_mid_step.py` against a log that ends between `STEP_STARTED` and `STEP_COMPLETED`, asserting the fold produces a context whose `last_completed_step_index` excludes the partial step
- [ ] T107 [P] [US1] Write the call-ordinal test in `tests/replay/test_nondet_call_ordinal.py`: a step calling `ctx.now()` twice replays the two values **in the order they were originally produced**. Without the ordinal the second call receives the first value and the divergence is invisible
- [ ] T108 [P] [US1] Write the AST determinism-ban test in `tests/boundary/test_agents_no_direct_nondeterminism.py` walking every module under `anchor/runtime/agents/` and failing on any reference to `datetime`, `time`, `random`, or `uuid`, naming the offending module and line (FR-035)
- [ ] T109 [P] [US1] Write the kill-and-resume integration test in `tests/failure/test_kill_and_resume.py` asserting a different worker id claims, `REPLAY_COMPLETED.steps_replayed` matches the count that had completed, and execution resumes at `last_completed_step_index + 1` — **not** at step 1
- [ ] T110 [P] [US1] Write the step-skip test in `tests/replay/test_completed_steps_not_reexecuted.py` asserting a step carrying `STEP_COMPLETED` is not re-executed on the resuming worker
- [ ] T111 [P] [US1] Write the derived-attempt test in `tests/unit/test_attempts_derived_from_log.py` asserting the per-step attempt count equals the number of `STEP_FAILED` events for that `step_index`, and that `runs.attempts` is never read by the retry path (D-43, FR-130)
- [ ] T112 [P] [US1] Write the nondet-batching test in `tests/unit/test_nondet_batched_per_step.py` asserting a step emits **one** `NONDET_RECORDED` carrying all its entries, committed in the same transaction as that step's `TOOL_INTENT` — or as `STEP_COMPLETED` when the step has no side effect (D-47, FR-031)
- [ ] T113 [P] [US1] Write the atomicity test in `tests/failure/test_no_effect_with_unrecorded_inputs.py` asserting there is no interleaving in which a `TOOL_INTENT` exists whose `ctx.new_id()`-derived key inputs are unrecorded — the case the batching decision exists to protect
- [ ] T114 [P] [US1] Write the model-replay test in `tests/replay/test_model_not_recalled_on_replay.py` asserting a journaled `LLM_CALLED` returns the recorded completion on replay with **no provider call at all** (FR-034)

### Implementation for Phase 2

#### P2.1 — `core/replay.reconstruct`

- [ ] T115 [US1] Implement `RunContext` in `anchor/core/replay/context.py` as the reconstructed-state container: accumulated messages, `last_completed_step_index`, journaled results by idempotency key, journaled non-deterministic values by `(step_index, kind, call_ordinal)`, and per-step attempt counts
- [ ] T116 [US1] Implement `reconstruct` in `anchor/core/replay/reconstruct.py` as **a pure fold over ordered events with no I/O** — the purity is what makes it unit-testable against fixtures without a database, which is what makes the invariant tests meaningful (FR-027, FR-028)
- [ ] T117 [US1] Implement the per-event fold handlers in `anchor/core/replay/handlers.py`, one per event type, with an explicit handler for every one of the 17 types so a new type cannot be silently ignored by a default branch
- [ ] T118 [US1] Derive the per-step attempt count inside the fold in `anchor/core/replay/reconstruct.py` by counting `STEP_FAILED` per `step_index`. Comment states the failure this prevents: an in-memory counter resets on handoff, and a poison step then retries forever (D-43)
- [ ] T119 [US1] Assert in `anchor/core/replay/reconstruct.py` that `LEASE_RENEWED` contributes **nothing** to the reconstructed state, and add `tests/replay/test_lease_renewed_not_consumed.py` proving it — this is what licenses the conditional emission of D-48

#### P2.2 — Journaled determinism

- [ ] T120 [US1] Implement the per-step non-determinism buffer in `anchor/core/determinism/buffer.py` accumulating `(kind, value, call_ordinal)` in call order
- [ ] T121 [US1] Implement `ctx.now()` in `anchor/core/determinism/context.py` recording kind `time`, returning the recorded value on replay (FR-031, FR-032)
- [ ] T122 [US1] Implement `ctx.random()` in `anchor/core/determinism/context.py` recording kind `random`
- [ ] T123 [US1] Implement `ctx.new_id()` in `anchor/core/determinism/context.py` recording kind `id`, **named separately from `random` deliberately** — a generated identifier that differs across replay is the specific failure that defeats deduplication, so it is individually visible in the log and individually greppable in agent code (FR-033)
- [ ] T124 [US1] Implement the buffer flush in `anchor/core/determinism/buffer.py` writing **one** `NONDET_RECORDED` per step in the same transaction as that step's `TOOL_INTENT`, or as `STEP_COMPLETED` when the step has no effect (D-47)
- [ ] T125 [US1] Implement replay-mode value return in `anchor/core/determinism/context.py` reading back by `(step_index, kind, call_ordinal)` **in original call order**
- [ ] T126 [US1] Implement `ctx.is_replaying` in `anchor/core/determinism/context.py` as informational only, with a docstring stating that branching on it makes replay non-deterministic and that the validator flags it
- [ ] T127 [US1] Document the crash behaviour of each `ctx` call in `anchor/core/determinism/context.py` per `contracts/agent-contract.md`: the three nondet calls are safely re-derivable because **nothing in the world observed the discarded value**; `call_model` costs money not correctness; `call_tool` is the only one whose crash behaviour is a correctness question

#### P2.3 — The AST determinism ban

- [ ] T128 [US1] Implement the shared AST checker in `anchor/core/determinism/ast_check.py` walking a module for references to `datetime`, `time`, `random`, and `uuid`, returning findings with line and column. **Written once here and reused by the phase-9 validator** (D-27)
- [ ] T129 [US1] Write teaching messages for each finding in `anchor/core/determinism/ast_check.py` naming the line and the step-context call that replaces it, per FR-124's phrasing — the message written now is the message the validator surfaces in phase 9

#### P2.4 — Replay on claim

- [ ] T130 [US1] Wire replay into the worker in `anchor/worker/loop.py` so the log is folded **before** any execution on every claim, including the first (FR-027)
- [ ] T131 [US1] Append `REPLAY_COMPLETED` in `anchor/worker/loop.py` carrying `steps_replayed`, `replay_ms`, `last_completed_step_index`, `journal_entries_loaded`, and `nondet_values_loaded` (FR-029)
- [ ] T132 [US1] Resume execution at `last_completed_step_index + 1` in `anchor/worker/loop.py`, with an assertion that the resume index is never lower than the highest completed step

#### P2.5 — Step-level skip

- [ ] T133 [US1] Implement step-level skip in `anchor/worker/loop.py` for steps carrying `STEP_COMPLETED`
- [ ] T134 [US1] Document the interim limitation in `anchor/worker/loop.py`: **step granularity only** — a crash *within* a step, between a tool's execution and its result being recorded, can still double-execute until phase 5. State it in the module docstring so it is not discovered by a reader who assumed otherwise

#### P2.6 — Recorded-log fixtures

- [ ] T135 [P] [US1] Create the happy-path fixture log in `tests/fixtures/logs/completed_short.json` captured from a real completed run
- [ ] T136 [P] [US1] Create the truncated-mid-step fixture in `tests/fixtures/logs/truncated_mid_step.json`
- [ ] T137 [P] [US1] Create the two-owner fixture in `tests/fixtures/logs/reclaimed_after_expiry.json` carrying two `RUN_CLAIMED` events and a handoff
- [ ] T138 [P] [US1] Create the multi-ordinal fixture in `tests/fixtures/logs/two_nondet_calls_one_step.json` exercising `call_ordinal` ordering
- [ ] T139 [P] [US1] Create the replayed-step fixture in `tests/fixtures/logs/with_skipped_steps.json` carrying `STEP_SKIPPED_ON_REPLAY` markers
- [ ] T140 [P] [US1] Implement the fixture loader in `tests/fixtures/__init__.py` returning ordered `RunEvent` lists, with a test asserting every fixture parses against the payload models
- [ ] T141 [US1] Implement a fixture-capture helper in `tests/fixtures/capture.py` that serializes a live run's log to a fixture file, so future fixtures are captured rather than hand-written

#### Phase 2 gate work

- [ ] T142 [US1] Run the full replay suite and confirm every fixture replays to an identical canonical hash
- [ ] T143 [US1] Execute [V2](./quickstart.md#v2--replay-after-death-phase-2--the-hard-gate) end to end against `docker compose`, confirming all six expected outcomes in order
- [ ] T144 [US1] Record the phase-2 gate result in the PR description, including `steps_replayed` from the observed run and the confirmation that effects show no duplicates on the step-skip path

**Exit gate**: [V2](./quickstart.md#v2--replay-after-death-phase-2--the-hard-gate), all six outcomes.

**Checkpoint**: 🎯 **The hard gate.** US1's core claim is demonstrable. Do not proceed until clean.

---

## Phase 3 — Concurrency: skip-locked claiming, leases, background renewal *(US1)*

**Goal**: many identical workers, one shared queue, no central coordinator. Ownership is time-bounded
and extended by a renewer that does not depend on step progress.

**Invariants in play**: `I3` (the epoch now advances, making the phase-0 trigger live), `I4`, `I5`.

**Independent test**: N workers, one available run, exactly one claim succeeds — repeated under load,
asserted exactly rather than statistically.

### Tests for Phase 3 (MANDATORY) ⚠️

- [ ] T145 [P] [US1] Write the claim-contention test in `tests/concurrency/test_exactly_one_claim.py`: N workers, one available run, **exactly one** claim succeeds. No assertion in this file may say "usually" or "eventually" — `SKIP LOCKED` in one transaction makes the property exact (FR-007)
- [ ] T146 [P] [US1] Write the sustained-contention test in `tests/concurrency/test_claim_under_load.py` repeating the above for many runs and many workers, asserting no run is ever claimed twice at the same epoch
- [ ] T147 [P] [US1] Write the reclaim test in `tests/concurrency/test_reclaim_after_expiry.py` asserting the second claim carries `reason: reclaimed_after_lease_expiry` and `epoch + 1`, and that `status` **stays** `running` (data-model.md §1 state machine) (FR-011)
- [ ] T148 [P] [US1] Write the single-statement test in `tests/unit/test_claim_is_one_statement.py` asserting `pending` and expired-lease runs are handled by **one** statement, never two queries (FR-009)
- [ ] T149 [P] [US1] Write the atomic-claim test in `tests/unit/test_claim_transaction_atomic.py` asserting the epoch increment, owner assignment, lease extension, status transition, and `RUN_CLAIMED` append are all one transaction — and that an induced failure after the update leaves none of them (FR-008)
- [ ] T150 [P] [US1] Write the long-step test in `tests/failure/test_long_step_not_fenced.py` asserting a step lasting longer than `lease_duration` is **not** fenced, because the renewer extends independently. This is the behaviour that makes two configuration profiles possible at all (FR-012)
- [ ] T151 [P] [US1] Write the database-clock test in `tests/unit/test_lease_expiry_uses_db_clock.py` asserting lease expiry is evaluated in SQL against `now()` and that no worker's clock appears in any comparison (`I5`, FR-010)
- [ ] T152 [P] [US1] Write the global-cap test in `tests/unit/test_global_cap_enforced_at_claim.py`: submitting far beyond the cap leaves the running count **at** the cap with the remainder `pending`, and **no submission rejected**. A cap applied at submission enforces nothing (D-44, FR-003)
- [ ] T153 [P] [US1] Write the renewal-latency test in `tests/unit/test_renewal_latency_recorded.py` asserting every renewal records its latency to telemetry regardless of whether an event was emitted (D-48)
- [ ] T154 [P] [US1] Write the conditional-emission test in `tests/unit/test_lease_renewed_emit_policy.py` asserting `LEASE_RENEWED` is emitted on `first_after_claim`, on `latency_threshold_exceeded`, and on `final_before_terminal` — and **not** on every renewal under the default policy (D-48)
- [ ] T155 [P] [US1] Write the polling-convoy test in `tests/concurrency/test_idle_backoff_jitter.py` asserting idle workers' poll times spread rather than synchronizing (FR-014)
- [ ] T156 [P] [US1] Write the structured-concurrency test in `tests/failure/test_taskgroup_cancels_sibling.py` asserting a failure in the renewer task cancels the execution task via the `TaskGroup` rather than leaving an orphaned writer

### Implementation for Phase 3

#### P3.1 — The claim statement

- [ ] T157 [US1] Implement the claim CTE in `anchor/core/leases/claim.py` selecting one eligible row — `pending`, **or** `running` with an expired lease — ordered by `priority` then `created_at`, `FOR UPDATE SKIP LOCKED LIMIT 1` (FR-007, D-10)
- [ ] T158 [US1] Extend the claim CTE in `anchor/core/leases/claim.py` to increment `epoch`, set `owner_worker_id`, extend `lease_expires_at` **from `now()`**, set `claimed_at`, and return `(id, epoch)` — all in the same statement (FR-008, FR-010)
- [ ] T159 [US1] Enforce the global concurrency cap **inside** the claim statement in `anchor/core/leases/claim.py` by counting currently-`running` runs in the same CTE. Comment states why: a cap at submission enforces nothing and contradicts §9's "new runs stay pending" (D-44, FR-003)
- [ ] T160 [US1] Append `RUN_CLAIMED` in the claim transaction in `anchor/core/leases/claim.py` carrying `worker_id`, `epoch`, `reason`, `lease_expires_at`, and `previous_worker_id` (FR-011)
- [ ] T161 [US1] Document in `anchor/core/leases/claim.py` why reclaim does **not** change `status`: `orphaned` is a derived display state, and storing it would require a writer at the exact moment nobody owns the run
- [ ] T162 [US1] Add the transaction comment to `anchor/core/leases/claim.py` stating what must be atomic and why — two workers observing the same epoch is the whole failure this statement exists to prevent

#### P3.2 — Claim indexes

- [ ] T163 [US1] Write migration 002 in `ops/migrations/versions/002_claim_indexes.py` adding any claim index not already created in 001, plus the `status` index the global-cap count uses, each with its serving query and write cost recorded as a SQL comment. **Numbering note**: this migration does not appear in plan.md, which labelled phase 5's migration `002` and phase 8's `003`. Because the global-cap count index cannot be specified before D-44 is implemented here, migrations are sequentially `002` (phase 3), `003` (phase 5), `004` (phase 8). Content is unchanged; only the labels shift by one
- [ ] T164 [US1] Add `tests/unit/test_claim_uses_indexes.py` asserting via `EXPLAIN` that both claim branches use their intended partial index rather than a sequential scan

#### P3.3 — Lease renewal

- [ ] T165 [US1] Implement lease renewal in `anchor/core/leases/renew.py` as `UPDATE runs SET lease_expires_at = now() + $interval WHERE id = $1 AND epoch = $2`, returning whether a row was updated — **a zero-row result is a fencing signal**, not a retryable error (FR-012)
- [ ] T166 [US1] Implement the emit policy in `anchor/core/leases/renew.py` per `lease_renewed_emit_policy`: emit on `first_after_claim`, on latency above `renewal_latency_warn_pct` of the lease, on `final_before_terminal`, and on every renewal only in `always` mode (D-48)
- [ ] T167 [US1] Record every renewal's latency to the telemetry path in `anchor/core/leases/renew.py` regardless of emission, so the distribution stays complete while the log stays readable
- [ ] T168 [US1] Document in `anchor/core/leases/renew.py` that the renewer emits **no liveness signal other than lease extension** — there is no heartbeat that can outlive a stalled process, and that absence is the design (FR-012)

#### P3.4 — The `TaskGroup` structure

- [ ] T169 [US1] Implement the per-run `asyncio.TaskGroup` in `anchor/worker/loop.py` holding the execution task and the renewer task, so a failure in either cancels the other by structured concurrency rather than by bookkeeping
- [ ] T170 [US1] Put the renewer on its own timer in `anchor/worker/renewer.py`, **independent of step progress**, and add a comment stating that coupling it to step completion is the mistake that makes long steps unrunnable
- [ ] T171 [US1] Document the crash behaviour in `anchor/worker/loop.py`: a crash between the claim commit and the first step leaves a claimed run with a live lease that expires normally; a crash inside the renewer cancels the sibling rather than orphaning a writer

#### P3.5 — Reclaim polling

- [ ] T172 [US1] Implement the poll loop in `anchor/worker/loop.py` at `reclaim_poll_interval_ms` plus jitter
- [ ] T173 [US1] Implement backoff with jitter on an empty claim in `anchor/worker/loop.py`, so idle workers do not form a polling convoy (FR-014)

#### P3.6 — Fleet telemetry

- [ ] T174 [US1] Update `current_run_count` on claim and release in `anchor/worker/registry/heartbeat.py`, with a comment stating it is **telemetry, not an authority** — admission control reads the worker's own in-process count, and using this column to decide would be a second source of truth (data-model.md §5)
- [ ] T175 [US1] Publish fleet telemetry to the `anchor:fleet` Redis channel in `anchor/worker/registry/heartbeat.py` as **display only** — `last_seen_at` in PostgreSQL remains the only thing anyone reasons about
- [ ] T176 [US1] Implement `GET /api/workers` in `anchor/api/routers/workers.py` returning id, label, incarnation, uptime, `current_run_count`, last-heartbeat age, `code_version`, and `role` (FR-066)
- [ ] T177 [US1] Implement stale-worker detection in `anchor/api/serializers/workers.py` as `now() - last_seen_at` against a threshold, surfacing the register-then-die case (FR-067)

#### P3.7 — Multi-worker verification

- [ ] T178 [US1] Add per-worker step throughput to the structured log in `anchor/worker/loop.py` so three workers competing for real work is observable without a console
- [ ] T179 [US1] Execute [V3](./quickstart.md#v3--claim-contention-phase-3) against a three-worker compose fleet and record the result
- [ ] T180 [US1] Run `tests/concurrency` under repetition (at least 100 iterations) and confirm zero double-claims
- [ ] T181 [P] [US1] Implement `POST /api/workers/{id}/kill` in `anchor/api/routers/workers.py` publishing to the Redis kill channel, documented and presented as a **first-class product feature**, not a debug affordance (FR-068)
- [ ] T182 [P] [US1] Add the graceful-kill variant to `anchor/api/routers/workers.py` that releases the lease on the way out, **labelled distinctly from the hard kill**, so the demo can show both and explain why they differ — presenting a cooperative shutdown as a crash would misrepresent system state (§25.5 closing note)
- [ ] T183 [P] [US1] Write the kill-endpoint contract test in `tests/contract/test_kill_endpoint.py` asserting both variants match `contracts/openapi.yaml` and that the hard kill produces no `stopped_at`
- [ ] T184 [P] [US1] Write the respawn test in `tests/failure/test_worker_respawns.py` asserting a killed worker returns to `GET /api/workers` within seconds **as a new id** with a higher incarnation, the old row unmodified (FR-069)
- [ ] T185 [P] [US1] Write the fleet-saturation test in `tests/failure/test_fleet_saturated.py` asserting excess runs stay `pending` and no worker exceeds its capacity — nothing degrades uniformly
- [ ] T186 [P] [US1] Write the register-then-die test in `tests/failure/test_worker_registers_then_dies.py` asserting the stale `last_seen_at` surfaces the worker as stale rather than as healthy
- [ ] T187 [P] [US1] Write the clock-skew test in `tests/failure/test_clock_skew_irrelevant.py` asserting a worker with a deliberately wrong system clock claims, renews, and expires identically — because every comparison is on the database clock (`I5`)
- [ ] T188 [US1] Record the crash behaviour of every await point added in phase 3 in the relevant module docstrings
- [ ] T189 [US1] Add `tests/boundary/test_redis_never_authoritative.py` asserting no ownership, lease, or liveness decision reads from Redis anywhere in `anchor/` (FR-058)
- [ ] T190 [US1] Run the full suite and confirm every phase-3 test passes

**Exit gate**: [V3](./quickstart.md#v3--claim-contention-phase-3).

**Checkpoint**: US1 is fully delivered. **No console work may begin — phase 4 is next and is a gate.**

---

## Phase 4 — Fencing tokens and the epoch write gate *(HARD GATE)* *(US2)*

**Goal**: deliberately construct a zombie worker and prove the stale worker is rejected, withdraws
silently, and writes nothing. **The hardest and most valuable phase.**

**Invariants in play**: `I3` above all, plus `I2` and `I4`.

**Independent test**: hold a stale epoch across a simulated stall, let a second worker reclaim, then
attempt an append with the stale epoch and assert the database raises `AN001`, that no partial write
landed, and that the fenced worker performs no subsequent write of any kind.

> **⚠️ HARD GATE, and the phase to budget generously.** Concurrency bugs are intermittent, resistant
> to reproduction, and hard to reason about. That difficulty is precisely why the project is worth
> building. The cancellation path is a real race on a different task than the one doing the work — it
> needs a test rather than an argument.

### Tests for Phase 4 (MANDATORY) ⚠️

All in `tests/failure`, each corresponding to a row of §9's failure matrix.

- [ ] T191 [P] [US2] Write the zombie-fencing test in `tests/failure/test_zombie_worker_fenced.py`: a worker holding a stale epoch attempts an append and the **database** raises `AN001` — the rejection comes from the trigger, not from Python (FR-017)
- [ ] T192 [P] [US2] Extend `tests/failure/test_zombie_worker_fenced.py` to assert **no partial write landed** — the run's `last_seq` is unchanged after the rejection
- [ ] T193 [P] [US2] Extend `tests/failure/test_zombie_worker_fenced.py` to assert the fenced worker performs **no subsequent write of any kind**, including no error event through that run's log (FR-019)
- [ ] T194 [P] [US2] Extend `tests/failure/test_zombie_worker_fenced.py` to assert the fenced worker does not retry and returns to the idle pool, claiming other work normally
- [ ] T195 [P] [US2] Write the renewal-cancellation test in `tests/failure/test_renewal_rejected_cancels_run_task.py` asserting a rejected renewal cancels the execution task and **no write follows the cancellation**, verified by the log's final `seq` being unchanged (FR-021)
- [ ] T196 [P] [US2] Write the blocked-loop test in `tests/failure/test_blocked_event_loop_is_reclaimed.py` asserting a fully blocked event loop results in lease expiry and reclaim, **not** in continued renewal — the renewer must be incapable of signalling liveness that outlives a stalled process
- [ ] T197 [P] [US2] Write the epoch-monotonicity test in `tests/unit/test_epoch_never_decrements.py` asserting no code path decrements `epoch`, and that a hand-crafted decrement is rejected by the `CHECK`
- [ ] T198 [P] [US2] Write the typed-error test in `tests/unit/test_fencing_error_distinguishable.py` asserting `LeaseFencedError` is catchable without catching any other database error — a fencing rejection handled as a generic failure would be retried, which is the one thing it must never be (FR-018)
- [ ] T199 [P] [US2] Write the `WORKER_FENCED` payload test in `tests/unit/test_worker_fenced_payload.py` asserting both `stale_epoch` and `current_epoch` are present and required, because §22.4 requires the marker to display both (FR-020)
- [ ] T200 [P] [US2] Write the single-writer-per-epoch test in `tests/concurrency/test_single_writer_per_epoch.py` asserting that across a contended workload, no `(run_id, epoch)` pair ever carries events from two different worker ids (`I3`)
- [ ] T201 [P] [US2] Write the append-cancellation-check test in `tests/failure/test_append_checks_cancellation.py` asserting the single append path checks its own cancellation state **before issuing SQL**, so a cancelled task cannot land a write in flight

### Implementation for Phase 4

#### P4.1 — Fenced-worker withdrawal

- [ ] T202 [US2] Implement fencing detection in `anchor/core/events/append.py` translating `AN001` into `LeaseFencedError` at the single append path, so every writer inherits the behaviour without implementing it
- [ ] T203 [US2] Implement fenced withdrawal in `anchor/worker/loop.py`: catch `LeaseFencedError`, **discard all in-memory state**, write nothing further through that run, perform no retry, and return to the idle pool (FR-019)
- [ ] T204 [US2] Add an explicit guard in `anchor/worker/loop.py` preventing an error event from being appended through a fenced run's log, with a comment stating why: the fenced worker no longer owns the run, and its opinion about what went wrong is exactly the corruption the epoch exists to prevent
- [ ] T205 [US2] Emit the fencing incident to the structured log in `anchor/worker/loop.py` carrying both epochs and the run id — **the local log, not the run's log** — so the incident is reconstructable from two workers' logs afterwards

#### P4.2 — The renewer as fencing detector

- [ ] T206 [US2] Implement rejection handling in `anchor/worker/renewer.py`: a zero-row renewal result raises `LeaseFencedError` rather than being retried
- [ ] T207 [US2] Implement execution-task cancellation in `anchor/worker/renewer.py` on detected fencing, propagating through the `TaskGroup` (FR-021)
- [ ] T208 [US2] Implement the cancellation check in `anchor/core/events/append.py` that inspects the current task's cancellation state immediately before issuing SQL, so a cancelled execution task cannot land a write already in flight
- [ ] T209 [US2] Document the race in `anchor/worker/renewer.py`: the cancellation path acts on a *different task* than the one doing the work, which is why T195 exists as a test rather than as an argument in a comment

#### P4.3 — `WORKER_FENCED`

- [ ] T210 [US2] Append `WORKER_FENCED` from the **surviving writer** in `anchor/core/leases/claim.py` where the fencing is observable, carrying `fenced_worker_id`, `stale_epoch`, `current_epoch`, and `detected_by` (FR-020)
- [ ] T211 [US2] Implement `detected_by` discrimination in `anchor/core/leases/fencing.py` distinguishing `renewer` from `append`, since the two are different races and the console displays which one fired

#### P4.4 — Zombie construction

- [ ] T212 [US2] Implement the test-only stall injection in `anchor/chaos/injections/stall.py` suspending a worker's event loop while it holds a stale epoch, so the zombie scenario is **reproducible rather than anecdotal** (FR-077)
- [ ] T213 [US2] Add a guard in `anchor/chaos/injections/stall.py` making the injection unreachable outside tests and the chaos harness, with `tests/boundary/test_stall_injection_not_reachable.py` asserting no production import path reaches it
- [ ] T214 [US2] Implement the zombie test harness in `tests/failure/conftest.py` providing a reusable "make me a zombie holding epoch N" fixture, since four tests need it and hand-rolling it four times is how they drift apart

#### P4.5 — Blocked-loop verification

- [ ] T215 [US2] Implement blocked-loop simulation in `tests/failure/test_blocked_event_loop_is_reclaimed.py` using a synchronous sleep that starves the loop, and assert lease expiry and reclaim follow
- [ ] T216 [US2] Add an assertion in `anchor/worker/renewer.py`'s docstring and in the test that the renewer cannot renew while the loop is blocked — **this is a property of running on the same loop, and it is load-bearing, not incidental**

#### P4.6 — Fencing-rate counting

- [ ] T217 [US2] Implement the fencing counter in `anchor/core/leases/fencing.py` incrementing on every rejected write, emitted to telemetry so the phase-6 metric series **has history by the time the chart exists**
- [ ] T218 [US2] Document in `anchor/core/leases/fencing.py` that a rising fencing rate reads as "the lease is too short relative to **renewal latency**", not as unhealthy workers — the misreading is the expensive one (FR-071)

#### Phase 4 gate work

- [ ] T219 [US2] Execute [V4](./quickstart.md#v4--the-zombie-worker-is-fenced-phase-4--the-most-valuable-phase) end to end and confirm all five expected outcomes
- [ ] T220 [US2] Run `tests/failure` and `tests/concurrency` under repetition and confirm no intermittent failure across at least 100 iterations
- [ ] T221 [US2] Write the fencing narrative in `docs/fencing.md`: the zombie timeline, why the epoch must be monotonic, and why the check must live in the database
- [ ] T222 [US2] **Whiteboard the fencing mechanism cold, without notes.** This is a non-mechanical exit gate and it is the one the source spec calls "the real bar" (SC-018)
- [ ] T223 [P] [US2] Add `tests/failure/test_duplicate_seq_under_contention.py` asserting that under deliberate racing, a duplicate `(run_id, seq)` is rejected by the primary key rather than overwriting
- [ ] T224 [P] [US2] Add `tests/failure/test_two_workers_race_same_run.py` asserting the race is structurally impossible — one locking transaction that skips rows locked elsewhere
- [ ] T225 [P] [US2] Add `tests/replay/test_replay_from_fencing_incident_log.py` replaying a log captured from a real fencing incident, since a `RunContext` bug that survives happy-path logs is the highest-value risk in the project
- [ ] T226 [P] [US2] Capture a fencing-incident log into `tests/fixtures/logs/fencing_incident.json` from the T219 run
- [ ] T227 [US2] Record the crash behaviour of every await point added in phase 4 in the relevant module docstrings
- [ ] T228 [US2] Record the phase-4 gate result in the PR description, including the observed `AN001` rejection and the unchanged `last_seq`

**Exit gate**: [V4](./quickstart.md#v4--the-zombie-worker-is-fenced-phase-4--the-most-valuable-phase),
plus the whiteboard gate of T222.

**Checkpoint**: 🎯 **The second hard gate.** US2 delivered. Console work is now unblocked — but phase
5 comes first, because the headline guarantee does not hold until it does.

---

## Phase 5 — The two-phase journal, canonical hashing, and uncertainty policies *(US3)*

**Goal**: the "no double email" guarantee. **The product's headline claim holds from the end of this
phase and not before**, and no claim about it may be published, demonstrated, or written into a README
until it does.

**Invariants in play**: `I1` and `I8` (the whole phase), plus `I2` and `I6`.

**Independent test**: run the demo agent to completion, replay its log, and assert every `send_email`
idempotency key carries at most one result and `demo_effects` holds exactly one row per logical side
effect. Separately inject a crash between `TOOL_INTENT` and `TOOL_RESULT` for one tool of each
declared category and assert the documented resolution for each.

### Tests for Phase 5 (MANDATORY) ⚠️

- [ ] T229 [P] [US3] Write the canonical-serialization property test in `tests/property/test_canonical_serialization.py` using `hypothesis`: structurally identical arguments in **any** mapping key order, **any** nesting traversal, and **any** numeric formatting hash identically. **This is the test that protects the entire idempotency mechanism** (FR-038)
- [ ] T230 [P] [US3] Extend `tests/property/test_canonical_serialization.py` to assert non-JSON-native types — `set`, `tuple`, `datetime`, `Decimal`, `NaN`, `±Infinity` — raise at call time **with the path to the offending value**, because the alternative is a key that varies across replay and fails silently (D-13)
- [ ] T231 [P] [US3] Write the key-framing test in `tests/unit/test_idempotency_key_framing.py` asserting the key is hashed over a canonical JSON **array** `[run_id, step_index, action_name, args]`, never a delimited string — framing is unambiguous by construction rather than by argument about which characters are legal in a tool name (D-41)
- [ ] T232 [P] [US3] Write the key-stability test in `tests/replay/test_key_identical_across_replay.py` asserting the same step re-derives an identical key on replay, including when `ctx.new_id()` feeds the arguments
- [ ] T233 [P] [US3] Write the journal-uniqueness test in `tests/unit/test_journal_one_intent_per_key.py` asserting a second intent row for the same key is rejected by the primary key (FR-041)
- [ ] T234 [P] [US3] Write the result-once trigger test in `tests/unit/test_tool_journal_result_once.py` asserting `NULL → result` is permitted, an `attempts` increment is permitted, setting `resolution` is permitted, and **overwriting a non-null `result` with a different value raises `AN004`**. A result, once recorded, is final
- [ ] T235 [P] [US3] Write the three-state lookup test in `tests/unit/test_journal_three_state_lookup.py` covering all three: row with result → skip and return; no row → execute; **row with `result IS NULL` → apply policy** (FR-042, FR-043)
- [ ] T236 [P] [US3] Write the uncertainty-window test in `tests/failure/test_uncertainty_window.py` with one case per declared category — `retry_safe` re-executes with the key passed through and produces one effect row; `reconcilable` runs the reconciler and branches, recording `resolution`; `unsafe` halts as `needs_review` holding **no lease** (FR-047, FR-048, FR-049)
- [ ] T237 [P] [US3] Extend `tests/failure/test_uncertainty_window.py` to assert a `reconcile_fn` returning `Unknown()` **escalates to `needs_review`** — a reconciler that guesses is worse than no reconciler, because it converts an honest halt into a silent double execution
- [ ] T238 [P] [US3] Write the registration-refusal tests in `tests/unit/test_tool_registration_refusals.py` for all three conditions: absent or invalid `safety`; `reconcilable` without `reconcile_fn`; `retry_safe` with neither `naturally_idempotent` nor `provider_accepts_key` (FR-045, FR-046)
- [ ] T239 [P] [US3] Write the registry `CHECK` tests in `tests/unit/test_tool_registry_checks.py` asserting the same three rules hold against a direct `INSERT`, so a row inserted by **any** path still satisfies them
- [ ] T240 [P] [US3] Write the declaration-conflict test in `tests/failure/test_tool_declaration_conflict.py`: two code versions registering one tool with different safety fields makes **that tool, and only that tool**, unexecutable fleet-wide, with both dissenting versions recorded and surfaced (D-46, FR-131)
- [ ] T241 [P] [US3] Extend `tests/failure/test_tool_declaration_conflict.py` to assert the uncertainty window is **never** resolved from an ambiguous declaration — the run halts instead
- [ ] T242 [P] [US3] Write the `demo_effects` uniqueness test in `tests/failure/test_demo_effects_unique.py` asserting a forced double execution is **rejected by the database**, not merely counted. The rejection is a loud failure rather than a silent duplicate row
- [ ] T243 [P] [US3] Write the operator-resolution test in `tests/contract/test_resolve_endpoint.py` asserting the write is attributed to `worker_id: "operator"` at the run's current epoch, is permitted **only on a leaseless `needs_review` run**, and offers three outcomes none of which is a guess (D-24, FR-050)
- [ ] T244 [P] [US3] Write the skip-marker test in `tests/replay/test_step_skipped_on_replay_emitted.py` asserting `STEP_SKIPPED_ON_REPLAY` carries `idempotency_key`, `tool_name`, `original_result_at`, and `original_epoch` so the console can render the distinction
- [ ] T245 [P] [US3] Write the intent-before-invocation test in `tests/failure/test_intent_committed_before_invocation.py` asserting no side effect can occur without a **preceding committed** journaled intent — the inverse ordering would make an unrecorded side effect possible, which the constitution forbids outright (FR-057)
- [ ] T246 [P] [US3] Write the one-effect-per-step test in `tests/unit/test_one_side_effect_per_step.py` asserting a step containing two side-effecting tool calls is rejected — this is what makes the key unique without a within-step counter (D-26)

### Implementation for Phase 5

#### P5.1 — Canonical serialization

- [ ] T247 [US3] Implement canonical JSON serialization in `anchor/core/journal/canonical.py`: sorted keys, compact separators, NFC-normalized strings, shortest-round-trip float formatting
- [ ] T248 [US3] Implement the type rejection in `anchor/core/journal/canonical.py` raising on `NaN`, `±Inf`, `set`, `tuple`, `datetime`, `Decimal`, and any non-JSON-native type, **carrying the JSON path to the offending value** so the author is told where rather than that
- [ ] T249 [US3] Document in `anchor/core/journal/canonical.py` the failure this module prevents: serialization drift **does not error, it double-executes** — which is why it is guarded by a property test rather than by examples

#### P5.2 — Idempotency key derivation

- [ ] T250 [US3] Implement key derivation in `anchor/core/journal/keys.py` as `sha256(canonical_json([run_id, step_index, action_name, args]))`, hashed over a canonical **array** so framing is unambiguous by construction (D-41, FR-037)
- [ ] T251 [US3] Store the full hex key and compute `args_hash` separately in `anchor/core/journal/keys.py`, with the short display form derived for the UI only and never used as an identity
- [ ] T252 [US3] Add `tests/unit/test_key_display_form_never_identity.py` asserting no lookup, comparison, or constraint uses the truncated display form

#### P5.3 — Migration 003

- [ ] T253 [US3] Write migration 003 in `ops/migrations/versions/003_journal.py` creating `tool_journal` per data-model.md §3 with `PRIMARY KEY (idempotency_key)`, the `(result IS NULL) = (result_at IS NULL)` `CHECK`, the `resolution` `CHECK`, and `CHECK (attempts >= 1)`
- [ ] T254 [US3] Create `tool_registry` in `ops/migrations/versions/003_journal.py` per data-model.md §4, including the safety `CHECK`, the **`reconcilable` implies `has_reconcile_fn`** `CHECK`, the **`retry_safe` implies `naturally_idempotent OR provider_accepts_key`** `CHECK`, and the conflict-columns-move-together `CHECK`
- [ ] T255 [US3] Create `demo_effects` in `ops/migrations/versions/003_journal.py` with **`UNIQUE (idempotency_key)`** — the single strongest piece of evidence in the product, because it makes a double execution a database error rather than a counted anomaly
- [ ] T256 [US3] Write the `tool_journal_result_once` `BEFORE UPDATE` trigger in `ops/migrations/versions/003_journal.py` permitting only `NULL → result`, `attempts` increment, and setting `resolution`, raising `AN004` otherwise. Comment states that without it, `I1` would hold only for as long as every write path remembered not to overwrite
- [ ] T257 [US3] Write the `tool_journal_no_delete` `BEFORE DELETE` trigger in `ops/migrations/versions/003_journal.py` raising `AN003`
- [ ] T258 [US3] Create the journal indexes in `ops/migrations/versions/003_journal.py` — `(run_id, step_index)`, `(tool_name, result_at DESC)`, and the **partial index `WHERE result IS NULL`** that finds every open uncertainty window in one scan and backs both invariant checking and the Needs review page

#### P5.4 — Two-phase `call_tool`

- [ ] T259 [US3] Implement the three-state journal lookup in `anchor/core/journal/lookup.py` returning `Completed(result)`, `NeverAttempted`, or `Uncertain` — the three states are a closed enum, so a fourth branch cannot be added by accident
- [ ] T260 [US3] Rewrite `ctx.call_tool` in `anchor/core/determinism/context.py` around the three-state lookup: skip / execute / apply policy
- [ ] T261 [US3] Implement the intent phase in `anchor/core/journal/two_phase.py` inserting the `tool_journal` row and appending `TOOL_INTENT` in one transaction, **committed before invocation** (FR-039)
- [ ] T262 [US3] Flush the step's non-determinism buffer inside the intent transaction in `anchor/core/journal/two_phase.py`, so a key's inputs and the intent commit atomically and no effect can exist whose inputs are unrecorded (D-47)
- [ ] T263 [US3] Implement the result phase in `anchor/core/journal/two_phase.py` updating `result` and `result_at` and appending `TOOL_RESULT` under the same key (FR-040)
- [ ] T264 [US3] Emit `STEP_SKIPPED_ON_REPLAY` on the skip path in `anchor/core/journal/two_phase.py` carrying the original `result_at` and `epoch`, so the console can render replayed steps distinctly (FR-043)
- [ ] T265 [US3] Enforce one side effect per step in `anchor/core/determinism/context.py`, raising on a second side-effecting call within a step (D-26)
- [ ] T266 [US3] Document the crash behaviour of each window in `anchor/core/journal/two_phase.py`: between intent commit and invocation → no effect occurred, policy resolves conservatively; between invocation and result → **the uncertainty window**; between result and `STEP_COMPLETED` → the result is durable and the step re-completes harmlessly

#### P5.5 — Tool registration and declarations

- [ ] T267 [US3] Implement `register_tool` in `anchor/runtime/tools/registry.py` per `contracts/tool-contract.md`, with the three refusal conditions and **no default safety category** — the decision must be made deliberately and there is nothing to fall back to (FR-045)
- [ ] T268 [US3] Implement declaration content-hashing in `anchor/runtime/tools/registry.py` over the five safety-relevant fields, upserting at worker startup (D-46)
- [ ] T269 [US3] Implement conflict detection in `anchor/runtime/tools/registry.py`: an existing row with a **different** hash sets `conflict_at` and `conflict_version`, recording both `code_version`s
- [ ] T270 [US3] Implement the per-tool fail-closed refusal in `anchor/core/journal/two_phase.py` — a tool with `conflict_at IS NOT NULL` is refused for execution **fleet-wide, that tool only**, not the worker and not the fleet (FR-131)
- [ ] T271 [US3] Document in `anchor/runtime/tools/registry.py` why the conflict is stored rather than logged: during a rolling deploy the table and the code can disagree about *the policy that resolves the uncertainty window*, and a tool reclassified between builds would halt on one worker and re-execute on another, in the same fleet, non-deterministically. `I8` says uncertainty is resolved by the declared policy — if the declared policy is ambiguous, `I8` has no content
- [ ] T272 [US3] Implement `GET /api/tools` in `anchor/api/routers/registry.py` returning every registry row with its declared category, reconciler presence, conflict state, and last-used timestamp (FR-120)
- [ ] T273 [US3] Update `last_used_at` on execution in `anchor/core/journal/two_phase.py`

#### P5.6 — The three uncertainty policies

- [ ] T274 [US3] Implement the `retry_safe` policy in `anchor/core/journal/policies.py` re-executing **with the idempotency key passed through** so the provider deduplicates on their side, and incrementing `attempts` (FR-047)
- [ ] T275 [US3] Implement the `reconcilable` policy in `anchor/core/journal/policies.py` invoking `reconcile_fn` with the same canonical arguments the intent recorded, and branching on `Executed` / `NotExecuted` (FR-048)
- [ ] T276 [US3] Implement `Unknown()` escalation in `anchor/core/journal/policies.py` routing to `needs_review` rather than defaulting to either branch
- [ ] T277 [US3] Implement the `unsafe` policy in `anchor/core/journal/policies.py`: set the run to `needs_review`, halt, **release the lease**, and append `RUN_NEEDS_REVIEW` carrying `step_index`, `idempotency_key`, `tool_name`, `reason`, and `available_resolutions`. **Do not guess** (FR-049)
- [ ] T278 [US3] Record the applied policy on the journal row's `resolution` and `resolved_at` in `anchor/core/journal/policies.py` (FR-044)
- [ ] T279 [US3] Add `tests/boundary/test_needs_review_holds_no_lease.py` asserting a `needs_review` run satisfies the terminal-state-style `CHECK` and cannot block reclaim while looking healthy

#### P5.7 — Operator resolution

- [ ] T280 [US3] Implement `POST /api/runs/{id}/resolve` in `anchor/api/routers/runs.py` with three outcomes — `mark_executed`, `mark_not_executed`, `retry` — none of which is a guess (FR-050)
- [ ] T281 [US3] Restrict the resolution write in `anchor/api/routers/runs.py` to a **leaseless `needs_review` run**, writing through `core.events.append` as `worker_id: 'operator'` at the run's current epoch. Comment states the exception's justification: this is the one permitted `api/` write into a run's log, and it is safe precisely because no worker can be racing a run nobody owns (D-24)
- [ ] T282 [US3] Implement `GET /api/runs?status=needs_review` and the ambiguous-call serializer in `anchor/api/serializers/runs.py` returning the specific call, its declared policy, and the available resolutions

#### P5.8 — The three demo agents *(reference implementations, per D-57)*

- [ ] T283 [US3] Implement `anchor/runtime/agents/demo_short.py` — 8–10 steps, 25–40 s total, varied 2–5 s step durations
- [ ] T284 [US3] Implement `anchor/runtime/agents/demo_long.py` at roughly 40 steps as **the canonical worked example of the already-done filter pattern** — the loop's progress lives in the journal via `ctx.completed_tool_args(...)`, never in a counter. The README points at this file by name (D-57, FR-138)
- [ ] T285 [US3] Implement `anchor/runtime/agents/demo_unsafe.py` crashing inside the uncertainty window, so the `needs_review` path is reachable from the interface
- [ ] T286 [US3] Write all three agents in `anchor/runtime/agents/` to reference-implementation quality with explanatory comments, since they are simultaneously the chaos harness's workloads and §27.4's few-shot examples. **This bar is not retrofittable** — improving them after phase 8 would change the system under test after the evidence was captured (D-57)
- [ ] T287 [US3] Implement the five demo tools in `anchor/runtime/tools/demo.py` — `web_search` and `fetch_page` (`retry_safe`, naturally idempotent), `create_ticket` (`reconcilable`), `send_email` (`unsafe`), `charge_card` (`retry_safe`, only because the provider accepts a key — the declaration names the reason) (§21.5)
- [ ] T288 [US3] Implement `reconcile_fn` for `create_ticket` in `anchor/runtime/tools/demo.py` returning `Executed` / `NotExecuted` / `Unknown`, located by the same key the tool would have used

#### P5.9 — `demo_effects` writes

- [ ] T289 [US3] Write one `demo_effects` row per side-effect execution in `anchor/runtime/tools/demo.py`, carrying the run, step, tool, key, and a payload describing what the fake effect "did"
- [ ] T290 [US3] Implement `GET /api/runs/{id}/effects` in `anchor/api/routers/runs.py` returning the rows and a total — **the ground truth a reviewer can check without trusting the log** (FR-107)
- [ ] T291 [US3] Execute [V5](./quickstart.md#v5--effectively-once-including-the-uncertainty-window-phase-5) end to end, including the honest-resolution path
- [ ] T292 [US3] Record the crash behaviour of every await point added in phase 5, and update `anchor/worker/loop.py`'s docstring to **remove** the phase-2 interim limitation note — within-step uncertainty is now handled, and the headline guarantee holds from here

**Exit gate**: [V5](./quickstart.md#v5--effectively-once-including-the-uncertainty-window-phase-5).

**Checkpoint**: 🎯 **US3 delivered. The product's headline guarantee now holds.** From this point the
claim may be stated — and not before.

---

## Phase 6 — Production-shaped behaviour *(US4)*

**Goal**: predictable behaviour under load and repeated failure; live configuration; real-time
fan-out; the observability surface the console will render.

**Invariants in play**: `I7` (fail closed on database loss; Redis loss degrades display only), plus
`I2`, `I5`, `I8`.

**Independent test**: submit more runs than the global cap permits and assert the excess stay
`pending` with no worker over its limit; separately register a deterministically failing tool and
assert the run reaches `failed` after exactly `max_attempts_per_step` attempts with backoff intervals
inside the jittered bounds.

### Tests for Phase 6 — the complete §9 failure matrix (MANDATORY) ⚠️

One module per row. This is the phase where the matrix is completed, not sampled.

- [ ] T293 [P] [US4] Write the retry-backoff test in `tests/failure/test_retry_backoff_jitter.py` asserting intervals fall inside the ±25% jittered bounds, are bounded by `backoff_cap_ms`, and that retry is **at step granularity only**, never run granularity (FR-051, FR-052)
- [ ] T294 [P] [US4] Write the dead-letter test in `tests/failure/test_dead_letter_on_attempt_cap.py` asserting `RUN_FAILED` carries `dead_lettered: true`, status becomes `failed`, the lease is released, and the run appears in the dead-letter view (FR-053)
- [ ] T295 [P] [US4] Write the attempt-cap-survives-handoff test in `tests/failure/test_attempt_cap_survives_handoff.py`: a deterministically failing step, with its worker killed **between every attempt**, reaches `failed` after exactly `max_attempts_per_step` *total* attempts. **Against an in-memory counter this test does not fail, it hangs** — which is precisely the production symptom it exists to prevent (D-43, FR-130)
- [ ] T296 [P] [US4] Write the cancellation test in `tests/failure/test_cancel_between_steps_only.py` asserting the flag is checked at a step boundary and **never mid-step**, and that the run finalizes as `cancelled` (FR-054)
- [ ] T297 [P] [US4] Write the pending-cancel test in `tests/failure/test_cancel_pending_run_immediate.py` asserting a `pending` run is finalized by the API without a claim, an epoch increment, or a replay — it is leaseless, so no worker can be racing it (D-54)
- [ ] T298 [P] [US4] Write the per-worker admission test in `tests/concurrency/test_per_worker_capacity.py` asserting a worker at its limit does not claim and sleeps briefly instead (FR-004)
- [ ] T299 [P] [US4] Write the step-timeout test in `tests/failure/test_step_timeout_stops_renewer.py` asserting a step exceeding `step_timeout_ms` fails **and the renewer stops**, so the lease lapses and the run is reclaimed rather than held (FR-013, FR-055)
- [ ] T300 [P] [US4] Write the database-unavailable test in `tests/failure/test_database_unavailable.py` asserting nothing executes, workers back off and retry, and **no side effect occurred without a durable record**. Failing closed is the correct behaviour and the test asserts it as such (FR-056)
- [ ] T301 [P] [US4] Write the Redis-unavailable test in `tests/failure/test_redis_unavailable.py` asserting execution is entirely unaffected and only live push degrades (FR-058)
- [ ] T302 [P] [US4] Write the slow-WebSocket-client test in `tests/failure/test_slow_ws_client_dropped.py` asserting a client exceeding its bounded queue is closed with `1013` and a `bye` frame naming `last_sent_seq`, and can then backfill from `after_seq` (FR-074)
- [ ] T303 [P] [US4] Write the configuration-rejection test in `tests/failure/test_config_change_rejected.py` asserting a change violating the lease relationship returns 422 naming the relationship and both values, and that **the configuration is unchanged and the fleet is unaffected** (FR-063)
- [ ] T304 [P] [US4] Write the config-boundary test in `tests/boundary/test_config_route_unmounted_in_demo.py` asserting `PATCH /api/config` returns **404** in demonstration mode (FR-064)
- [ ] T305 [P] [US4] Write the step-boundary-application test in `tests/unit/test_config_applied_at_step_boundary.py` asserting a live configuration change takes effect only at a step boundary, never mid-step (FR-062)
- [ ] T306 [P] [US4] Write the publish-after-commit test in `tests/failure/test_publish_after_commit.py` asserting no event is published to Redis before its transaction commits — a notification about an uncommitted write would be a lie (D-50)
- [ ] T307 [P] [US4] Write the rollup-rebuild test in `tests/unit/test_rollup_rebuild_matches_live.py` asserting that truncating `metrics_rollup` and running `REBUILD` reproduces every bucket exactly as the live aggregation computes it — which is what proves the rollup is derived rather than a second source of truth (D-49, FR-133)
- [ ] T308 [P] [US4] Write the correctness-reads test in `tests/boundary/test_correctness_reads_never_from_rollup.py` asserting the duplicate-effect count, stranded-run count, `needs_review` list, effect counts, and every chaos-report figure are computed from `tool_journal` and `run_events`, **never** from `metrics_rollup`. A stale zero on the duplicate counter is the single most damaging thing this product could display
- [ ] T309 [P] [US4] Write the no-trigger-on-append test in `tests/boundary/test_rollup_not_maintained_by_trigger.py` asserting no trigger on `run_events` maintains the rollup — a trigger would make every worker contend on one bucket row and serialize appends across runs that currently never contend (D-49)
- [ ] T310 [P] [US4] Write the payload-ceiling dead-letter test in `tests/failure/test_payload_ceiling_dead_letters.py` asserting an oversized payload fails the step, exhausts attempts, and dead-letters with the event type and measured size in the reason — **nothing truncated** (D-51, FR-132)
- [ ] T311 [P] [US4] Write the WebSocket framing contract test in `tests/contract/test_ws_framing.py` against `contracts/websocket.md`: `hello` then `snapshot` on connect, per-event frames carrying `seq`, and the `lag` frame on orphan transition
- [ ] T312 [P] [US4] Write the reconnect-race test in `tests/failure/test_ws_snapshot_after_events.py` asserting a client that receives `snapshot` after `event` frames discards events with `seq <= snapshot.last_seq`
- [ ] T313 [P] [US4] Write the timeline-shape contract test in `tests/contract/test_timeline_matches_component_props.py` asserting `GET /api/runs/{id}/timeline` produces **exactly** the `RunDetail` prop shape from `contracts/component-contract.md`, so the component stays a pure function of props
- [ ] T314 [P] [US4] Write the rate-limit test in `tests/boundary/test_rate_limits_under_load.py` asserting submission and kill endpoints enforce their limits under concurrent load (FR-006)
- [ ] T315 [P] [US4] Write the reset-affordance test in `tests/boundary/test_reset_never_touches_chaos.py` asserting the reset prunes completed demo runs and leaves `chaos_events` and `chaos_reports` untouched (FR-108)
- [ ] T316 [P] [US4] Write the global-cap saturation test in `tests/concurrency/test_fleet_saturation_leaves_pending.py` asserting the running count sits at the cap, the remainder are `pending`, and **no submission was rejected** (FR-003)

### Implementation for Phase 6

#### P6.1 — Retry

- [ ] T317 [US4] Implement exponential backoff with ±25% jitter in `anchor/worker/retry/backoff.py`, bounded by `backoff_cap_ms`, with every constant read from configuration (FR-052)
- [ ] T318 [US4] Implement step-granularity retry in `anchor/worker/retry/policy.py`, taking the attempt number from the **log-derived** count rather than from memory (D-43, FR-051)
- [ ] T319 [US4] Append `STEP_FAILED` in `anchor/worker/retry/policy.py` carrying `attempt`, `error_type`, `error_message`, `will_retry`, and `backoff_ms`

#### P6.2 — Dead-lettering

- [ ] T320 [US4] Implement the attempt cap in `anchor/worker/retry/policy.py` reading the derived count, so **the cap holds across arbitrary handoffs** (FR-053)
- [ ] T321 [US4] Implement dead-lettering in `anchor/worker/retry/policy.py` appending `RUN_FAILED` with `dead_lettered: true`, setting status `failed`, and releasing the lease in one transaction
- [ ] T322 [US4] Implement the dead-letter view in `anchor/api/routers/runs.py` as a filtered query with the failing step and reason surfaced

#### P6.3 — Cooperative cancellation

- [ ] T323 [US4] Implement `POST /api/runs/{id}/cancel` in `anchor/api/routers/runs.py` setting `cancel_requested_at` on a `running` run and **finalizing a `pending` run directly** (D-54)
- [ ] T324 [US4] Implement the between-steps cancellation check in `anchor/worker/loop.py`, never mid-step, finalizing as `cancelled` with `RUN_CANCELLED` carrying `requested_at`, `step_index`, and `cancelled_by` (FR-054)
- [ ] T325 [US4] Scope cancel to demo runs in demonstration mode in `anchor/api/routers/runs.py` (FR-115)

#### P6.4 — Admission control

- [ ] T326 [US4] Implement the per-worker limit in `anchor/worker/admission/limiter.py` checked **before** claiming, from the worker's own in-process count — never from `workers.current_run_count`, which is telemetry (FR-004)
- [ ] T327 [US4] Report the global cap and current running count from `GET /api/health` in `anchor/api/routers/health.py`, and document that the API **reports** rather than rejects (FR-003)

#### P6.5 — Step timeout

- [ ] T328 [US4] Wrap every external call in `asyncio.timeout` at `step_timeout_ms` in `anchor/core/determinism/context.py` (FR-055)
- [ ] T329 [US4] Stop the renewer on step-timeout in `anchor/worker/renewer.py`, so a non-progressing worker **lapses its lease rather than holding the run** (FR-013)

#### P6.6 — Live configuration

- [ ] T330 [US4] Implement `runtime_config` reads at startup and a bounded re-poll in `anchor/core/config/live.py`
- [ ] T331 [US4] Implement the Redis "version changed" nudge in `anchor/core/config/live.py` as an **optimization only** — the bounded poll is the correctness path and works with Redis down
- [ ] T332 [US4] Apply new values only at a step boundary in `anchor/worker/loop.py`, so a lease shortening mid-step cannot fence the worker executing it (FR-062)
- [ ] T333 [US4] Implement `PATCH /api/config` in `anchor/api/routers/config.py` re-running the assertion and **rejecting the change, never the fleet** (FR-063)
- [ ] T334 [US4] Unmount `PATCH /api/config` in demonstration mode in `anchor/api/app.py`, and document that this is an **availability** restriction rather than a security boundary — conflating the two makes both harder to reason about (§31.2, FR-064)
- [ ] T335 [US4] Implement `GET /api/config` in `anchor/api/routers/config.py` returning current values, the active profile, and the version, available in both modes

#### P6.7 — Redis publish

- [ ] T336 [US4] Implement post-commit publish in `anchor/core/events/publish.py` to the single `anchor:events` firehose, **after commit** (D-50, FR-073)
- [ ] T337 [US4] Implement the `anchor:fleet` publish path in `anchor/worker/registry/heartbeat.py`
- [ ] T338 [US4] Document in `anchor/core/events/publish.py` why one firehose rather than per-run channels: per-run channels put subscribe and unsubscribe on the request path, which loses any event published between connect and subscribe — invisible unless someone notices a gap in `seq`

#### P6.8 — WebSocket channels

- [ ] T339 [US4] Implement the single always-on Redis subscription in `anchor/api/ws/subscriber.py`, demultiplexed by `run_id` in process (D-50)
- [ ] T340 [US4] Implement `WS /ws/runs/{run_id}` in `anchor/api/ws/runs.py` sending `hello` then one `snapshot`, so a client never renders an empty timeline while waiting
- [ ] T341 [US4] Implement per-event frames in `anchor/api/ws/runs.py` carrying the envelope from `contracts/websocket.md`, with `seq` **required** because it is what makes backfill exact rather than approximate
- [ ] T342 [US4] Implement the bounded per-client outbound queue in `anchor/api/ws/backpressure.py`, closing with `1013` and a `bye` frame carrying `last_sent_seq` on overflow (FR-074)
- [ ] T343 [US4] Implement the `lag` frame in `anchor/api/ws/runs.py` pushed on orphan transition — **the most important two seconds in the product, and it must not wait for a poll interval**
- [ ] T344 [US4] Implement `WS /ws/fleet` in `anchor/api/ws/fleet.py` sending `hello` then a `fleet` frame on every change, including the immediate advisory on a requested kill
- [ ] T345 [US4] Document in `anchor/api/ws/fleet.py` that the kill advisory is a **display optimization** and that `last_seen_at` in PostgreSQL remains the only thing anyone reasons about

#### P6.9 — Timeline derivation

- [ ] T346 [US4] Implement `GET /api/runs/{id}/timeline` in `anchor/api/serializers/timeline.py` deriving worker segments from `RUN_CLAIMED` events, with `ended_at IS NULL` identifying the current owner
- [ ] T347 [US4] Derive `handoff_count`, `recovery_seconds`, and `duplicate_side_effects` in `anchor/api/serializers/timeline.py`, with `recovery_seconds` **suppressed entirely when `handoff_count = 0`** rather than reported as zero
- [ ] T348 [US4] Derive the worker identity-hue slot in `anchor/api/serializers/timeline.py` from `workers.label` and claim order, so a hue survives a worker restart while the incarnation stays distinct in the log
- [ ] T349 [US4] Compute `duplicate_side_effects` **live from `tool_journal`, always**, in `anchor/api/serializers/timeline.py` — never cached, because the claim is only worth what its verification is (D-30)

#### P6.10 — Metrics rollup job

- [ ] T350 [US4] Write migration 004 in `ops/migrations/versions/004_metrics_rollup.py` creating `metrics_rollup` and `metrics_rollup_watermark` per data-model.md §9, with `CHECK (bucket_seconds IN (10, 300))`
- [ ] T351 [US4] Implement the watermarked rollup job in `anchor/api/serializers/rollup.py` reading strictly above the watermark, upserting buckets, and advancing the watermark **in the same transaction**
- [ ] T352 [US4] Implement both resolutions in `anchor/api/serializers/rollup.py` — 10 s for live views, 300 s for long windows
- [ ] T353 [US4] Implement the `REBUILD` path in `anchor/api/serializers/rollup.py` reconstructing every bucket from the log, and document that its existence is what proves the table is derived rather than authoritative
- [ ] T354 [US4] Run the job as a periodic task in `anchor/api/app.py`, **never as a trigger on the append path** (D-49)

#### P6.11 — Metrics and health

- [ ] T355 [US4] Implement `GET /api/metrics` in `anchor/api/routers/observability.py` serving display series from the rollup: run-state distribution, step throughput per worker and aggregate, recovery latency, replay overhead, fencing rate, uncertainty entries by policy, renewal latency, dead-letter volume (FR-071)
- [ ] T356 [US4] Serve the duplicate-effect count, stranded-run count, and every chaos figure **live from source** in `anchor/api/routers/observability.py`, with a comment naming the rollup as forbidden for these reads
- [ ] T357 [US4] Extend `GET /api/health` in `anchor/api/routers/health.py` with degradation, the schema revision, and the global cap with the current running count (FR-072)
- [ ] T358 [US4] Implement `GET /api/logs` in `anchor/api/routers/observability.py` searching `run_events` globally by type, worker, epoch, and time range, with `LEASE_RENEWED` **excluded by default** (FR-026)

#### P6.12 — Rate limiting

- [ ] T359 [US4] Implement the per-IP token bucket in `anchor/api/middleware.py` for submission and kill, plus the hourly demo cap (FR-006)
- [ ] T360 [US4] State the single-web-instance assumption in a comment at `anchor/api/middleware.py`, since in-process rate limiting is adequate **only** because there is exactly one web instance — and that is a fact about the deployment, not about the code (D-39)

#### P6.13 — Reset affordance

- [ ] T361 [US4] Implement `POST /api/runs/demo/reset` in `anchor/api/routers/runs.py` pruning completed demo runs and cascading their events
- [ ] T362 [US4] Make the reset **structurally unable** to touch chaos history in `anchor/api/routers/runs.py` — scoped by `is_demo` with no code path that reaches `chaos_events` or `chaos_reports` (FR-108)

#### Phase 6 completion

- [ ] T363 [P] [US4] Add `tests/failure/test_worker_registers_then_dies.py` coverage to the matrix index and confirm every §9 row has exactly one module
- [ ] T364 [P] [US4] Create `tests/failure/README.md` mapping each module to its §9 failure-matrix row, so a missing row is visible rather than inferred
- [ ] T365 [US4] Run `tests/failure` in full and confirm every module induces its failure deliberately and asserts the documented handling
- [ ] T366 [US4] Execute [V6](./quickstart.md#v6--load-and-repeated-failure-phase-6) and [V12](./quickstart.md#v12--configuration-cannot-be-set-to-a-self-fencing-state-phase-6-onward)
- [ ] T367 [US4] Execute [V13](./quickstart.md#v13--fleet-and-deployment-integrity-phases-0-5-6) in full — the six optimality-pass checks
- [ ] T368 [US4] Confirm each of the five optimality-pass tests (T295, T307, T310, T316, T297) was **seen to fail** against pre-pass behaviour before being trusted, and record that in the PR description
- [ ] T369 [US4] Record the crash behaviour of every await point and I/O boundary added in phase 6
- [ ] T370 [P] [US4] Implement `GET /api/agents` in `anchor/api/routers/registry.py` returning registered agents and their contracts (FR-120)
- [ ] T371 [P] [US4] Add the contract test for every phase-6 endpoint in `tests/contract/`, asserting each response validates against its `contracts/openapi.yaml` schema
- [ ] T372 [P] [US4] Add `tests/boundary/test_no_cross_run_write_paths.py` deriving the set of run-id-accepting mutating routes from `contracts/openapi.yaml` and matching it against an explicit allowlist — cancel, resolve, kill. A new mutating route fails this test until it is added deliberately. **This is the one assertion whose subject is code that does not exist** (FR-135)
- [ ] T373 [P] [US4] Add `tests/boundary/test_no_identity_gating.py` asserting no route reads a session, cookie, token, or user identifier, so every restriction remains a function of deployment mode alone (FR-114)
- [ ] T374 [P] [US4] Add `tests/unit/test_orphaned_is_derived.py` asserting `orphaned` appears in no column of any table and is computed at read time
- [ ] T375 [P] [US4] Add `tests/replay/test_completed_run_replays_identically.py` over a corpus of completed runs, comparing canonical hashes (FR-030)
- [ ] T376 [P] [US4] Add `tests/property/test_event_payload_roundtrip.py` asserting every payload model round-trips through `jsonb` without loss, including nested numerics
- [ ] T377 [US4] Verify `mypy --strict` and `ruff` pass clean across `anchor/` with no new per-file ignores
- [ ] T378 [US4] Confirm the backend surface matches `contracts/openapi.yaml` exactly — 23 paths, 25 operations — with a test that diffs the mounted routes against the document

**Exit gate**: [V6](./quickstart.md#v6--load-and-repeated-failure-phase-6) and
[V12](./quickstart.md#v12--configuration-cannot-be-set-to-a-self-fencing-state-phase-6-onward).

**Checkpoint**: US4 delivered. The backend is complete. **Console work is now unblocked.**

---

## Phase 7 — The operator console *(US5)*

**Goal**: make the runtime demonstrable and completely auditable.

**Invariants in play**: **none directly — and that is the point.** `web/` has no correctness
responsibilities and must never appear to have any. What it must not do is *misrepresent* them,
which is what P7.16 audits.

**Independent test**: render the run detail against recorded mock data for a run with two workers,
one handoff, five steps and zero duplicate side effects, and assert the handoff divider, the
per-worker hues, the ghosted replayed segments and the suppressed recovery figure all appear as
specified — **with no live backend**.

> **Order within the phase is not arbitrary**: tokens first, then the instrument layer, with the
> replayed-step encoding as the priority. Build what `contracts/component-contract.md` describes.
> **Do not substitute a generic timeline library, a Gantt chart, or a kanban layout** — a generic
> timeline renders this data as a project schedule, which communicates nothing about ownership
> handoff, and ownership handoff is the entire point.

### Tests for Phase 7 (MANDATORY) ⚠️

- [ ] T379 [P] [US5] Write the five-mock-state component tests in `web/components/run/__tests__/RunDetail.states.test.tsx` covering zero handoffs, three-plus handoffs, `needs_review`, 40 steps, and **currently orphaned**
- [ ] T380 [P] [US5] Write the orphaned-state test in `web/components/run/__tests__/RunDetail.orphaned.test.tsx` asserting that when **no segment has `ended_at === null`** the component renders the gap, the hairline and the countdown — **not an error and not an empty state**. This is the state the component is in during the most important two seconds of the demo, and it is the easiest to forget (FR-095)
- [ ] T381 [P] [US5] Write the snapshot suite in `web/components/run/__tests__/RunDetail.snapshot.test.tsx` with `now` **injected**, since relative timestamps make snapshots flap
- [ ] T382 [P] [US5] Write the no-bare-dots test in `web/components/primitives/__tests__/StatusPill.test.tsx` asserting every status renders icon **plus** label **plus** color, and that no status renders as a bare colored dot anywhere (FR-091)
- [ ] T383 [P] [US5] Write the strand-animation test in `web/components/run/__tests__/RunThread.animation.test.tsx` asserting the flow animation **stops at terminal state** — a strand that keeps flowing after the run finished is decoration, and it also lies
- [ ] T384 [P] [US5] Write the marker-shape test in `web/components/run/__tests__/RunThread.markers.test.tsx` asserting circle / square / ring, not three colored circles. The red/green pair is CVD ΔE 4.1 and **cannot be fixed with color** (FR-090)
- [ ] T385 [P] [US5] Write the strand-color test in `web/components/run/__tests__/RunThread.color.test.tsx` asserting **one gold along the whole length**, not a shade per worker — strand-gold-2 against worker-2 orange measures CVD ΔE 1.2, the same color to a colorblind reader (§24.8)
- [ ] T386 [P] [US5] Write the recovery-suppression test in `web/components/run/__tests__/RunDetail.footer.test.tsx` asserting `recovery_seconds` is **absent** at zero handoffs rather than rendered as `0.0s`, and that the duplicate count **leads** the footer line
- [ ] T387 [P] [US5] Write the kill-target test in `web/components/run/__tests__/RunDetail.kill.test.tsx` asserting the kill button targets the segment with `ended_at === null` and is disabled **with a stated reason** when the run is terminal
- [ ] T388 [P] [US5] Write the no-fetch test in `web/components/run/__tests__/RunDetail.pure.test.tsx` asserting neither component performs data fetching, opens a WebSocket, or calls the API — kill is raised to the parent
- [ ] T389 [P] [US5] Write the label-drop test in `web/components/run/__tests__/RunThread.labels.test.tsx` asserting a marker label that will not fit is **dropped, not clipped**
- [ ] T390 [P] [US5] Write the token-completeness test in `web/styles/__tests__/tokens.test.ts` asserting both dark and light sets define every token and that **no component file contains a hardcoded color literal** (FR-094)
- [ ] T391 [P] [US5] Write the chart-rules test in `web/components/primitives/__tests__/Chart.test.tsx` asserting exactly one hero figure per view, **no dual-axis chart**, a table view available for every chart, and a legend present whenever there are two or more series (FR-092)
- [ ] T392 [P] [US5] Write the staleness test in `web/hooks/__tests__/useRunStream.test.ts` asserting a dropped stream surfaces staleness on screen and that optimistic state is never rendered as confirmed (FR-095)
- [ ] T393 [P] [US5] Write the backfill test in `web/hooks/__tests__/useRunStream.backfill.test.ts` asserting reconnect uses `after_seq` rather than refetching the whole log, and that events with `seq <= snapshot.last_seq` are discarded
- [ ] T394 [P] [US5] Write the conditional-page test in `web/app/__tests__/navigation.test.tsx` asserting Scheduled, API keys and Webhooks are **absent** from the sidebar rather than present and empty (FR-087)
- [ ] T395 [P] [US5] Write the mode-gating test in `web/app/__tests__/deployment-mode.test.tsx` asserting the Environment page is absent in demonstration mode and the mode banner is present at all times

### Implementation for Phase 7

#### P7.1 — Design tokens

- [ ] T396 [US5] Define the dark token set in `web/styles/tokens.dark.css` as CSS custom properties: surfaces, ink, gridlines, the three identity hues (`#3987e5` → `#d95926` → `#199e70`), the status set, and the strand gold `#F6C453`
- [ ] T397 [US5] Define the light token set in `web/styles/tokens.light.css` with the measured light-mode values, including strand gold `#7A6300`
- [ ] T398 [US5] Document in `web/styles/README.md` that `serious` is **deliberately absent** because it failed measurement, so its absence reads as a decision rather than an omission
- [ ] T399 [US5] Configure Tailwind v4 in `web/tailwind.config.ts` to consume the custom properties, so utilities handle layout while signature colors stay tokenized

#### P7.2 — Typography and figures

- [ ] T400 [US5] Configure the two type families in `web/styles/typography.css` — one proportional, one monospace — with no third family
- [ ] T401 [US5] Apply proportional figures to hero and stat values and `tabular-nums` **only** in columns that must align vertically, in `web/styles/typography.css`
- [ ] T402 [US5] Add `web/components/primitives/__tests__/typography.test.tsx` asserting **text never wears a data color** — the active step's label is bold in primary ink with a trailing ellipsis, never amber

#### P7.3 — Shell and navigation

- [ ] T403 [US5] Implement the persistent sidebar in `web/components/shell/Sidebar.tsx` with the workspace slot, the **seven** groups, and the docs link pinned at the bottom (FR-084)
- [ ] T404 [US5] Implement the route group structure in `web/app/(console)/layout.tsx` for the fourteen built pages of the canonical inventory (FR-085)
- [ ] T405 [US5] Implement the deployment-mode banner in `web/components/shell/ModeBanner.tsx`, present at all times and reading from `GET /api/health`
- [ ] T406 [US5] Omit conditional pages entirely in `web/components/shell/Sidebar.tsx` — an empty settings page reads as an unfinished product; an absent one reads as a scoped one (FR-087)

#### P7.4 — API client and stream hooks

- [ ] T407 [US5] Implement the typed `fetch` client in `web/lib/api.ts` generated against `contracts/openapi.yaml`, with **no query library** (D-31)
- [ ] T408 [US5] Implement `useRunStream` in `web/hooks/useRunStream.ts` handling `hello`, `snapshot`, `event`, `lag`, and `bye`, applying events to the snapshot in `seq` order
- [ ] T409 [US5] Implement `useFleetStream` in `web/hooks/useFleetStream.ts` consuming `fleet` frames
- [ ] T410 [US5] Implement the polling fallback in `web/hooks/usePolling.ts` engaged when the socket is unavailable, with staleness surfaced rather than hidden
- [ ] T411 [US5] Implement reconnect with backoff and jitter plus `after_seq` backfill in `web/hooks/useRunStream.ts`
- [ ] T412 [US5] Document in `web/hooks/README.md` the client obligations from `contracts/websocket.md`: **never treat a frame as confirmation of a write** — the log is the record, and a frame is a notification that the log changed

#### P7.5 — `RunThread`

- [ ] T413 [US5] Implement `RunThread` in `web/components/run/RunThread.tsx` taking `segments`, `compact`, and `animate` as props, per `contracts/component-contract.md`
- [ ] T414 [US5] Implement the strand geometry in `web/components/run/RunThread.tsx` as inline SVG, viewBox ≈ `0 0 620 70`, **one continuous wavy path of smooth béziers — never straight segments**, stroke 2–2.5px and noticeably thinner than the bars
- [ ] T415 [US5] Implement the single-gold stroke in `web/components/run/RunThread.tsx`, with segment boundaries marked by the enlarged `handoff` marker rather than by a change of shade
- [ ] T416 [US5] Implement the three shape-coded markers in `web/components/run/ThreadMarkers.tsx` — muted circle for an ordinary step, **red square** for a real side effect, **green ring** for reconciled-safely — distinguishable under every form of color blindness, in grayscale, and in a compressed screen recording
- [ ] T417 [US5] Implement marker labels in `web/components/run/ThreadMarkers.tsx` at 11–12px, muted, never overlapping the strand, **dropped rather than clipped** when they will not fit. `sent once` is the label that states the guarantee in the reader's own language, next to the marker proving it
- [ ] T418 [US5] Implement the flow animation in `web/components/run/RunThread.tsx` via `stroke-dasharray`/`stroke-dashoffset` CSS keyframes at 2.5–3.5 s, linear and subtle — **the one permitted exception to the ban on ambient motion**, earned because the strand represents execution in progress
- [ ] T419 [US5] Stop the animation at terminal state in `web/components/run/RunThread.tsx`
- [ ] T420 [US5] Implement reduced-motion handling in `web/components/run/RunThread.tsx` freezing the dashoffset while colors, markers and labels all remain
- [ ] T421 [US5] Implement live path extension in `web/components/run/RunThread.tsx` so a new step event extends the path rather than snapping
- [ ] T422 [US5] Implement `compact` mode in `web/components/run/RunThread.tsx`, and document that it **cannot communicate which workers touched a run** — so it is not a substitute for the runs list's owning-worker column

#### P7.6 — `RunDetail`

- [ ] T423 [US5] Implement `RunDetail` in `web/components/run/RunDetail.tsx` taking `run`, `onKill`, and an injectable `now`, performing **no data fetching and no API call** (contracts/component-contract.md)
- [ ] T424 [US5] Implement the header in `web/components/run/RunDetail.tsx`: title, `started {n}s ago · {n} steps` subtitle, and a status pill carrying **text and, for `needs_review`/`failed`, an icon** — because `completed`-green against `failed`-red measures ΔE 4.1 for a deuteranopic reader
- [ ] T425 [US5] Implement the fixed-width monospace worker-id column in `web/components/run/RunDetail.tsx`, so bars align to a common left edge — **bars starting at different x positions cannot be compared by eye**. Ids read `worker-a#3`, label plus incarnation
- [ ] T426 [US5] Implement the per-worker bars in `web/components/run/WorkerBar.tsx` with the fill in the worker's identity hue and the unfilled portion a **neutral surface step — never a lighter tint of the worker's hue**, which would read as a magnitude ramp and imply the empty portion carried a value
- [ ] T427 [US5] Derive the identity hue from the worker's **label** in `web/lib/hues.ts`, so a worker that restarts keeps its color while remaining a distinct identity in the log
- [ ] T428 [US5] Implement the beyond-three fallback in `web/lib/hues.ts`: current owner slot 1, all prior owners muted, with identity carried by direct labels rather than by extending the validated three-hue set
- [ ] T429 [US5] Implement step labels in `web/components/run/RunDetail.tsx` aligned to where each step falls, with the active step bold in primary ink and a trailing ellipsis
- [ ] T430 [US5] Implement per-segment logs in `web/components/run/SegmentLog.tsx` at monospace 11px, muted for `info`, success for `success`, warning for `warning` — **per segment rather than one block**, so every line is attributed to the worker that wrote it
- [ ] T431 [US5] Implement the handoff divider in `web/components/run/HandoffDivider.tsx` as a dashed rule with a centered pill reading `{worker_id} lease expired` in danger colors. **This is the money moment. It must never be collapsed, hidden behind a toggle, or animated away**
- [ ] T432 [US5] Implement the footer in `web/components/run/RunDetail.tsx` with the duplicate count **leading** the line, handoff count, recovery seconds suppressed at zero handoffs, and the kill control in danger styling on the right
- [ ] T433 [US5] Trust `ended_at === null` as the current-owner signal in `web/components/run/RunDetail.tsx` rather than re-deriving it — that single field drives the kill target, the active-step styling, and which strand segment is still growing
- [ ] T434 [US5] Implement the raw event log panel in `web/components/run/RawEventLog.tsx` with type, worker, epoch and sequence visible

#### P7.7 — The five mock states

- [ ] T435 [P] [US5] Create the reference mock in `web/components/run/mocks/reference.ts` — 5 steps, 2 workers, 1 handoff, 0 duplicate side effects, 3.1 s recovery — which **must render meaningfully with no live backend**
- [ ] T436 [P] [US5] Create the zero-handoff mock in `web/components/run/mocks/zeroHandoffs.ts`
- [ ] T437 [P] [US5] Create the three-plus-handoff mock in `web/components/run/mocks/manyHandoffs.ts` exercising the beyond-three color rule
- [ ] T438 [P] [US5] Create the `needs_review` mock in `web/components/run/mocks/needsReview.ts`
- [ ] T439 [P] [US5] Create the 40-step mock in `web/components/run/mocks/fortySteps.ts` exercising label collision and the rail fallback
- [ ] T440 [P] [US5] Create the currently-orphaned mock in `web/components/run/mocks/orphaned.ts` where **no segment has `ended_at === null`**
- [ ] T441 [US5] Create the component preview route in `web/app/(dev)/preview/page.tsx` rendering all five states side by side, with no backend required

#### P7.8 — Timeline track

- [ ] T442 [US5] Implement the timeline track in `web/components/run/TimelineTrack.tsx` with segments sized by duration, a clickable floor for very short steps, and 2px surface gaps
- [ ] T443 [US5] Implement the notched leading edge for tool calls in `web/components/run/TimelineTrack.tsx`, distinguishing tool from model **by shape, not only by hue** (FR-090)
- [ ] T444 [US5] Implement the ghosted fill for replayed steps in `web/components/run/TimelineTrack.tsx`, legible **in grayscale** (FR-088)
- [ ] T445 [US5] Implement full-height fencing markers in `web/components/run/FencingMarker.tsx` showing **both** the stale and current epoch, never as a buried log line (FR-088)
- [ ] T446 [US5] Implement the worker-id rail fallback in `web/components/run/TimelineTrack.tsx` moving the label to a continuous rail rather than clipping it (FR-089)

#### P7.9 – P7.15 — The pages

- [ ] T447 [US5] Implement the All runs page in `web/app/(console)/runs/page.tsx` as a live table with the compact strand per row **and the owning-worker column retained**, status filters, and rows updating in place
- [ ] T448 [US5] Implement the Run detail page in `web/app/(console)/runs/[id]/page.tsx` fetching the timeline and owning the kill API call, passing data down as props
- [ ] T449 [US5] Implement the Needs review page in `web/app/(console)/needs-review/page.tsx` as **its own page, not a filter** — per §13.3, failures must not be reachable only by narrowing a list (FR-086)
- [ ] T450 [US5] Show the full log, the failing step highlighted, the ambiguous call, the declared policy and the resolution actions in `web/app/(console)/needs-review/[id]/page.tsx`
- [ ] T451 [US5] Implement the Fleet page in `web/app/(console)/workers/page.tsx` with a card per worker — id, uptime, current run count, last-heartbeat age, code version, kill control
- [ ] T452 [US5] Implement the Deployments page in `web/app/(console)/workers/deployments/page.tsx` grouping by `workers.code_version` **with no new schema**, answering "which build is actually running"
- [ ] T453 [US5] Implement the Tool registry page in `web/app/(console)/tools/page.tsx` showing declared safety categories, reconciler presence, conflict state and last used
- [ ] T454 [US5] Implement the Test run page in `web/app/(console)/tools/test-run/page.tsx` as a one-off submission form for **pre-registered agents only, in every deployment mode** — this page selects, it does not author
- [ ] T455 [US5] Implement the Metrics page in `web/app/(console)/metrics/page.tsx` rendering the §12 series in their specified forms
- [ ] T456 [US5] Implement the chart primitives in `web/components/primitives/Chart.tsx`: one hero figure per view, **no dual axes**, a table view for every chart, legends only at two-plus series (FR-092)
- [ ] T457 [US5] Implement the Logs page in `web/app/(console)/logs/page.tsx` with global search by type, worker, epoch and time, and `LEASE_RENEWED` excluded by default
- [ ] T458 [US5] Implement the Environment page in `web/app/(console)/settings/environment/page.tsx` with live-editable settings and the assertion's rejection surfaced as a useful message naming the relationship and both values
- [ ] T459 [US5] Make the Environment page **absent in demonstration mode** in `web/app/(console)/settings/environment/page.tsx`, not present-and-disabled (FR-064)
- [ ] T460 [US5] Implement the Dashboard in `web/app/(console)/page.tsx` with active runs, live worker count, a steps/sec sparkline inside a stat tile, and the duplicate counter **reading zero explicitly** (FR-096)
- [ ] T461 [US5] Implement the stat tile, hero figure and status pill primitives in `web/components/primitives/`

#### P7.16 — States and audits

- [ ] T462 [US5] Implement loading, empty and error states for **every** live component, with a checklist in `web/components/README.md` (Principle VIII)
- [ ] T463 [US5] Implement the database-unreachable screen in `web/app/(console)/error.tsx` stating that **execution is halted deliberately** — the failure is a designed behaviour and the screen says so rather than reading as a crash
- [ ] T464 [US5] Perform the **grayscale audit** manually: set the display to grayscale and confirm replayed segments remain distinguishable from executed ones (SC-010)
- [ ] T465 [US5] Perform the **reduced-motion audit** manually: enable `prefers-reduced-motion` and confirm no information is lost — the explainer falls back to a labelled static frame, the pulse becomes a static state color, and the orphaned gap keeps its countdown as plain changing text (SC-011, FR-093)
- [ ] T466 [US5] Perform the **40-step layout pass** manually across every view, checking for label collisions, overflow, and a timeline that still reads
- [ ] T467 [US5] Confirm no bare colored dots anywhere by inspection, in addition to the automated assertion
- [ ] T468 [US5] Apply sentence case throughout and confirm the interface uses **the same vocabulary as the logs and the documentation** — run, step, event, epoch, lease, fencing, zombie worker, idempotency key, uncertainty window, replay, determinism boundary, dead letter (FR-097)
- [ ] T469 [US5] Confirm monospace is used **only where alignment carries meaning** — run ids, worker ids, epochs, keys, timestamps, log lines — and not for the prose subtitle or the step labels
- [ ] T470 [US5] Confirm no decorative gradients, shadows or glow appear anywhere, the strand's flow being the single intentional exception
- [ ] T471 [US5] Run `pnpm --dir web lint` and `pnpm --dir web test` clean, with TypeScript strict passing
- [ ] T472 [US5] Execute [V7](./quickstart.md#v7--the-console-tells-the-truth-phase-7) including all five manual checks
- [ ] T473 [US5] Record the three manual audits' results in the PR description — **they cannot be automated and must not be skipped**

**Exit gate**: [V7](./quickstart.md#v7--the-console-tells-the-truth-phase-7), including the three
manual audits.

**Checkpoint**: US5 delivered. **The landing surface is still blocked** — its figures do not exist
until phase 8 produces them.

---

## Phase 8 — The chaos harness, the proof, and only then the landing surface *(US6, US7)*

**Goal**: convert the guarantee from a claim into a measured, accumulating, regenerating number — and
then present it.

**Invariants in play**: all eight, **as subjects of the assertions rather than as implementation**.

**Independent test (US6)**: run the harness for a bounded duration against a local fleet, assert all
five invariant checks pass, that a report row is written with the measured distributions, and that
the reported numbers are read back by the metrics endpoint rather than hardcoded anywhere.

**Independent test (US7)**: in a fresh private window against the deployed instance, complete the
four-step guided sequence without scrolling past the first viewport, without an account, and without
navigating away — then confirm from the fleet page that the killed worker really was killed and has
respawned.

> **Order within the phase is normative**: the harness and its console come first, the landing
> surface last. The evidence badge cannot be honestly built before the evidence exists, and a
> landing page written first would contain placeholder figures — which have a way of shipping.

### Tests for Phase 8 (MANDATORY) ⚠️

- [ ] T474 [P] [US6] Write the invariant-1 test in `tests/unit/test_invariant_no_duplicate_effects.py` asserting the SQL assertion finds a deliberately planted duplicate result and reports zero on a clean corpus
- [ ] T475 [P] [US6] Write the invariant-2 test in `tests/unit/test_invariant_log_monotonic.py` asserting the assertion detects a planted gap and a planted duplicate `seq`
- [ ] T476 [P] [US6] Write the invariant-3 test in `tests/unit/test_invariant_single_writer_per_epoch.py` asserting the assertion detects a planted `(run_id, epoch)` carrying two worker ids
- [ ] T477 [P] [US6] Write the invariant-4 test in `tests/unit/test_invariant_terminal_reachability.py` asserting the assertion detects a run left non-terminal past the bound
- [ ] T478 [P] [US6] Write the invariant-5 test in `tests/unit/test_invariant_replay_determinism.py` asserting the assertion detects a log whose replayed final state differs from the recorded one
- [ ] T479 [P] [US6] Write the report-immutability test in `tests/boundary/test_chaos_reports_immutable.py` asserting `UPDATE` and `DELETE` on `chaos_reports` and `chaos_events` raise `AN003` **in both deployment modes** (FR-083)
- [ ] T480 [P] [US6] Write the recovery-measurement test in `tests/unit/test_recovery_measured_from_chaos_event.py` asserting recovery latency is measured from the `worker_kill` row's `created_at` to the reclaiming `RUN_CLAIMED.created_at`
- [ ] T481 [P] [US6] Write the profile-reported test in `tests/contract/test_report_carries_profile_and_lease.py` asserting the config profile and lease duration are stored on the report and returned with every figure — **a recovery figure without them is not a measurement** (FR-061)
- [ ] T482 [P] [US6] Write the violations-explicit test in `tests/unit/test_violations_empty_not_null.py` asserting `violations` is returned as `[]` rather than `null` when clean
- [ ] T483 [P] [US6] Write the abandoned-detection test in `tests/failure/test_chaos_run_abandoned_on_restart.py` asserting an API restart mid-harness marks the chaos run `abandoned` rather than leaving it `running` with a stale heartbeat
- [ ] T484 [P] [US6] Write the harness-through-public-API test in `tests/boundary/test_harness_uses_public_api.py` asserting the harness drives the system through HTTP, so the console button and the CI run share one implementation (D-36)
- [ ] T485 [P] [US6] Write the bounded-parameters test in `tests/boundary/test_chaos_bounded_in_demo_mode.py` asserting duration and worker count are capped in demonstration mode **while the capability remains available** — cap the parameters, not the capability (FR-116)
- [ ] T486 [P] [US7] Write the evidence-badge test in `tests/contract/test_evidence_badge_absent_when_no_report.py` asserting `GET /api/chaos/latest` returns 404 and the badge is **absent rather than a placeholder** (FR-104, SC-017)
- [ ] T487 [P] [US7] Write the no-hardcoded-figures test in `tests/boundary/test_no_hardcoded_figures.py` scanning `web/` for numeric literals in evidence positions and failing on any figure not read from an endpoint
- [ ] T488 [P] [US7] Write the guided-demo test in `web/app/__tests__/guided-demo.test.tsx` asserting one click submits a real run with no form, no options and no modal, and that the kill control calls the **real** endpoint and says so (FR-100, FR-101)
- [ ] T489 [P] [US7] Write the self-heal test in `tests/failure/test_fleet_self_heals_after_full_kill.py` asserting a visitor killing every worker finds the fleet at full complement within seconds (SC-016)
- [ ] T490 [P] [US7] Write the outbound-exclusions test in `web/app/__tests__/outbound-surface.test.tsx` asserting no newsletter signup, social button, notification prompt, feature grid, testimonial, pricing element, or analytics modal is present (FR-109)

### Implementation for Phase 8

#### P8.1 — Migration 005

- [ ] T491 [US6] Write migration 005 in `ops/migrations/versions/005_chaos.py` creating `chaos_runs`, `chaos_reports` and `chaos_events` per data-model.md §6–§8, with every `CHECK` including `(recovery_ms_p50 IS NULL) = (kills_injected = 0)`. **Numbering note**: plan.md labels this "Migration 003"; sequential numbering makes it 005 (see T163)
- [ ] T492 [US6] Write the `chaos_reports_immutable` and `chaos_events_immutable` triggers in `ops/migrations/versions/005_chaos.py` raising `AN003` on `UPDATE` and `DELETE`, **active in both deployment modes** — it is evidence, and immutability is a database property
- [ ] T493 [US6] Create the chaos indexes in `ops/migrations/versions/005_chaos.py` — `(chaos_run_id, created_at)`, `(type, created_at DESC)`, `(started_at DESC)`, and `chaos_reports (created_at DESC)` for the landing badge and the README refresher

#### P8.2 — Harness core

- [ ] T494 [US6] Implement the harness orchestrator in `anchor/chaos/harness.py` launching N workers and submitting M runs, **driving everything through the public API** (D-36, FR-075)
- [ ] T495 [US6] Implement the deliberate workload mix in `anchor/chaos/harness.py` — step counts, tool types spanning all three safety categories, and durations
- [ ] T496 [US6] Implement sustained operation in `anchor/chaos/harness.py` running continuously for a configured duration rather than a single pass, with heartbeat writes to `chaos_runs.heartbeat_at` (FR-080)
- [ ] T497 [US6] Implement `abandoned` detection in `anchor/chaos/harness.py` marking a `running` chaos row with a stale heartbeat as `abandoned` at API startup, and displaying it as such
- [ ] T498 [US6] Document in `anchor/chaos/harness.py` that **the harness is deliberately not durable**: making it durable would mean running it on Anchor, which is circular and compromises the independence of the proof. The harness is the rig, not the system under test

#### P8.3 — Injections

- [ ] T499 [US6] Implement random worker kills in `anchor/chaos/injections/kill.py` at a configurable rate, at random points in a run (FR-076)
- [ ] T500 [US6] Implement latency injection in `anchor/chaos/injections/latency.py` (FR-077)
- [ ] T501 [US6] Implement stall injection in `anchor/chaos/injections/stall.py` aimed specifically at the fencing path, reusing P4.4's mechanism (FR-077)
- [ ] T502 [US6] Implement tool-failure injection in `anchor/chaos/injections/tool_failure.py` at a configurable rate, exercising retry and dead-lettering (FR-078)
- [ ] T503 [US6] Implement uncertainty-window crash injection in `anchor/chaos/injections/uncertainty.py` **exercising every declared policy**, so all three resolution paths are measured rather than assumed (FR-079)
- [ ] T504 [US6] Record every injection as a `chaos_events` row in `anchor/chaos/injections/recorder.py` with type, target worker, timestamp and affected run ids — **this table is one of the two inputs to the published recovery number**, not documentation of the experiment (FR-081)

#### P8.4 — The five invariants

- [ ] T505 [US6] Implement invariant 1 in `anchor/chaos/invariants.py` as a SQL-backed assertion: **at most one recorded result per idempotency key**
- [ ] T506 [US6] Implement invariant 2 in `anchor/chaos/invariants.py`: `seq` strictly increasing within every run, with no duplicates and no gaps
- [ ] T507 [US6] Implement invariant 3 in `anchor/chaos/invariants.py`: no `(run_id, epoch)` carries events from two worker ids
- [ ] T508 [US6] Implement invariant 4 in `anchor/chaos/invariants.py`: every submitted run reaches a terminal state within the bound — nothing stranded
- [ ] T509 [US6] Implement invariant 5 in `anchor/chaos/invariants.py`: every completed log replays to an identical final state, compared by canonical hash
- [ ] T510 [US6] Implement continuous assertion in `anchor/chaos/invariants.py` running the five during the harness run rather than only at the end, so a violation is caught near the injection that caused it (FR-082)
- [ ] T511 [US6] Record each violation in `anchor/chaos/invariants.py` with the run, key, epoch or `seq` that failed, so a failure is actionable rather than merely reported

#### P8.5 — Report computation

- [ ] T512 [US6] Implement report computation in `anchor/chaos/report.py` producing duplicate and stranded counts **computed live from `tool_journal` and `run_events`**, never from the rollup
- [ ] T513 [US6] Compute recovery percentiles in `anchor/chaos/report.py` — p50, p95, p99, max — from each kill's `chaos_events.created_at` to the reclaiming `RUN_CLAIMED`
- [ ] T514 [US6] Compute replay overhead in `anchor/chaos/report.py` as mean steps replayed per resumption and mean replay latency
- [ ] T515 [US6] Compute throughput, fencing events, uncertainty entries by policy, and dead-letter volume in `anchor/chaos/report.py`
- [ ] T516 [US6] Write the report with the **profile and lease in force** in `anchor/chaos/report.py`, captured at launch (FR-082)

#### P8.6 — Chaos API

- [ ] T517 [US6] Implement `POST /api/chaos/start` in `anchor/api/routers/chaos.py`, **bounded per deployment mode** (FR-116)
- [ ] T518 [US6] Implement `GET /api/chaos` in `anchor/api/routers/chaos.py` listing every past run, newest first
- [ ] T519 [US6] Implement `GET /api/chaos/latest` in `anchor/api/routers/chaos.py` returning 404 when no report exists, so the badge can be absent rather than stale
- [ ] T520 [US6] Implement `GET /api/chaos/{id}/report` in `anchor/api/routers/chaos.py` returning `violations` as `[]` explicitly, never `null`

#### P8.7 — Chaos console and history

- [ ] T521 [US6] Implement the Chaos console page in `web/app/(console)/chaos/page.tsx` configuring worker count, kill rate, latency injection, failure injection and duration, with the launch control
- [ ] T522 [US6] Implement the live invariant panel in `web/components/chaos/InvariantPanel.tsx` showing duplicate executions, stranded runs, recovery distribution and replay overhead as they accumulate
- [ ] T523 [US6] Implement the Chaos history page in `web/app/(console)/chaos/history/page.tsx` with every past run and its final invariant report, retained permanently
- [ ] T524 [US6] Display the profile and lease alongside every recovery figure in `web/components/chaos/ReportCard.tsx` (FR-082)
- [ ] T525 [US6] Note in `web/app/(console)/chaos/page.tsx` that **this page is the project** — it is what you show first

#### P8.8 — CI and schedule

- [ ] T526 [US6] Add a bounded chaos smoke to `.github/workflows/ci.yml` on every push (D-35)
- [ ] T527 [US6] Add the sustained scheduled chaos job in `ops/deploy/scheduled-chaos.yml` running against the deployed instance
- [ ] T528 [US6] Implement the README figure refresher in `ops/deploy/refresh_readme_figures.py` reading the latest report and rewriting the README's figures — **generated, never hand-typed** (SC-017)

#### P8.9 — Landing bands 1–5

- [ ] T529 [US7] Implement band 1 in `web/app/(landing)/page.tsx`: the claim in two sentences with a live status strip reading worker count, run count and duplicate-effect count from the real health and metrics endpoints, reporting degradation honestly (FR-098)
- [ ] T530 [US7] Implement the mechanism explainer in `web/components/landing/Explainer.tsx` as hand-built SVG/CSS **under a few kilobytes**, with no animation library and no video file (FR-099)
- [ ] T531 [US7] Implement the explainer's reduced-motion fallback in `web/components/landing/Explainer.tsx` as a **labelled static frame** (FR-093, FR-099)
- [ ] T532 [US7] Implement the evidence band in `web/components/landing/EvidenceBand.tsx` whose hero is the harness-generated zero with its timestamp (FR-104)
- [ ] T533 [US7] Implement the architecture band in `web/components/landing/ArchitectureBand.tsx` stating the **prior art by name** — Temporal and Restate, unprompted — the effectively-once framing, and the single-writer ceiling (FR-105)
- [ ] T534 [US7] State the positioning sentence verbatim in `web/components/landing/ArchitectureBand.tsx`: *Anchor is a durable execution engine in the Temporal lineage, specialized for agent workloads and built to be demonstrated rather than deployed at scale.* Getting there first converts a potential gap in your awareness into evidence of it

#### P8.10 — The guided demo

- [ ] T535 [US7] Implement the four-step guided demo in `web/components/landing/GuidedDemo.tsx` — submit → watch → kill → resume — **inline, with no navigation, no account and no configuration** (FR-100)
- [ ] T536 [US7] Call the real kill endpoint from `web/components/landing/GuidedDemo.tsx` and **label it as real**, not a simulation (FR-101)
- [ ] T537 [US7] Narrate the orphaned stall in `web/components/landing/GuidedDemo.tsx` with a lease countdown labelled `orphaned — lease expiring`, driven by the `lag` frame rather than by a poll (FR-102)
- [ ] T538 [US7] Show the new worker id and the replayed steps distinctly in `web/components/landing/GuidedDemo.tsx`, with **one sentence stating in words that their tool calls did not run a second time** (FR-103)
- [ ] T539 [US7] State on the page that model calls are stubbed in `web/components/landing/GuidedDemo.tsx` — the log says so, so the page says so too (FR-036)

#### P8.11 — Presets and self-sufficiency

- [ ] T540 [US7] Implement the three one-click presets in `web/components/landing/Presets.tsx` — short run, long run, and the unsafe-tool run that crashes inside the uncertainty window (FR-106)
- [ ] T541 [US7] Verify automatic respawn end to end and surface the fleet's self-healing on the landing page (FR-069)
- [ ] T542 [US7] Apply submission and kill rate limits to the landing paths, **rate-limited only so the fleet view stays readable** — killing workers is not a vulnerability here, it is the demonstration
- [ ] T543 [US7] Wire the reset affordance into the landing surface in `web/components/landing/Reset.tsx`, structurally unable to touch chaos history (FR-108)

#### P8.12 — Outbound surface

- [ ] T544 [US7] Implement the header in `web/components/shell/Header.tsx` with wordmark, **GitHub** — the single most important outbound link on the site — and Console
- [ ] T545 [US7] Implement the live evidence badge in `web/components/landing/EvidenceBadge.tsx` reading the current headline result from the most recent report, **never hardcoded**, and **absent** when no chaos run has completed (FR-104, SC-017)
- [ ] T546 [US7] Implement the one-line attribution strip in `web/components/landing/Attribution.tsx` — a project page that spends more vertical space on its author than on its evidence inverts the thing it is trying to demonstrate
- [ ] T547 [US7] Implement the footer in `web/components/shell/Footer.tsx` with the repository link repeated, the license, the self-hosting statement verbatim, and the design-document link if it was written. **`TODO(LICENSE)` — the link is omitted rather than faked until a license is chosen** (FR-109)
- [ ] T548 [US7] Exclude every §32.5 item in `web/components/shell/Footer.tsx` and the landing layout: newsletter signups, social buttons, **notification prompts**, feature grids, testimonials, pricing, and **any analytics modal or cookie banner beyond the legal minimum** (FR-109)
- [ ] T549 [US7] Execute [V8](./quickstart.md#v8--measured-proof-phase-8) — a full harness run with all five invariants true, `duplicate_effect_count: 0`, `stranded_run_count: 0`, and a recovery distribution inside the derived bound
- [ ] T550 [US7] Execute [V9](./quickstart.md#v9--the-cold-reviewer-path-phase-8-after-the-chaos-console) against the deployed instance in a fresh private window, **timeboxed to sixty seconds**
- [ ] T551 [US6] Confirm chaos history survives the reset affordance and that a direct `UPDATE` on `chaos_reports` in `psql` raises `AN003`

**Exit gate**: [V8](./quickstart.md#v8--measured-proof-phase-8) and
[V9](./quickstart.md#v9--the-cold-reviewer-path-phase-8-after-the-chaos-console).

**Checkpoint**: 🎯 **US6 and US7 delivered. The definition of the project is complete at the end of
this phase.** Everything after it is optional.

---

## Phase 9 — The authoring surface *(stretch, optional)* *(US9)*

**Goal**: make the agent contract legible without a clone.

**Begins only after phase 8 is complete.** Order within the phase: **validator, then editor, then
generator.** The validator is the part with engineering content; the editor is a dependency someone
else wrote; the generator is a convenience. **If only half is built, the half worth having is the
validator.**

**Independent test**: on a public-mode instance, submit a draft calling `datetime.now()` and assert
the validator rejects it naming the step-context replacement; then assert the register endpoint
returns **404 rather than 401 or 403**.

> **This phase proves nothing the runtime does not already prove.** It is strictly additive, and it
> must not consume hours that phases 4 and 5 need. If it is never built, nothing in the developer
> path becomes untrue — the quickstart works entirely from the command line, which is how developers
> integrate infrastructure anyway.

### Tests for Phase 9 (MANDATORY) ⚠️

- [ ] T552 [P] [US9] Write the determinism-rejection test in `tests/contract/test_validator_determinism.py` asserting a draft referencing `datetime`, `time`, `random` or `uuid` is rejected **with the line number and the step-context call that replaces it** (FR-123, FR-124)
- [ ] T553 [P] [US9] Write the return-shape test in `tests/contract/test_validator_return_shape.py` asserting anything not a `ToolCall`, `ModelCall` or `Done` is rejected with its own specific message
- [ ] T554 [P] [US9] Write the module-state test in `tests/contract/test_validator_module_state.py` asserting globals mutated across invocations are rejected — state held outside `ctx` does not survive a handoff and is the most likely authoring mistake
- [ ] T555 [P] [US9] Write the unregistered-tool test in `tests/contract/test_validator_unregistered_tool.py` asserting a `ToolCall` naming a tool absent from the registry fails **in the editor rather than at step 3 of a live run**
- [ ] T556 [P] [US9] Write the missing-safety test in `tests/contract/test_validator_missing_safety.py` asserting a registered tool with no declared category is rejected
- [ ] T557 [P] [US9] Write the self-recursion test in `tests/contract/test_validator_self_recursion.py` asserting a step that can only return itself is rejected, catching the trivial infinite-run case
- [ ] T558 [P] [US9] Write the generator-routing test in `tests/contract/test_generator_routed_through_validator.py` asserting a generated draft arrives **with validation already run and any violations already marked** (FR-125)
- [ ] T559 [P] [US9] Write the honest-degradation test in `tests/contract/test_generator_degrades_honestly.py` asserting that with no provider key the editor and validator work and the generate control is disabled **with a plain statement of why** (FR-126)
- [ ] T560 [P] [US9] Write the route-not-mounted test in `tests/boundary/test_register_route_not_mounted.py` asserting `POST /api/authoring/register` returns **404, not 401 or 403** — the response must not imply that a credential would help (FR-112, SC-015)
- [ ] T561 [P] [US9] Write the import-path test in `tests/boundary/test_no_import_path_to_registry_mutation.py` asserting that with `ANCHOR_AUTHORING_EXECUTE` unset, no import path in the API package reaches registry-mutation code (FR-113)
- [ ] T562 [P] [US9] Write the both-modes test in `tests/boundary/test_validate_and_generate_both_modes.py` asserting `/api/authoring/validate` and `/api/authoring/generate` succeed in **both** modes
- [ ] T563 [P] [US9] Write the no-draft-persistence test in `tests/boundary/test_no_server_side_draft_state.py` asserting no table, cache key, or filesystem path holds a draft after the response is written (FR-136, §27.5)
- [ ] T564 [P] [US9] Write the stated-ceiling test in `tests/contract/test_validation_report_carries_unchecked.py` asserting every `ValidationReport` — including a clean one — carries the `unchecked` array with the four pre-registration checklist items (FR-134)

### Implementation for Phase 9

#### P9.1 — The validator

- [ ] T565 [US9] Implement the validator entrypoint in `anchor/api/authoring/validator.py` running six static checks over a draft
- [ ] T566 [US9] Implement the determinism-imports check in `anchor/api/authoring/checks/determinism.py` **reusing P2.3's AST checker** — the test that runs at commit time here runs interactively, against a draft, before the code has ever executed
- [ ] T567 [US9] Implement the return-shape check in `anchor/api/authoring/checks/return_shape.py`
- [ ] T568 [US9] Implement the module-level mutable state check in `anchor/api/authoring/checks/module_state.py`
- [ ] T569 [US9] Implement the unregistered-tool check in `anchor/api/authoring/checks/tool_names.py` reading the live registry
- [ ] T570 [US9] Implement the missing-safety-declaration check in `anchor/api/authoring/checks/safety.py`
- [ ] T571 [US9] Implement the unbounded-self-recursion check in `anchor/api/authoring/checks/recursion.py`, with a comment noting the attempt cap of phase 6 catches the rest
- [ ] T572 [US9] Implement `ValidationReport` in `anchor/api/authoring/models.py` matching `contracts/openapi.yaml`, carrying `valid`, `findings` and the required `unchecked` array

#### P9.2 — Teaching error messages

- [ ] T573 [US9] Write teaching messages for all six checks in `anchor/api/authoring/messages.py`, each naming the line **and the replacement** — *"line 14 calls `datetime.now()`. Agent code must use `ctx.now()` so the value is journaled and replay returns the same timestamp."* **An error that teaches the invariant is worth more than the feature that produced it** (FR-124)

#### P9.3 — `validate` endpoint and editor

- [ ] T574 [US9] Implement `POST /api/authoring/validate` in `anchor/api/routers/authoring.py`, available in **both** modes, static analysis only, nothing executed
- [ ] T575 [US9] Ensure no draft is persisted server-side in `anchor/api/routers/authoring.py` — the source is read, analyzed, and discarded (FR-136)
- [ ] T576 [US9] Implement the Authoring page in `web/app/(console)/tools/authoring/page.tsx` with the editor preloaded with the agent contract and the three demo agents as worked examples
- [ ] T577 [US9] Run validation on keystroke pause and on submission in `web/app/(console)/tools/authoring/page.tsx`
- [ ] T578 [US9] State the deployment mode in the page header **at all times** in `web/app/(console)/tools/authoring/page.tsx` (FR-127)

#### P9.4 — The generator

- [ ] T579 [US9] Implement `POST /api/authoring/generate` in `anchor/api/routers/authoring.py` seeded with the contract, the one taught constraint, the tool registry, and the three demo agents as worked examples
- [ ] T580 [US9] Route generator output **through the validator before display** in `anchor/api/routers/authoring.py` — the generator does not get to produce something the validator would reject and have that pass without comment (FR-125)
- [ ] T581 [US9] Ensure the generator **never registers and never executes** in `anchor/api/routers/authoring.py`; output lands in the editor and registration is always a separate, explicit human action
- [ ] T582 [US9] Implement honest degradation in `anchor/api/routers/authoring.py` returning 503 with a plain statement when no provider key is configured, while the editor and validator keep working (FR-126)

#### P9.5 — `register`, local only

- [ ] T583 [US9] Mount `POST /api/authoring/register` in `anchor/api/app.py` **only** when `ANCHOR_AUTHORING_EXECUTE=true`, so demonstration mode returns 404 because the route does not exist (FR-112)
- [ ] T584 [US9] Document in `anchor/api/app.py` why this is an unmounted route rather than a permission check: **an unmounted route survives a middleware ordering bug, a session-handling error, and a credential-stuffing attempt, because there is nothing behind it** (§31.2)
- [ ] T585 [US9] Implement the registration handler in `anchor/api/authoring/register.py` reachable only from the gated mount, re-running full validation before loading into the live registry

#### P9.6 — Boundary tests

- [ ] T586 [US9] Run the five §31.3 assertions in full and confirm each passes in both modes as specified
- [ ] T587 [US9] Execute [V11](./quickstart.md#v11--the-deployment-boundary-every-phase-that-adds-a-route) end to end

#### P9.7 — The stated ceiling

- [ ] T588 [US9] Populate the `unchecked` array on **every** `ValidationReport` in `anchor/api/authoring/validator.py` with the four pre-registration checklist items from `contracts/agent-contract.md`, so the ceiling travels with the response rather than depending on a console that might render `valid: true` alone (FR-134)
- [ ] T589 [US9] Render the ceiling adjacent to the results panel in `web/components/authoring/ValidationPanel.tsx` as the **stated next step** — *these six mechanical checks passed; these four judgements are yours* — never as a disclaimer and never as "all checks passed" standing in for "this agent is correct" (D-59)
- [ ] T590 [US9] State on the generator control in `web/components/authoring/GenerateControl.tsx` that generation happens at **authoring time, on text a human then reviews**, which is why it does not contradict the rule forbidding generated behaviour at runtime (FR-137)
- [ ] T591 [US9] Confirm the validator visibly rejects a deliberately wrong draft **on the public instance**
- [ ] T592 [US9] Confirm no page in this phase offers saved drafts, per-user workspaces, or any server-side draft state — §21.7 stands (FR-136)

**Exit gate**: [V11](./quickstart.md#v11--the-deployment-boundary-every-phase-that-adds-a-route),
plus a validator that visibly rejects a deliberately wrong draft on the public instance **and a
results panel that states what it did not check.**

**Checkpoint**: US9 delivered.

---

## Cross-cutting — Documentation, narrative, and the developer path *(US8)*

**Purpose**: the surfaces around the claim. Not a phase, because these span phases — but each has a
gate, and the third-party quickstart run gates the project being called done.

> **Note**: "Code cleanup and refactoring" is deliberately absent. Per Principle IX, refactoring
> outside the task scope is not a task — anything worth fixing is raised as a separate item.

- [ ] T593 [US8] Write the README's first paragraph in `README.md` stating that **Anchor is self-hosted and is not a service**, and that the deployed instance is a demonstration instance rather than a distribution channel (FR-122)
- [ ] T594 [US8] Add the screen recording to `README.md` as the opening artifact
- [ ] T595 [US8] Add the generated chaos figures to `README.md`, refreshed automatically by the T528 job and **never hand-typed**
- [ ] T596 [US8] Add the architecture diagram to `README.md`
- [ ] T597 [US8] Add the **eight-step quickstart** to `README.md` immediately after the architecture diagram, because a reviewer convinced by the numbers next wants to know what using it costs them (§26.3)
- [ ] T598 [US8] Add the professor-outreach agent **verbatim** to `README.md` immediately after the one taught constraint, and point at `anchor/runtime/agents/demo_long.py` as the canonical already-done-filter example. It is the only place the constraint is shown to **buy** something rather than merely to cost something (FR-138)
- [ ] T599 [US8] State the one taught constraint in the first paragraph of the authoring documentation in `docs/authoring.md`: *the agent function returns one action and then returns control; it does not loop, and it does not hold state in variables across steps* (FR-121)
- [ ] T600 [US8] Add the glossary to `README.md` — run · step · event · epoch · lease · fencing · zombie worker · idempotency key · uncertainty window · replay · determinism boundary · dead letter
- [ ] T601 [US8] Add the honest-weaknesses section to `README.md`, including the single-writer ceiling and the fact that the chaos harness is not itself durable
- [ ] T602 [P] [US8] Write the design document in `docs/design.md` covering tradeoffs, rejected alternatives and known limitations — **the artifact a senior reviewer is most likely to actually read**
- [ ] T603 [P] [US8] State the **framework-adapter shape** in `docs/design.md`: a graph-based framework is driven one node per `decide_next_step` invocation, with its state object rehydrated from `ctx` on each call, rather than by calling the framework's own end-to-end execution method. **Say the shape, do not build it** (FR-139, §26.5)
- [ ] T604 [P] [US8] Write the future-work section of `docs/design.md` covering divergence-aware replay, cost-aware recovery, and a generic reconciliation protocol
- [ ] T605 [P] [US8] Record **semantic compensation as refused rather than deferred** in `docs/design.md` — generating compensating actions with a model at runtime contradicts the governing rule directly, unlike §27.4's authoring-time generation, which does not (§28.4)
- [ ] T606 [P] [US8] Record the branching cut in `docs/design.md` as **load-bearing**: a fork produces two histories sharing a prefix, and `I2` and `I3` both assume one linear history per run, so reintroducing it reopens the two invariants that constitute the proof (§28.3)
- [ ] T607 [P] [US8] Document the agent contract in `docs/authoring.md` from `contracts/agent-contract.md`, including the full `StepContext` surface and the crash behaviour of each call
- [ ] T608 [P] [US8] Document the tool contract in `docs/tools.md` from `contracts/tool-contract.md`, with the three categories and their uncertainty-window behaviour
- [ ] T609 [P] [US8] Publish the four-item pre-registration checklist in `docs/authoring.md`, and state which of the four the validator **cannot** check (FR-134)
- [ ] T610 [US8] Enforce glossary discipline at review: the same words in the code, the log, the interface and the docs, from phase 1 onward
- [ ] T611 [US8] Prepare the four cold-defence answers in `docs/interview-notes.md` — PostgreSQL over a broker; Redis excluded from ownership; step-level checkpointing; database-clock expiry
- [ ] T612 [US8] Prepare the single-writer-ceiling answer in `docs/interview-notes.md`, including the sharding remediation and **D-52's constraint on how it may ever be done**
- [ ] T613 [US8] Prepare the preempted-weaknesses list in `docs/interview-notes.md`, so the honest limitations are stated before they are found
- [ ] T614 [US8] **Have someone other than the author follow the eight-step quickstart from a clean clone**, on a machine that has never run the project. Every step works as written, or the step is corrected (SC-012, §29.2)
- [ ] T615 [US8] Execute [V10](./quickstart.md#v10--the-developer-path-documentation-gate) in full, including the three additional checks on the README example, the adapter shape, and the checklist
- [ ] T616 [US8] Resolve `TODO(LICENSE)` — choose a license, add `LICENSE`, and wire the footer link. **Until then the link is omitted rather than faked.** This is the maintainer's decision and is not an architectural one
- [ ] T617 [P] Run the full gate: `ruff check`, `ruff format --check`, `mypy --strict`, `pytest -q` across all seven suites, `pnpm --dir web lint`, `pnpm --dir web test`
- [ ] T618 [P] Run the sustained chaos harness for 1800 seconds and confirm all five invariants hold
- [ ] T619 Re-read the constitution against the code each phase produced and correct or record any drift, per the phase-gate requirement
- [ ] T620 Confirm every one of the constitution's Definition of Done items is satisfied, including the two that cannot be checked by a machine
- [ ] T621 Confirm a reviewer reaches the deployed URL and is convinced in sixty seconds (V9, SC-008)
- [ ] T622 Confirm the fencing token mechanism can be **whiteboarded cold, without notes** — the zombie timeline, why the epoch must be monotonic, and why the check must live in the database (SC-018)

---

## Dependencies & Execution Order

### Phase dependencies — the real graph

```
Phase 0  Foundation
   │
   ▼
Phase 1  The log is the spine ──────────────── US1 (partial)
   │
   ▼
Phase 2  Replay  ⛔ HARD GATE ───────────────── US1
   │
   ▼
Phase 3  Concurrency and leases ────────────── US1 complete
   │
   ▼
Phase 4  Fencing  ⛔ HARD GATE ──────────────── US2
   │                    │
   │                    └──── unblocks console work (but phase 5 comes first)
   ▼
Phase 5  Two-phase journal ─────────────────── US3
   │        ▲
   │        └── the headline guarantee holds from here and not before
   ▼
Phase 6  Production-shaped behaviour ───────── US4
   │
   ▼
Phase 7  Operator console ──────────────────── US5
   │
   ▼
Phase 8  Chaos → proof → landing ───────────── US6, US7
   │        ▲
   │        └── project definition is COMPLETE here
   ▼
Phase 9  Authoring surface (optional) ──────── US9

Cross-cutting ──────────────────────────────── US8   (spans; gated after phase 8)
```

### Why user stories are not parallel-startable

This is the point at which this task list departs from the template's default, and the departure is
deliberate:

- **US1 → US2**: fencing has nothing to fence without leases and epochs from phase 3.
- **US2 → US3**: the journal's uncertainty resolution assumes a single writer, which is exactly what
  phase 4 establishes.
- **US3 → US4**: retry caps, dead-lettering and cancellation all read the journal and the log.
- **US5 is prohibited before phase 4** by an explicit sequencing rule — not merely inconvenient. A
  beautiful console over an unproven runtime invites scrutiny the system cannot yet survive.
- **US7 is prohibited before phase 8** because its bands quote figures that do not exist earlier.
- **US6 depends on everything**, since the invariants it asserts are the properties the prior phases
  built.
- **US8 spans**, and its gate — the third-party quickstart run — comes after phase 8.
- **US9 is optional** and begins only after phase 8.

### Within each phase

1. Tests first. Write them, **watch them fail**, then implement.
2. Migrations and schema before the code that depends on them.
3. `core/` before `worker/` before `api/` before `web/`.
4. Crash behaviour recorded for every new await point and I/O boundary, in the same change.
5. Exit gate **demonstrated, not asserted** — the gate is a command someone else can run.

### Parallel opportunities

`[P]` tasks touch different files and have no dependency on incomplete work. The densest clusters:

- **Phase 0**: T001–T012, the entire test batch, then T014–T021 scaffold tasks
- **Phase 2**: T105–T114 tests; T135–T140 fixtures
- **Phase 4**: T191–T201 tests, though they share the T214 zombie fixture and it lands first
- **Phase 5**: T229–T246 tests
- **Phase 6**: T293–T316, the complete failure matrix — the largest parallel batch in the project
- **Phase 7**: T379–T395 component tests; T435–T440 mock states
- **Phase 8**: T474–T490 tests
- **Cross-cutting**: T602–T609 documentation

**Not parallelizable despite appearances**: everything touching `anchor/core/events/append.py`
(T076–T079, T202, T208) — it is the single append path, and concurrent edits to it are how a
cancellation check gets dropped.

---

## Parallel Example: the phase-6 failure matrix

```bash
# The largest parallel batch in the project — one module per row of the §9 matrix.
Task: "Write the database-unavailable test in tests/failure/test_database_unavailable.py"
Task: "Write the Redis-unavailable test in tests/failure/test_redis_unavailable.py"
Task: "Write the slow-WebSocket-client test in tests/failure/test_slow_ws_client_dropped.py"
Task: "Write the step-timeout test in tests/failure/test_step_timeout_stops_renewer.py"
Task: "Write the attempt-cap-survives-handoff test in tests/failure/test_attempt_cap_survives_handoff.py"
Task: "Write the payload-ceiling dead-letter test in tests/failure/test_payload_ceiling_dead_letters.py"
```

---

## Implementation Strategy

### The MVP is phase 2, not user story 1

The template's default MVP is "user story 1 only". Here the meaningful first increment is narrower
and lands earlier: **phase 0 → phase 1 → phase 2**. At the end of phase 2 a worker can be killed
mid-run and another resumes from the correct step. That is the product's claim in its smallest
honest form, and §20 of the source specification is explicit that until it happens, nothing else in
the system means anything.

Do not demo before phase 2. Do not claim effectively-once before phase 5.

### Incremental delivery

| Increment | Phases | What can honestly be said |
|---|---|---|
| 1 | 0–2 | "A run survives the death of the machine executing it." **Step granularity only** |
| 2 | 3–4 | "…and a stalled worker that wakes up cannot corrupt it." |
| 3 | 5 | "…and no tool executes twice." **The headline claim, from here** |
| 4 | 6 | "…predictably, under load and repeated failure." |
| 5 | 7 | "…and every run is completely auditable." |
| 6 | 8 | "…and it is measured continuously, not asserted." **Project complete** |
| 7 | 9 | "…and the contract is legible without a clone." *(optional)* |

**Between increments 1 and 3 the headline guarantee does not hold**, and no claim about it may be
published, demonstrated, or written into a README. This is the intended sequencing, not a defect —
but it is the thing most likely to be forgotten under the pressure of having something to show.

### Budget

Phases 4 and 5 will overrun. Concurrency bugs are intermittent, resistant to reproduction, and hard
to reason about. **That difficulty is precisely why the project is worth building**, and expecting
it beats being surprised by it. Expect to return to earlier phases from phase 8 — the sustained run
is where an intermittent bug from phase 4 or 5 finally surfaces, and that is the harness working as
intended rather than a setback.

---

## Notes

- `[P]` = different files, no dependency on incomplete work
- `[Story]` maps a task to a user story for traceability; phase 0 and cross-cutting carry none
- **Verify tests fail before implementing.** Six tests in this file guard holes found by reasoning
  rather than by failure, and a test that has never been red has proven nothing
- Commit after each task or logical group; the branch is per Spec Kit feature with a self-review PR
- Every PR description records the constitution-compliance result
- **Stop and raise** any change that could weaken an invariant, even if it was requested

