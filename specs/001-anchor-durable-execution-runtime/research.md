# Phase 0 — Research and Decisions

**Feature**: 001-anchor-durable-execution-runtime
**Date**: 2026-07-31
**Inputs**: [`anchor-spec.md`](../../anchor-spec.md) (§0–§36, Addenda A–F),
[constitution v1.1.0](../../.specify/memory/constitution.md), [`spec.md`](./spec.md)

Every decision below is recorded as **Decision / Rationale / Alternatives considered**, and every
one names the rule, constraint, or measurement that forced it. Decisions already fixed by the
constitution are marked **[inherited]** and are restated only where the plan depends on a detail the
constitution states as a property rather than as a mechanism.

Three decisions required maintainer approval and were granted on 2026-07-31: the `anchor/` package
wrapper (D-01), the three new tables (D-20, D-21, D-22), and the single-holistic-plan shape (D-38).

**Revision note (2026-07-31, optimality pass).** A second pass over the design found three
correctness holes and nine decisions where the first call was defensible but not optimal. The
resulting fifteen decisions are recorded as **D-41 – D-55 in §10**, and each superseded decision
carries a banner pointing forward. Nothing in §10 requires a constitution amendment; §10.0 states why
for each. The superseded reasoning is left in place deliberately — what was reconsidered and why is
part of the record.

**Revision note (2026-08-08, Addendum F intake).** `anchor-spec.md` gained **Addendum F (§34–§36)**,
which records agent-authoring boilerplate and explicitly defers all of it until phases 1–8 are working
and demoed. The intake is recorded as **D-56 – D-59 in §11**. Three of its four items stay deferred;
one is pulled *forward* into phase 5 because deferring it is the more expensive choice, and the reason
is D-57. No other section of the source specification changed, and nothing in §11 touches an invariant,
the data model, the protocol, or the chaos harness.

---

## 1. Layout, packaging, and toolchain

### D-01 — Python packages live under `anchor/`; `web/` and `ops/` are siblings

**Decision.** The repository root holds `anchor/` (containing `core/`, `worker/`, `runtime/`, `api/`,
`chaos/`), plus `web/`, `ops/`, `tests/`, and `specs/`. Imports read `anchor.core.leases`.

**Rationale.** §5.1 draws `core/`, `worker/`, … directly under `anchor/`, where `anchor/` is the
repository. Taken literally that makes `core` and `api` top-level importable module names, which
collide with common third-party and stdlib-adjacent names and make `pyproject` list five packages.
Wrapping them in one package is a one-level deviation that preserves every directory name and every
boundary the spec cares about. **Approved by the maintainer on 2026-07-31**, as the constitution
requires for layout changes.

**Alternatives considered.** Literal flat layout — rejected for namespace pollution. `src/anchor/` —
rejected as two levels of deviation from a document that cross-references its own tree.

### D-02 — Python 3.12

**Decision.** Pin 3.12 in `pyproject`, the Docker images, and CI.

**Rationale.** `asyncio.TaskGroup` and `asyncio.timeout` (3.11+) are exactly the primitives the
background renewer and the per-step timeout need, and structured concurrency makes the
"renewer cancels the run task, and that task writes nothing after cancellation" requirement
expressible rather than hand-rolled. 3.12 has mature `asyncpg` wheels; 3.13's free-threading is
irrelevant here and adds ecosystem risk to a correctness project.

**Alternatives considered.** 3.11 — acceptable, no benefit. 3.13 — rejected as unnecessary risk.

### D-03 — `uv` for packaging, `ruff` for lint and format, `mypy --strict` for types [inherited]

**Decision.** One lockfile committed. `ruff` covers both lint and format. `mypy --strict` with zero
suppressions added; a suppression is a review conversation, not a fix.

**Rationale.** Constitution, Technology Stack. Reproducible worker images matter because the
Deployments page answers "which build is actually running", and that answer is worthless if two
workers on the same commit resolved different dependency versions.

### D-04 — Dependency set, fixed and minimal

**Decision.** Runtime: `fastapi`, `uvicorn[standard]`, `asyncpg`, `redis`, `pydantic`,
`pydantic-settings`. Migrations only: `alembic`, `sqlalchemy`. Dev: `pytest`, `pytest-asyncio`,
`hypothesis`, `ruff`, `mypy`. Frontend: React, Vite, TypeScript, Tailwind. **Nothing else without
maintainer approval.**

**Rationale.** The constitution requires approval for any dependency. Two candidates were rejected
specifically: a structured-logging library (stdlib `logging` plus a ~20-line JSON formatter is
sufficient, and log shape is not a correctness surface), and `testcontainers` (the compose file
already provides PostgreSQL and Redis, and CI provides service containers — see D-34).

**Alternatives considered.** `structlog` — rejected, no capability gained. `SQLAlchemy Core` for
query building — rejected; explicit SQL is required on the hot path anyway and a second dialect of
query construction would blur where the SQL that enforces invariants lives.

### D-05 — Alembic, forward-only, with raw SQL for every constraint and trigger [inherited]

> **Extended by [D-45](#d-45--migrations-are-a-gated-one-shot-step-and-every-process-refuses-to-start-on-a-schema-mismatch).** Choosing Alembic was right; leaving *when* it runs unspecified was not.

**Decision.** Alembic owns migration ordering and history. Every constraint, trigger, and function is
written as raw SQL inside `op.execute`. `sqlalchemy` is importable **only** under
`ops/migrations/`, asserted by a test that walks imports (D-33). No `downgrade` is written for a
migration that would lose data; those raise instead.

**Rationale.** The invariants live in DDL, and DDL that a reviewer cannot read in the diff is DDL
nobody audits. Alembic supplies ordering, a version table, and a standard runner without asking the
runtime to depend on an ORM.

**Alternatives considered.** Numbered `.sql` files with a hand-written runner — viable, rejected
because ordering, idempotent application, and "which migrations ran" all get reinvented.
Autogenerate from models — rejected outright; there are no models, and autogenerate cannot express
the epoch trigger.

### D-06 — Node 22 LTS, `pnpm`, React + Vite, TypeScript strict, Tailwind v4

**Decision.** Tailwind v4 with tokens declared as CSS custom properties in a single theme layer,
carrying a dark set and a light set.

**Rationale.** §24.4 requires the signature colors to live in CSS custom properties "so they render
consistently regardless of theme", and the constitution requires dual-valued tokens with nothing
hardcoded. Tailwind v4's CSS-first theme is that requirement expressed natively rather than bridged
through a JS config.

**Alternatives considered.** Tailwind v3 with a JS theme — workable, needs a bridge to expose the
same values as custom properties for the SVG strand and the timeline fills. A component library
(shadcn/ui, Radix) — rejected: the console is dense bespoke instrumentation, and §21.2 is explicit
that borders, shadows, and glass panels are what a template looks like.

---

## 2. The append path

### D-07 — Append is one statement: a CTE that increments `last_seq` and inserts the event

**Decision.**

```sql
WITH s AS (
  UPDATE runs SET last_seq = last_seq + 1
  WHERE id = $1
  RETURNING last_seq
)
INSERT INTO run_events (run_id, seq, type, payload, epoch, worker_id)
SELECT $1, s.last_seq, $2, $3::jsonb, $4, $5 FROM s
RETURNING seq, created_at;
```

**Rationale.** The `UPDATE` takes the `runs` row's write lock, which is the serialization point
Addendum C §25.4 requires; the epoch trigger then reads a value no concurrent claim can move; the
sequence allocation is uncontended because `I3` guarantees one writer; and a rollback un-increments
the counter, so `I2`'s no-gaps property holds. One statement also means there is no window between
allocation and insert in which the process can die and leave the counter advanced.

**Alternatives considered.** `SELECT MAX(seq)+1` with catch-and-retry — forbidden by the
constitution, because it turns a fencing bug into invisible retry noise. A per-run `SEQUENCE` —
forbidden; non-transactional, so a rollback leaves a gap and breaks a published invariant. Lock
`runs` with an explicit `SELECT … FOR UPDATE` and then insert in a second statement — correct but two
round trips and one more place to forget the lock.

### D-08 — The epoch write-gate is a `BEFORE INSERT` trigger that takes the row lock itself

**Decision.** The trigger reads the run's current epoch with `SELECT epoch FROM runs WHERE id =
NEW.run_id FOR UPDATE` and raises `SQLSTATE 'AN001'` when `NEW.epoch < current_epoch`. It also
raises when `NEW.epoch > current_epoch`, which can only mean a writer invented an epoch.

**Rationale.** Constitution: the check must be in the database, and it must hold for a code path that
did not exist when it was written — including a migration script and a `psql` session. Taking the
lock **inside** the trigger makes the guarantee independent of whether the caller remembered to lock,
which is the difference between a constraint and a convention. Re-locking a row the same transaction
already holds is free, so this composes with D-07 rather than fighting it. Lock ordering is uniform
(`runs` before `run_events` on every path), so no deadlock cycle exists.

**Alternatives considered.** `UPDATE … WHERE epoch = $1` with a rowcount check in the worker —
explicitly forbidden as application-level enforcement. A `CHECK` constraint — impossible; `CHECK`
cannot reference another table's row. A foreign key on `(run_id, epoch)` against a per-epoch table —
considered and rejected: it would permit writes at any *past* epoch, which is precisely the hole.

### D-09 — `now()`, never `clock_timestamp()`

**Decision.** Every lease read and write uses `now()` (transaction start time). `clock_timestamp()`
appears nowhere.

**Rationale.** `I5` requires the database clock, and two reads inside one transaction must agree — a
claim that evaluates expiry with one value and sets the new lease from another has an internal
inconsistency that appears only under load.

### D-10 — Claim is two statements in one explicit transaction

**Decision.** Statement 1 selects and updates the candidate:

```sql
WITH candidate AS (
  SELECT id FROM runs
  WHERE status = 'pending'
     OR (status = 'running' AND lease_expires_at < now())
  ORDER BY priority ASC, created_at ASC
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE runs r
   SET epoch = r.epoch + 1,
       owner_worker_id = $1,
       lease_expires_at = now() + $2::interval,
       status = 'running',
       claimed_at = now()
  FROM candidate c
 WHERE r.id = c.id
RETURNING r.id, r.epoch;
```

Statement 2 is the ordinary append helper (D-07) writing `RUN_CLAIMED` with the returned epoch. Both
commit together.

**Rationale.** §6 requires one query that handles both new and expired-lease runs, and `I4` requires
claim, epoch increment, lease, and claim-event to be atomic. Reusing the append helper for statement
2 means the claim event goes through the same trigger and the same counter as every other event —
uniform enforcement rather than a special case. Two statements in one transaction is not two
decisions: nothing observes the intermediate state, because the row lock is held to commit.

**Alternatives considered.** A single mega-statement that also inserts the event — possible with
nested CTEs, rejected because it duplicates the append logic and puts `I2`/`I3` enforcement in two
places. `ORDER BY … FOR UPDATE` without `SKIP LOCKED` — rejected; workers would queue behind each
other instead of fanning out.

### D-11 — `priority ASC`, lower number sooner, default 0

**Decision.** `priority smallint NOT NULL DEFAULT 0`, ordered ascending.

**Rationale.** §6's claim query says `ORDER BY priority, created_at` with no direction, which is
ascending in SQL. Choosing the reading that matches the literal text avoids a silent divergence
between the document and the code; the direction is documented at the column and in the API.

### D-12 — Idempotency key: SHA-256 over a canonical JSON encoding, with a short display form

> **Framing superseded by [D-41](#d-41--the-idempotency-key-is-hashed-over-a-canonical-json-array-not-a-delimited-string).** The hash inputs, the storage, and the display form stand.

**Decision.** `idempotency_key = sha256("{run_id}|{step_index}|{action_name}|{canonical_json(args)}")`
as lowercase hex, stored whole and uniquely constrained. `args_hash` stores the SHA-256 of the
canonical arguments alone. The console displays `r{run_id}:s{step_index}:{first 4 hex of args_hash}`,
matching the spec's `run47:s1:a91f` shape, and the full key is available in the tooltip.

**Rationale.** §3.3 defines the key's inputs. Storing the full hash keeps the unique constraint
collision-proof; storing `args_hash` separately makes "the same arguments at a different step"
queryable, which the invariant checker needs. The truncated display form exists because a 64-hex key
is unreadable in a timeline label, and truncation in the *view* costs nothing while truncation in the
*key* would be a silent correctness reduction.

**Alternatives considered.** Truncating the stored key to 16 hex — rejected; a birthday collision is
unlikely but the failure mode is a skipped side effect, which is unacceptable at any probability.
BLAKE2b — faster, rejected for SHA-256's ubiquity in review conversations.

### D-13 — Canonical serialization: JSON-only argument types, sorted keys, compact separators, rejected specials

**Decision.** Tool and model arguments MUST be JSON-native: object, array, string, integer, float,
boolean, null. The canonical encoding sorts object keys by Unicode code point, uses `(',', ':')`
separators, emits no insignificant whitespace, normalizes strings to NFC, encodes integers in
decimal, encodes floats with Python's shortest round-trip `repr`, and **raises** on NaN, `±Infinity`,
non-string keys, sets, tuples, `datetime`, `Decimal`, or any other type. The raise carries the path
to the offending value.

**Rationale.** §3.3 states that a hash differing across replay silently defeats deduplication, so
every source of encoding freedom is either eliminated or made an error at call time rather than a
divergence at replay time. Rejecting types is the "explicit beats clever" reading: a developer who
passes a `datetime` gets an immediate, located error instead of an idempotency key that depends on
`str(datetime)` behaviour. Float `repr` has been shortest-round-trip and stable since Python 3.1,
and the property test (D-31) pins it.

**Alternatives considered.** Accepting arbitrary objects via a pluggable encoder — rejected; it moves
the stability guarantee into user code. CBOR canonical form — genuinely well-specified and rejected
only because the journal is read by humans in the console, and JSON is the format the log already
uses. Coercing floats to a fixed decimal string — rejected; it loses information and surprises.

### D-14 — Run ids are `bigint` identity, rendered `run_47`; worker ids are stable strings

> **Worker identity superseded by [D-42](#d-42--worker-identity-carries-an-incarnation-counter).** Hostname plus pid is reused across restarts on a container platform. The run-id half stands.

**Decision.** `runs.id bigint GENERATED ALWAYS AS IDENTITY`. The UI renders `run_{id}`. A worker's id
is assigned at registration as `worker-{suffix}` where the suffix is derived from hostname and pid
and is stable for the process lifetime.

**Rationale.** The spec's own examples read `run_47`, `worker-a`, `worker-c` throughout, and the
vocabulary rule says the interface uses the same words as the logs. A `bigint` also keeps
`(run_id, seq)` index entries compact, which matters because that index is on the hottest write path.
Nothing in the product needs unguessable run ids: there are no accounts, no per-user data, and every
run is world-readable by design.

**Alternatives considered.** UUIDv4 ids — rejected; wider index, and `run_9f2c…` breaks every example
in the document. UUIDv7 — same objection, and the time-ordering it buys is already given by
`created_at`.

### D-15 — `ctx.new_id()` returns a UUIDv4 from the stdlib, journaled

**Decision.** Stdlib `uuid.uuid4()`, recorded as `NONDET_RECORDED` with kind `id`.

**Rationale.** The value's ordering is irrelevant because it is read back from the log on replay; what
matters is that it is journaled and that the call is individually greppable. A UUIDv7 helper would be
either a dependency or hand-rolled bit-twiddling, and neither buys a property this system needs.

---

## 3. Lease, renewal, and the worker loop

### D-16 — One `asyncio.TaskGroup` per claimed run: the step task and the renewer task

**Decision.** Claiming a run opens a `TaskGroup` containing the run's execution task and its lease
renewer. The renewer extends on its own timer. A rejected renewal (SQLSTATE `AN001` on the renewal
statement, or zero rows affected because ownership moved) cancels the execution task and the group
exits. Nothing in the group writes after cancellation, enforced by every write path going through the
one append helper, which checks its own cancellation state before issuing SQL.

**Rationale.** Addendum C §25.5 requires renewal to be independent of step progress and names the
cancellation path as "real code with a real race" that needs a test rather than an argument.
`TaskGroup` makes the parent-child cancellation semantics explicit and guarantees the group is not
left half-running if either task raises.

**Alternatives considered.** A single loop that renews between steps — superseded by Addendum C,
because it makes recovery time strictly greater than the longest permitted step. A separate renewer
*process* — rejected; it would be able to signal liveness that outlives a stalled worker, which is
exactly the property §3.4 relies on not existing.

### D-17 — Lease renewal is an `UPDATE … WHERE id = $1 AND epoch = $2` and a `LEASE_RENEWED` append

**Decision.** Renewal updates `lease_expires_at = now() + $interval` guarded by the epoch in the
`WHERE` clause, and appends `LEASE_RENEWED`. Zero rows affected means ownership moved; the append's
trigger would independently reject the write.

**Rationale.** Two independent detectors for the same condition is acceptable here — and is not "two
sources of truth" — because both read the same authoritative column in the same database, and the
trigger is the one that is load-bearing. The `WHERE` clause exists to avoid writing a
`LEASE_RENEWED` event that the trigger would then reject, keeping the log free of noise.

**Note on volume — superseded by [D-48](#d-48--lease_renewed-is-emitted-at-boundaries-and-on-threshold-breaches-renewal-latency-lives-in-telemetry).**
`LEASE_RENEWED` at a 1-second interval on the demo profile is one event per second per active run.
Hiding it in the UI was a band-aid on a data problem; D-48 fixes the emission policy instead.

### D-18 — Live configuration is a `runtime_config` table, polled with a Redis nudge, applied at step boundaries

**Decision.** `runtime_config` holds the timing, retry, and concurrency values with a monotonically
increasing `version`. PostgreSQL is authoritative. Workers read at startup, re-read on a bounded
poll, and additionally subscribe to a Redis channel that carries only "the version changed" as a
promptness hint. **New values are applied only at a step boundary**, never mid-step. The API
re-runs the startup assertion on write and **rejects the write** when it fails.

**Rationale.** §13.3 requires live editing without a redeploy; §25.5 requires the assertion to reject
the change rather than the fleet; the constitution forbids Redis from holding anything
authoritative. Polling from PostgreSQL keeps the single source of truth and makes Redis pure delivery
— exactly the role §4 assigns it. Applying at a step boundary avoids changing lease arithmetic
underneath an in-flight renewal, which would produce precisely the intermittent fencing bug §6.1
warns about.

**Alternatives considered.** Config in Redis — forbidden. Config in the process environment with a
restart — rejected; it deletes the feature §13.3 argues is what makes the console read as tooling.
`LISTEN/NOTIFY` instead of Redis pub/sub — genuinely attractive, since it needs no second system and
is transactional with the write; rejected only because it holds a dedicated PostgreSQL connection per
worker for a non-authoritative hint, and Redis is already present for fan-out. Recorded as the
fallback if Redis is ever removed.

### D-19 — Worker kill is delivered over Redis pub/sub; the process hard-exits

**Decision.** `POST /api/workers/{id}/kill` publishes to `worker:{id}:control`. The worker's
subscriber calls `os._exit(137)` immediately, skipping every cleanup path, because that is what a
crash does. A `mode=graceful` variant releases the lease first and exits 0, and the interface labels
the two differently. Both record a `chaos_events` row. If Redis is unreachable the endpoint returns
an honest error stating that kill delivery is unavailable and that execution is unaffected.

**Rationale.** §8 makes the kill endpoint a first-class feature and §21.4 requires it to be real; a
terminal is not reachable on a hosted container. Ownership is never carried on this path, so using
Redis does not violate the non-authoritative rule. Addendum C §25.5's closing note asks for both
paths to be offered and labelled, because showing a reviewer why they differ demonstrates the
recovery path is understood rather than merely observed.

**Alternatives considered.** A `kill_requested_at` column that workers poll — rejected; it delays the
kill by the poll interval, which blunts the demo, and it stores a control signal next to authoritative
state. Platform APIs (Render's restart endpoint) — rejected; it is not a crash, it is slower, and it
couples the product to one host.

---

## 4. Schema decisions requiring approval

### D-20 — `chaos_runs` (new table; approved)

**Decision.** One row per harness execution: parameters (worker count, kill rate, latency and failure
injection rates, duration), `status` in `pending`/`running`/`completed`/`failed`/`abandoned`, start
and end timestamps, and the deployment mode it ran in.

**Rationale.** §8 exposes `POST /api/chaos/start` and `GET /api/chaos/{id}/report`, and §13.3's
History page requires every past run to be listable. Neither is expressible against `chaos_events`
alone, which records individual injected failures with no notion of the run that injected them.

### D-21 — `chaos_reports` (new table; approved)

**Decision.** One row per completed chaos run: the five invariant results, duplicate-effect count,
stranded-run count, recovery latency percentiles, replay overhead, throughput, kill count, run and
step totals, the configuration profile, and the lease duration in force. **Immutable in every
deployment mode**, enforced by a trigger that raises on `UPDATE` and `DELETE`.

**Rationale.** §31 forbids altering chaos history in both modes, and §21.6 forbids the reset
affordance from touching it. The constitution requires published numbers to carry the profile and
lease they were measured under, which means those belong on the report row rather than being
reconstructed later from configuration that has since been edited.

### D-22 — `runtime_config` (new table; approved)

**Decision.** Key/value with a typed value column, a monotonically increasing `version`, and
`updated_at`. Seeded from the active profile at first migration.

**Rationale.** See D-18. Recorded here separately because it is a schema addition beyond §7 and the
constitution requires those to be raised before they are made.

### D-23 — Terminal states release the lease, enforced by a `CHECK`

**Decision.** `completed`, `failed`, `cancelled`, and `needs_review` all set `owner_worker_id` and
`lease_expires_at` to `NULL`, and a table `CHECK` makes any other combination unrepresentable.

**Rationale.** The constitution requires illegal states to be modelled structurally, giving the
example "a run cannot be both `completed` and hold a lease". `needs_review` is included because it
halts the run and a halted run holding a lease would block reclaim forever while looking healthy.

**Consequence, stated because it is not obvious.** A `needs_review` run holds no lease, so the
operator's resolution write cannot carry a worker's epoch. See D-24.

### D-24 — Operator resolution writes are attributed to `operator` at the run's current epoch

**Decision.** `POST /api/runs/{id}/resolve` appends with `worker_id = 'operator'` and the run's
current epoch, permitted only when the run is `needs_review` and therefore holds no lease. Resolving
"the effect did happen" writes the missing `TOOL_RESULT` with an operator-attributed payload;
resolving "it did not" marks the journal row unexecuted and returns the run to `pending`; resolving
"abandon" finalizes as `cancelled`. Every outcome appends an event naming the human decision.

**Rationale.** `I8` says uncertainty is resolved by policy, and for the `unsafe` category the policy
*is* a human. That human's decision must be in the log, attributable, and epoch-consistent, or the
audit trail has a hole exactly where the system admitted it did not know something. Restricting the
write to a leaseless `needs_review` run means it can never race a worker.

**Alternatives considered.** Letting a worker perform the resolution after reading an operator flag —
rejected; it adds a second source of truth for a decision that is already recorded, and it delays the
resolution by a poll interval for no benefit.

---

## 5. Replay and determinism

### D-25 — Replay is a pure fold over events; the reconstructed context is compared by canonical hash

**Decision.** `core/replay` exposes `reconstruct(events) -> RunContext` as a pure function with no
I/O. The replay-determinism test compares `canonical_json(final_state)` hashes rather than object
identity or `repr`.

**Rationale.** The standard asks for a "byte-identical final state"; comparing by canonical hash both
makes that precise and dogfoods the serializer whose stability the whole idempotency mechanism
depends on. Purity is what lets the concurrency and failure tests build a log by hand and assert on
reconstruction without a database.

### D-26 — A "step" is one `decide_next_step` invocation and the action it returns

**Decision.** `step_index` increments once per invocation. `STEP_STARTED` precedes the invocation;
`LLM_CALLED`, `TOOL_INTENT`/`TOOL_RESULT`, or `NONDET_RECORDED` records the action's boundary
crossings; `STEP_COMPLETED` closes it. A step contains at most one side-effecting tool call.

**Rationale.** §4.1 argues the step boundary is the natural transaction boundary "because it is
precisely where side effects occur". One side effect per step is what makes
`hash(run_id, step_index, action, args)` unique without a within-step counter, and what makes the
timeline segment a meaningful unit of duration.

**Alternatives considered.** Allowing several tool calls per step with a sub-index — rejected; it
widens the uncertainty window to cover multiple effects and complicates the three-state lookup for no
gain the demo agent needs.

### D-27 — The determinism ban is enforced by an AST check, not a string search

**Decision.** The required test parses every module under `anchor/runtime/agents/` with `ast` and
fails on any `Import`, `ImportFrom`, or attribute access reaching `datetime`, `time`, `random`, or
`uuid`. The same function backs the authoring validator's first check.

**Rationale.** §25.3 asks for a three-line test; a string search over source would be three lines and
would also flag the word `time` in a comment and miss `__import__("random")`. An AST walk is a dozen
lines, has no false positives on prose, and is the same code the validator needs — so writing it once
satisfies both `I6`'s commit-time guard and FR-123.

### D-28 — Stubbed model calls sleep to simulate latency, and that is not the banned `sleep()`

**Decision.** The stub adapter awaits a fixed, configured duration to emulate provider latency.

**Rationale.** Recorded explicitly because the constitution's anti-pattern list forbids "`sleep()` as
a synchronization mechanism", and a reader auditing against that list will encounter this sleep. It
is a *simulation* of an external call's duration, not a substitute for a synchronization primitive.
Naming the distinction here prevents the fix that would break the demo's varied step durations.

---

## 6. API, fan-out, and the console

### D-29 — WebSocket fan-out: API subscribes to Redis, per-client bounded queue, drop-and-backfill

> **Subscription topology superseded by [D-50](#d-50--one-redis-firehose-channel-demultiplexed-in-process).** The bounded queue, the drop policy, and `seq`-exact backfill all stand.

**Decision.** The API subscribes to `run:{id}:events` and `fleet:telemetry`. Each connected client
gets a bounded queue; a client that exceeds it is closed with a code and a reason the interface
displays, and it reconnects and backfills with `GET /api/runs/{id}/events?after_seq=N`. Every
WebSocket frame carries the `seq` it corresponds to, so a client can detect its own gap.

**Rationale.** §9 requires a slow client to be dropped past a buffer threshold and able to resubscribe
and backfill from the log; the constitution requires every fan-out to have a bound. Carrying `seq` on
each frame is what makes backfill exact rather than approximate — the client asks for what it
actually missed.

**Alternatives considered.** Unbounded per-client buffering — a bug by the constitution's definition.
Redis Streams with consumer groups — more machinery, and the log itself is already the durable record
that makes replayable delivery unnecessary.

### D-30 — Metrics are derived from `run_events` on read; only harness reports are stored

> **Partially superseded by [D-49](#d-49--a-derived-rebuildable-metrics-rollup-computed-off-the-hot-path).** Correctness reads stay live on the source, exactly as below. Display-only time series move to a rollup, because full scans per dashboard poll do not survive one chaos corpus.

**Decision.** `GET /api/metrics` computes its series from `run_events` and `runs` with supporting
indexes. Nothing pre-aggregates live state. `chaos_reports` stores the harness's own computed
numbers, because those are a report of a completed experiment rather than a cache of current state.

**Rationale.** The constitution forbids "a cache in front of a correctness read". Duplicate-effect
count in particular must be computed from the journal every time it is displayed, because it is the
product's central claim and a stale zero would be the single most damaging thing this interface could
show. Materialized views remain available if a query proves slow, and would be introduced with the
query they serve and their refresh cost stated.

### D-31 — Frontend data layer: typed `fetch` client, two stream hooks, no query library

**Decision.** A hand-written typed API client, `useRunStream(runId)` and `useFleetStream()` for
WebSocket subscriptions with polling fallback, and component-level props. No TanStack Query, no SWR.

**Rationale.** The constitution puts data fetching in hooks and components as pure functions of
props, which is the whole of what a query library would provide here; adding one requires approval and
buys caching the console explicitly does not want (D-30's reasoning applies to the client too).

### D-32 — `RunDetail`/`RunThread` take data as props and raise kill to the parent [inherited]

**Decision.** No fetching, no WebSocket, no API call inside either component; `now` is injectable.

**Rationale.** §24.6. Recorded here because the injectable `now` is the detail most likely to be
dropped, and without it every snapshot test of "41s ago" flaps.

---

## 7. Testing and CI

### D-33 — Test suites are directories that map one-to-one onto the required classes

**Decision.** `tests/unit`, `tests/property`, `tests/replay`, `tests/concurrency`, `tests/failure`,
`tests/boundary`, `tests/contract`, `tests/web`. `tests/failure` contains one module per row of §9's
failure matrix, named after the row.

**Rationale.** The constitution enumerates the required classes and requires every failure-matrix row
to have a test. Making the directory structure mirror that list turns "is the coverage complete?"
into a directory listing rather than a judgement, and turns §9 into the test plan it already
implicitly is. Two boundary tests live in `tests/boundary` specifically: the `sqlalchemy`-confinement
walk and the deployment-mode 404 assertions.

### D-34 — Integration tests run against real PostgreSQL and Redis from compose or CI services

**Decision.** A session fixture applies migrations once against a dedicated test database; each test
runs in a transaction that is rolled back, except concurrency and failure tests, which need real
commits and instead truncate between cases. CI provides `postgres:16` and `redis:7` as service
containers.

**Rationale.** Every invariant this project claims is enforced by PostgreSQL — a trigger, a unique
constraint, `SKIP LOCKED` semantics, and `now()`. A test double for the database would test the
double. `testcontainers` is avoided per D-04 because compose and CI services already provide the
same thing without a dependency.

**Alternatives considered.** SQLite for unit tests — rejected; it has none of the semantics under
test. A shared long-lived test database — rejected; concurrency tests would interfere.

### D-35 — CI gates every push and runs a bounded chaos smoke; sustained chaos is scheduled against the deployment

**Decision.** On push: `ruff`, `mypy --strict`, all pytest suites, and a bounded chaos smoke —
short duration, three workers, an aggressive kill rate — asserting all five invariants. On a
schedule: the sustained harness against the deployed instance, writing a `chaos_reports` row, with an
automated job refreshing the README's figures from the latest report.

**Rationale.** The constitution requires both, and the split is what makes them practical: a
30-minute sustained run per commit would make CI useless, while a per-commit smoke catches an
invariant regression at the commit that caused it. The deployed instance already has the fleet the
sustained run needs.

### D-36 — The chaos harness drives the system through its public API

**Decision.** The harness submits runs, kills workers, and reads logs through HTTP and the database's
read path only — never by importing worker internals. `POST /api/chaos/start` inserts a `chaos_runs`
row and executes the run as a bounded background task in the API process; the CLI entry point does
the same thing out-of-process for local and CI use.

**Rationale.** A harness that reaches into internals proves the internals agree with themselves. One
that goes through the same surface a reviewer uses proves the system. Using the same code path for
the console button and the CLI means the number on the landing page and the number in CI are produced
by one implementation.

**Honest limitation, recorded rather than hidden.** The harness is the test rig, not the system under
test, and it is **not** itself durable: an API restart mid-run abandons the chaos run. Any
`running` chaos row older than a threshold is marked `abandoned` on startup, and abandoned runs are
displayed as abandoned rather than dropped. Making the harness durable would mean running it on
Anchor, which is circular and would compromise the independence of the proof.

---

## 8. Deployment and operations

### D-37 — Compose topology: `postgres`, `redis`, `api`, `worker` scaled to three, `web`

**Decision.** `docker compose up` brings all five up with `restart: always` on the workers, the
console on port 3000, and `ANCHOR_AUTHORING_EXECUTE=true` set **only** in the compose file. Render
mirrors this as one web service, one PostgreSQL, one Redis, and three always-on background workers on
a paid tier, with the variable unset.

**Rationale.** §4 requires three or more workers locally from day one — "a single-worker development
environment hides every bug the project exists to solve" — and requires a paid tier because a
sleeping worker is not a fault-tolerant runtime. `restart: always` is what makes killing workers safe
rather than destructive, which is the same self-healing property the product claims.

### D-38 — One holistic plan; `/speckit-tasks` per phase (approved)

**Decision.** A single feature directory holds the whole-project spec, plan, research, data model, and
contracts. Task lists are generated per phase on demand.

**Rationale.** The architecture is cross-phase and needs one home; task lists are not, and a
400-item list covering phases 1–9 would be stale before phase 6 was reached. Approved by the
maintainer on 2026-07-31.

### D-39 — Rate limiting is in-process per IP, and that is adequate because there is exactly one web instance

**Decision.** A token bucket in the API process, keyed by client IP, for submission and kill. The
limit and window live in configuration.

**Rationale.** §21.6 requires a submission rate limit and an hourly demo cap; the deployment has one
web service, so a per-process bucket is the whole fleet. Recorded with its assumption stated, because
the moment a second web instance exists this becomes wrong and would need Redis.

### D-40 — Logging is stdlib `logging` with a JSON formatter, correlated by run id and epoch

**Decision.** Every worker log line carries `run_id`, `epoch`, `worker_id`, and `step_index` where
applicable. No dependency added.

**Rationale.** The console's per-segment log lines are read from `run_events`, not from process logs,
so process logging exists only for operator debugging. Carrying the epoch is what makes a fencing
incident reconstructable from two workers' logs after the fact.

---

## 9. Open items deliberately left unresolved

| Item | Why it is not being decided now |
|---|---|
| **License** | The maintainer's choice, and not an architectural one. §32.4 requires the footer link; until a license exists the link is omitted rather than faked, and the constitution carries the `TODO(LICENSE)`. |
| **Which real model provider** | The *interface* is decided now (D-55) so an adapter is purely additive. Which provider, and whether one is ever added, is out of scope until phases 1–8 are complete and is forbidden in demonstration mode regardless. |
| **Light theme build-out** | Tokens are dual-valued from the start so the theme is buildable at any time; shipping it is not required for phases 1–8. |
| **Scheduled / recurring runs, webhooks, human-in-the-loop pause** | Add-if-early items. Their console pages stay absent rather than empty, and their schema is not being pre-built. |
| **Log sharding across hosts** | The known scaling remediation, deliberately not implemented — its existence is the answer to "what breaks when you add workers". **D-52 now constrains *how* it may ever be done**, because the obvious approach destroys the schema's most important constraint. |

---

## 10. Revised and additional decisions — the optimality pass

### 10.0 What triggered this pass, and why none of it needs a constitution amendment

A second reading of §1–§9 against the failure modes each decision would actually produce found:

- **three correctness holes** — a retry cap that resets across a worker handoff (D-43), a global
  concurrency cap that enforced nothing (D-44), and worker identity that is reused across container
  restarts (D-42);
- **two deployment hazards** — unspecified migration timing against a fleet that boots concurrently
  (D-45), and tool safety declarations that can silently disagree between two code versions (D-46);
- **four scale-or-latency decisions that were adequate rather than right** — per-call non-determinism
  journaling (D-47), unconditional renewal events (D-48), full-scan metrics (D-49), and per-run Redis
  subscriptions (D-50);
- **and six hardening calls** worth stating rather than discovering (D-41, D-51, D-52, D-53, D-54,
  D-55).

**No constitution amendment is required**, and that is a load-bearing claim rather than a
convenience, so here is the check per principle that could plausibly be implicated:

| Change | Principle that could be implicated | Why it holds |
|---|---|---|
| D-49 metrics rollup | Anti-pattern 6, "a cache in front of a correctness read" | The duplicate-effect count, the stranded-run count, and every chaos-report figure continue to be computed from `tool_journal` and `run_events` at read time. Only *display time series* are rolled up, and the rollup is derived, watermarked, and rebuildable from the log by construction. A throughput sparkline is not a correctness read. |
| D-48 renewal emission policy | Data Model, "the 17 event types MUST exist"; FR-025 | All 17 still exist and `LEASE_RENEWED` is still emitted. Only its *frequency* changed, and renewal latency remains fully measured. Replay does not consume `LEASE_RENEWED` at all, which is what makes it observability rather than audit. |
| D-47 batched non-determinism | `I6`, "non-determinism is journaled, never re-derived" | Every value is still journaled, in order, before **anything that depends on it leaves the process**. The flush is in the *same transaction* as the step's `TOOL_INTENT`, so there is no interleaving in which an effect exists whose inputs are unrecorded. |
| D-43 derived attempt counts | `I2` append-only | Deriving from the log is strictly *more* append-only than the counter it replaces. |
| D-45 migration gating | `I7` fail closed | It adds a fail-closed check where there was none. |
| D-42 worker incarnations | Naming precision; audit completeness | It makes `worker_id` mean one process, which is what every existing claim about attribution already assumed. |

---

### D-41 — The idempotency key is hashed over a canonical JSON array, not a delimited string

*Supersedes D-12's encoding. Hash inputs, storage, and display form unchanged.*

**Decision.**

```
idempotency_key = sha256( canonical_json([run_id, step_index, action_name, args]) )
```

The same canonical encoder from D-13 produces the framing. There is no `|` separator anywhere.

**Rationale.** A delimited string makes injection resistance a matter of *reasoning* — "could an
action name contain a pipe such that two different tuples produce one byte string?" — when it can
instead be a matter of *structure*. Canonical JSON is self-delimiting: `["a|b", 1]` and `["a", "b|1"]`
encode differently, unconditionally, with no argument about which characters are legal in a tool name.
It also means the key derivation has exactly one encoder to test, and the property test that protects
canonical serialization now protects key framing at the same time. **The thing that must never
collide is derived by the thing that is already property-tested.**

**Alternatives considered.** Length-prefixed framing (`len(name):name`) — unambiguous and correct,
rejected as a second bespoke encoding to test. Hashing each component and concatenating digests —
also unambiguous, rejected because it obscures what was hashed when debugging a key mismatch, which
is the exact situation where the stored `args_canonical` needs to explain itself.

### D-42 — Worker identity carries an incarnation counter

*Supersedes D-14's worker-id scheme.*

**Decision.** `workers.id` is `{label}#{incarnation}` — `worker-a#1`, `worker-c#7`. The **label** is
claimed from a small pool (`a`, `b`, `c`, …) at registration and identifies a fleet *slot*; the
**incarnation** comes from a PostgreSQL sequence per label and identifies one process lifetime.
`workers.label` and `workers.incarnation` are stored as their own columns. The identity hue is derived
from the **label**, so a worker's color survives its restart.

**Rationale.** Hostname plus pid is **reused** on a container platform: a killed worker restarts in a
container with the same hostname and can easily receive the same pid. Under D-14 that produced a
silent aliasing bug with three consequences, each of which quietly falsifies something the product
claims:

1. `runs.owner_worker_id` would point at an id that now denotes a **different process**, so
   "which worker executed each step" — product guarantee 3 — becomes untrue without any error.
2. The `workers` row would be overwritten on re-registration, so `started_at` and uptime would
   describe the new process while historical events attribute work to the id as though it were
   continuous. Register-then-die detection (FR-067) would be blind to a *repeated* register-then-die.
3. **The Deployments page could not answer its own question.** §13.3 says its value is telling you
   whether an in-flight run is being resumed by a worker running different code — which is
   unanswerable if two code versions can share a worker id.

`worker-a#3` reads naturally in a log line (`run_claimed worker-c#2 epoch=6`), makes a restart
*visible in the log* rather than inferred, and keeps the spec's short readable names.

**Alternatives considered.** A `bigint` identity with a separate display label — clean FKs, rejected
because the raw event log becomes unreadable and the spec's own examples use the name as the id. A
UUID per process — unique and unreadable. Appending a start timestamp — unique, but 13 digits of
noise in every log line, and it sorts worse than a counter.

### D-43 — Step attempt counts are derived from the log, never held in memory or on `runs`

*New. This closes a correctness hole.*

**Decision.** A step's attempt count is computed during replay as the number of `STEP_FAILED` events
recorded for that `step_index`. `runs.attempts` remains **only** as a denormalized convenience for
the list view and is explicitly documented as derived. The retry decision reads the derived value.

**Rationale.** Under the original design the attempt count lived in the worker's memory for the
duration of the run. Trace the interaction with a handoff:

```
worker-a  step 4 fails  attempt 1 → STEP_FAILED, backoff
worker-a  step 4 fails  attempt 2 → STEP_FAILED, backoff
worker-a  killed
worker-c  claims, replays, resumes step 4  ← in-memory count is GONE, restarts at 1
worker-c  step 4 fails  attempt 1, 2 …
worker-c  killed
…
```

**A poison step plus worker churn retries forever.** That directly violates product guarantee 4 —
"a poisonous run does not retry forever" — and §9's dead-letter row, and it does so *silently*, with
every individual worker behaving exactly as specified. Nothing in the invariant set catches it either,
because terminal-state reachability is only asserted "within a bounded time" by the chaos harness,
where a long-poisoned run looks like a stranded run and the cause would be non-obvious.

Deriving from the log is the fix, and it is free: replay already reads every event, `STEP_FAILED` is
already appended per attempt, and the count is then **durable, exact, and immune to handoff** — which
is the same argument that put every other piece of run state in the log.

**Alternatives considered.** A counter column on `runs` incremented per failure — survives handoff
but is per-run, not per-step, so a run failing two different steps twice each would dead-letter as
though one step failed four times. A `step_attempts` table — a second source of truth for something
the log already records.

### D-44 — The global concurrency cap is enforced inside the claim statement

*New. This closes a correctness hole.*

**Decision.** The claim statement is guarded by the fleet-wide running count:

```sql
WHERE ... AND (SELECT count(*) FROM runs WHERE status = 'running') < $global_cap
```

evaluated inside the same transaction as the claim, against an index on `status`. The API **reports**
saturation (`/api/health` exposes the cap and the current count) but does not reject submissions.

**Rationale.** The original plan enforced the cap "at submission", which enforces nothing useful and
contradicts the specification in two directions at once. §9's saturation row requires that "new runs
stay `pending`" — so submission must succeed. And §5 lists admission control on the API — so the cap
must be visible there. Both are satisfied only if the *enforcement* is at claim and the *reporting*
is at the API: a cap that rejected submissions would fail the first requirement, and a cap that only
displayed a number would fail to cap anything.

Enforcing it in the claim transaction also makes it authoritative in the one place `I4` already puts
ownership decisions, rather than distributed across N workers each counting locally — which is what a
worker-side global cap would be, and which is the "two sources of truth" the constitution forbids.

**Cost, stated.** A `count(*)` per claim attempt. With a global cap of 100 and a bounded pending set
the count is an index-only scan over a small number of rows, and claims run at a handful per second
per worker. If it ever matters, the remediation is a maintained counter — which is a second source of
truth and therefore requires a real justification, not a hunch.

**Alternatives considered.** A per-worker share of the global cap (`cap / worker_count`) — no shared
counting at all, rejected because it under-utilizes the fleet whenever load is uneven and it breaks
entirely when a worker dies. A semaphore in Redis — forbidden; ownership-adjacent state outside
PostgreSQL.

### D-45 — Migrations are a gated one-shot step, and every process refuses to start on a schema mismatch

*Extends D-05.*

**Decision.** Migrations run in a **dedicated one-shot step** — a `migrate` service that the API and
workers `depends_on: service_completed_successfully` in compose, and a pre-deploy command on Render.
No long-running process ever runs `alembic upgrade head`. Every process reads the applied revision at
startup, compares it against the revision the code was built against, and **refuses to start** on a
mismatch, naming both revisions.

**Rationale.** Under D-05 as written, "migrations apply automatically on API start" while three
workers boot concurrently. That is a race on DDL: Alembic's version-table lock serializes the
*upgrade*, but concurrent `CREATE INDEX`/`ALTER TABLE` from multiple processes can deadlock, and a
partially applied deploy leaves a fleet where some processes have the new schema and some do not —
which is exactly the class of split-state this project exists to eliminate, reintroduced through the
deploy pipeline. Failing closed on mismatch is `I7` applied to schema version: **a process that
cannot be sure it agrees with the database must not execute steps.**

It also makes the Deployments page honest. Version skew across the fleet becomes a startup refusal
rather than a subtle behavioural difference between two workers resuming the same run.

**Alternatives considered.** Advisory-locking the migration inside the API's startup — works, but
still couples deploy ordering to process boot and hides a failed migration inside a health check.
Migration-on-first-request — worse in every respect.

### D-46 — Tool declarations are content-hashed, and a cross-version conflict fails that tool closed

*New. This closes an `I8` hazard.*

**Decision.** `register_tool` computes a `declaration_hash` over the safety-relevant fields (`safety`,
`naturally_idempotent`, `provider_accepts_key`, `has_reconcile_fn`, `default_policy`). The worker
upserts its declaration at startup. If an existing row carries a **different** hash, the conflict is
recorded with both `code_version`s and **that tool is refused for execution fleet-wide** until an
operator resolves it; every other tool keeps working. `TOOL_INTENT` continues to record the `safety`
actually applied, per call.

**Rationale.** The registry is a table and the declaration is code, so during a rolling deploy the
two can disagree — and the thing they disagree about is *the policy that resolves the uncertainty
window*. Concretely: a tool reclassified from `unsafe` to `retry_safe` between two builds means a
crash inside the uncertainty window resolves by **halting for review on one worker and re-executing
on another**, for the same tool, in the same fleet, non-deterministically. `I8` says uncertainty is
resolved by the tool's declared policy; if "the declared policy" is ambiguous, `I8` has no content.

Failing that tool closed is the fail-loud reading: a refusal names the conflict and the two versions,
where the alternative is a silent coin-flip on the most consequential decision in the system. Scoping
the refusal to the tool rather than the worker prevents one reclassification from taking the fleet
down, which would be a self-inflicted outage in the name of safety.

**Alternatives considered.** Last-writer-wins on the registry row — the silent coin-flip, rejected.
Code always wins, table is a pure projection — better, but two workers on different code still apply
different policies with nothing detecting it. Version the declaration and pin each run to the version
in force at submission — genuinely more precise and rejected as disproportionate: it adds a
per-run policy snapshot to solve a problem that a deploy-time refusal removes entirely.

### D-47 — Non-deterministic values are batched per step and flushed in the step's effect transaction

*Revises the per-call journaling implied by D-25 and the `NONDET_RECORDED` payload in the data model.*

**Decision.** `ctx.now()`, `ctx.random()`, and `ctx.new_id()` accumulate in an ordered in-memory
buffer for the current step. The buffer is written as **one** `NONDET_RECORDED` event whose payload
is an array of `{kind, call_ordinal, value}` entries, **in the same transaction** as that step's
`TOOL_INTENT` — or as `STEP_COMPLETED` when the step performs no side effect. Ordering is preserved by
`call_ordinal`, exactly as before.

**Rationale.** This exploits a property already established and then not used: `ctx.now()` and
`ctx.random()` have **no external effect**, so a crash before their journal write is safely
re-derivable — nothing in the world observed the discarded value. Durability is therefore required not
at the moment of the call but **before anything that depends on the value leaves the process**. The
only such thing is a side effect, and a side effect is already gated behind `TOOL_INTENT`. Putting the
batch in that same transaction means there is no interleaving in which an effect exists whose inputs
are unrecorded — including the case that actually matters, where `ctx.new_id()` feeds the idempotency
key, because the key's inputs and the intent commit atomically.

The saving is not cosmetic. An agent calling `ctx.now()` a few times per step across a 40-step run
generates hundreds of individual events, each one a synchronous round trip on the critical path, each
one competing for the same `runs` row lock that serializes appends. Batching collapses that to one
event per step. **Fewer round trips on the hot path, an order of magnitude less log volume, and the
invariant is preserved by construction rather than by care.**

**Alternatives considered.** Journal each call individually (the original) — simplest to reason about,
and its cost is paid on every step of every run forever. Buffer and flush at `STEP_COMPLETED` only —
wrong: a `new_id()` consumed by an idempotency key would be recorded *after* the effect it keyed.
Flush in a separate transaction immediately before the intent — correct but two commits where one
suffices, and it opens a window in which the batch is durable and the intent is not, which is a state
with no meaning.

### D-48 — `LEASE_RENEWED` is emitted at boundaries and on threshold breaches; renewal latency lives in telemetry

*Supersedes D-17's volume note.*

**Decision.** `LEASE_RENEWED` is appended on the **first renewal after a claim**, on any renewal whose
**latency exceeds a configured fraction of the lease** (the §12 warning sign), and on the **last
renewal before a terminal state**. Every renewal's latency is recorded in the telemetry path (D-49)
regardless. The emission policy is one configuration value, and setting it to `always` restores
per-renewal events for debugging.

**Rationale.** At a 1-second renewal interval with 100 concurrent runs, unconditional emission writes
**100 events per second of pure heartbeat**, which over a 30-minute sustained chaos run is roughly
180,000 renewal events against perhaps 40,000 events that describe what the agents actually did.
**Four out of five rows in the audit log would be heartbeat.** That inflates the table, every global
index, the WAL, and every cross-run query — and the earlier mitigation, hiding it in the UI, treated a
data-volume problem as a display problem.

The principled line is this: **`LEASE_RENEWED` is the only event type replay does not consume.** It
contributes nothing to reconstructing agent state; it is purely observability. Observability belongs
in the metrics path, where it is aggregated, and the audit log keeps the events that carry a decision
or a state transition. Emitting the boundary renewals and the slow ones keeps every renewal fact that
a human would ever want *per run* — "when did ownership begin", "did renewal ever get close to the
lease" — while the distribution stays complete in telemetry.

**Alternatives considered.** Uniform sampling (1 in N) — loses precisely the slow renewals that
matter, since they are rare by definition. A separate `lease_renewals` table — a second write per
renewal, so it saves the index cost and none of the write cost. Keeping everything and partitioning
the log by time — see D-52; that path destroys the schema's most important constraint.

### D-49 — A derived, rebuildable metrics rollup, computed off the hot path

*Partially supersedes D-30, which stands for correctness reads.*

**Decision.** Two tiers, and the boundary between them is explicit:

| Read | Source | Why |
|---|---|---|
| Duplicate-effect count, stranded runs, `needs_review` list, effect counts, **every chaos-report figure** | Live query against `tool_journal` / `run_events` | Correctness reads. Never cached, never rolled up. A stale zero on the duplicate counter is the single most damaging thing this product could display |
| Throughput series, run-state distribution over time, recovery and renewal histograms, replay overhead, fencing rate | `metrics_rollup` | Display-only time series |

`metrics_rollup` is keyed by `(bucket_start, bucket_seconds, metric, dimension)` and is maintained by
a **periodic job with a watermark** — it reads `run_events` above the last processed `(created_at, run_id, seq)`
and upserts buckets. It is **derived and rebuildable**: truncating it and replaying the log
reconstructs it exactly, and a `REBUILD` path exists and is tested. A BRIN index on
`run_events.created_at` supports both the rollup scan and any ad-hoc window query.

**Rationale.** Full aggregation over `run_events` per dashboard poll is fine on day one and untenable
after one chaos corpus: eight series over hundreds of thousands of rows, on every poll, from a landing
page that a reviewer may leave open. The rollup makes those reads O(buckets).

**The mechanism choice is the interesting part, and one option had to be rejected on correctness
grounds rather than cost.** A trigger-maintained rollup — `AFTER INSERT ON run_events` upserting the
current bucket — is the obvious implementation and is **actively harmful here**: every worker
appending an event would contend on the *same* rollup bucket row, which would serialize appends
**across runs that currently never contend at all**. It would convert the system's best property —
that the only lock on the append path is the run's own row — into a global write bottleneck, in
service of a sparkline. The periodic job has no hot-path cost, bounded staleness, and a rebuild story.

**Alternatives considered.** Trigger-maintained rollup — rejected above; recorded because it is the
first thing anyone would reach for. PostgreSQL materialized views with `REFRESH CONCURRENTLY` —
viable, rejected because refresh cost is opaque and a full refresh re-reads the whole log. TimescaleDB
continuous aggregates — the right tool, and an extension dependency this project does not need.
Computing series in the API and caching in Redis — a cache, non-authoritative, and unrebuildable.

### D-50 — One Redis firehose channel, demultiplexed in process

*Supersedes D-29's subscription topology. The bounded queue, drop policy, and backfill stand.*

**Decision.** Committed events are published to a single `anchor:events` channel. The API holds **one**
subscription and routes each message to the connected clients for that `run_id`, plus
`anchor:fleet` for fleet telemetry. No per-run channels, no pattern subscriptions.

**Rationale.** Per-run channels make subscribe and unsubscribe part of the request path, which
introduces a race with a name: a client connects, the API subscribes, and any event published in
between is lost — invisible unless someone notices a gap in `seq`, and the reason the snapshot-then-events
handshake exists is to paper over exactly that. One always-on subscription removes the race by
construction; the handshake then only has to handle reconnects. At this volume the "cost" — every
event reaching the API whether or not anyone is watching — is a few hundred small messages per second
to a process that is already connected.

**Alternatives considered.** Per-run channels — the original; correct only with careful
subscribe-before-snapshot ordering, and that ordering is a bug waiting for a refactor. Pattern
subscribe (`run:*`) — same volume as the firehose with more Redis-side matching. PostgreSQL
`LISTEN/NOTIFY` — no second system and transactional with the write, but it holds a dedicated
connection and caps payloads at 8 kB; recorded as the fallback if Redis is ever removed. **When the
web tier is scaled past one instance the firehose stays correct** — every instance sees every event and
routes to its own clients — which is a nice property to get for free.

### D-51 — A payload ceiling that dead-letters loudly rather than truncating silently

**Decision.** `core/events.append` rejects a payload above a configured ceiling (default 1 MiB) with
a typed `PayloadTooLargeError`. The step fails, retries do not help, the attempt cap dead-letters the
run, and the dead-letter reason names the event type and the measured size.

**Rationale.** `LLM_CALLED.response` is unbounded in principle, and JSONB plus TOAST will happily
store a 50 MB response — which then has to be read on **every** subsequent replay of that run,
turning one pathological step into a permanent tax on recovery time, which is a published number.
Truncation is the tempting fix and is forbidden: replay would reconstruct different messages than the
original execution, which is replay divergence — the exact failure `I6` exists to prevent, introduced
by a size optimization. So the only honest options are "store it" or "fail", and a bounded loud
failure beats an unbounded quiet cost.

**Alternatives considered.** Store large payloads externally with a content hash in the event — a real
design, and it adds an object store, a second durability domain, and a fetch on the replay path.
Compress in the application — TOAST already compresses; doing it again hides the size from the
ceiling check.

### D-52 — Only `run_id`-keyed partitioning is permissible; time-range partitioning `run_events` is forbidden

**Decision.** `run_events` is **not** partitioned. If it is ever partitioned, the partition key MUST
include `run_id`. **Range-partitioning by `created_at` is forbidden outright**, and this is recorded
here so that a future performance pass cannot arrive at it innocently.

**Rationale.** PostgreSQL requires every unique constraint on a partitioned table to contain the
partition key. Partitioning by `created_at` therefore forces the primary key to become
`(run_id, seq, created_at)` — which **does not enforce uniqueness of `(run_id, seq)`**. Two events
for one run with the same sequence number, landing in different time partitions, would both be
accepted. That single change would delete the constraint the specification calls the most important
one in the schema, break `I2`, and make duplicate appends silent — and it would look like a routine
time-series optimization in the diff.

`run_id` as the partition key keeps `(run_id, seq)` uniqueness intact (the key is contained in the
constraint) and keeps replay reads partition-pruned. It is also the remediation the specification
already names for the single-writer ceiling. It is nonetheless **not being done now**, because
partitioning one table on one host does not move the ceiling — the bottleneck is a single instance's
write path, not the table's structure — so it would add operational surface and buy a number nobody
measured. The honest position stays: measure the ceiling, publish it, and name `run_id` sharding as
the fix.

### D-53 — `now()`'s conservatism is documented, and renewal uses it too

**Decision.** Every lease read and write uses `now()` (transaction start). This includes the renewal
statement.

**Rationale.** A slow claim transaction sets `lease_expires_at` from the transaction's *start*, so the
lease effectively begins earlier than the commit and the real ownership window is shorter than the
configured one by the transaction's duration. **The error direction is toward earlier expiry, which is
safe**: a lease that expires slightly early causes a reclaim of a run nobody is progressing, while a
lease that expired slightly *late* would let two workers believe they own the same run — and only the
epoch would save it. Choosing the clock whose error is conservative, and writing down which direction
that is, is the difference between a safe default and a lucky one.

### D-54 — Cancelling a `pending` run is finalized by the API

**Decision.** `POST /api/runs/{id}/cancel` on a `pending` run finalizes it as `cancelled` immediately,
writing `RUN_CANCELLED` attributed to `operator` at the run's current epoch. On a `running` run it
sets `cancel_requested_at` and the owning worker finalizes at its next step boundary.

**Rationale.** A `pending` run has no owner, so "the worker checks the flag between steps" never
happens — under the original design a cancelled `pending` run would sit until some worker claimed it
purely in order to cancel it, which wastes a claim, an epoch increment, and a replay, and looks like a
bug in the runs list. A `pending` run is leaseless, so the same reasoning that makes the operator
resolution write safe (D-24) makes this safe: no worker can be racing a run nobody owns.

### D-55 — The model adapter is a protocol; only the stub ships

**Decision.** `ModelAdapter` is a protocol with one method, selected by configuration. `StubAdapter`
ships and is the default on every path — demo, chaos, and tests. A real adapter is additive, is
forbidden in demonstration mode, and is unreachable from any test.

**Rationale.** Deciding the *seam* now costs nothing and keeps the eventual adapter from becoming a
refactor; deciding the *provider* now would be scope the specification explicitly defers. The stub
also carries the demo's varied step durations, and the determinism boundary means the runtime cannot
tell a stub from a provider — which is the property that makes this seam safe to leave unfilled.

---

## 11. Addendum F intake — the deferred authoring backlog

`anchor-spec.md` Addendum F (§34–§36) names four items and one sequencing rule. The sequencing rule is
unambiguous and is honoured: *"Do not implement any part of this until the end product from phases 1–8
is working and demoed."* The four decisions below record how that rule is carried into this plan
without either smuggling the work into scope or losing it.

### D-56 — Addendum F is a backlog, not phase 10

**Decision.** Addendum F is recorded in [plan.md](./plan.md) under **"Deferred backlog — unscheduled"**,
a section that is deliberately *not* a phase, carries no phase number, no work-package numbers, no exit
gate, and no traceability row. Its items are not decomposed by `/speckit-tasks`.

**Rationale.** Constitution Principle VI gates work by phase, and the phase sequence is the mechanism
that keeps later-phase work from being pulled forward. Giving Addendum F a phase number would therefore
do the exact thing §36 forbids: place it *in the build order*, where "phase 10" reads as "after phase
9" rather than as "not scheduled." Phase 9 is already the stretch, and it is itself gated on phase 8;
a phase 10 would inherit that framing and acquire an implied commitment the source document explicitly
withholds. **A backlog section states the same content with the opposite default** — nothing in it is
scheduled until someone schedules it, and the plan's work-package count does not move.

**Alternatives considered.** *Phase 10* — rejected above. *Omit it entirely* — rejected: §36's
reasoning ("this makes writing agents for the runtime less error-prone, which is a different axis") is
the kind of thing that gets re-derived badly six months later, and the addendum exists precisely so the
idea isn't lost. *Fold it into the Cross-cutting workstreams table* — rejected: every workstream there
has a stated "when," and Addendum F's honest "when" is *unscheduled*, which would make it the one row
that lies.

### D-57 — The "demo agents as reference implementations" item is pulled forward into phase 5

**Decision.** §35's second item — the three §21.5 demo agents written well enough to serve as
reference implementations, with the long-run agent as the canonical worked example of the
already-done filter pattern — is **not deferred**. It becomes an acceptance criterion on the phase-5
work package that writes those agents (P5.7), and the README pointer to the long-run agent joins the
README workstream.

**Rationale.** This is the one item in Addendum F that is **zero added scope**, and deferring it costs
strictly more than doing it. The agents are written in phase 5 either way. §29.1 already imposes the
same bar for a different reason — they are §27.4's few-shot examples, so the generator's output quality
is bounded by their quality. The decisive argument is that the bar is **not retrofittable**: these
agents are also the chaos harness's workloads from phase 8 onward, so rewriting them afterward to read
better as documentation changes the system under test *after* the evidence was captured, and every
published chaos figure would then describe a build that no longer exists. **Improving a fixture
invalidates the measurement taken with it.** Writing them well once, at the point they are first
written, is the only ordering in which both properties hold.

This is not a violation of §36's sequencing rule. §36 defers work that "makes writing agents for the
runtime less error-prone"; it does not license writing phase-5 deliverables badly on the theory that
documentation quality is someone else's phase.

**Alternatives considered.** *Defer with the rest* — rejected on the invalidation argument above.
*Write a fourth, separate "reference" agent later* — rejected: it would drift from the three that
actually run, and a worked example that is not exercised by the chaos harness is a worked example
nobody has proven correct.

### D-58 — The `_template.py` scaffold, if ever built, is a registered no-op, not an inert file

**Decision.** Deferred, per §36. But the constraint it must satisfy is recorded **now**: a scaffold at
`anchor/runtime/agents/_template.py` lands inside the package that P2.3's AST determinism test walks
and that the phase-9 validator checks. If it is ever built it MUST be a **valid, registered, no-op
agent** — importable, passing the AST walk, returning a real `Done(...)` on its first invocation, with
its TODO markers in comments rather than in place of code. It MUST NOT be added as an inert file plus a
new exclusion in the AST test.

**Rationale.** The tempting implementation is a half-written skeleton with `TODO` where the branches
go. That file fails the AST walk and the validator, and the path of least resistance from there is to
exclude it — which **puts a hole in the determinism test for the sake of a documentation file**. The
AST walk is the enforcement mechanism for `I6` in agent code; an exclusion list on it is an exclusion
list on an invariant, and the first entry is always the one that seemed harmless. A scaffold that is
itself a working agent has no such cost: it demonstrates the four-step shape by *being* the four-step
shape, and it stays correct because the same tests that guard every other agent guard it.

Recording the constraint at intake rather than at build time is the point of the decision. The
deferral is only safe if the deferred thing cannot quietly weaken something when it eventually arrives.

**Alternatives considered.** *A `.py.txt` or `.md` template outside the package* — a reasonable
second choice, and acceptable if the no-op agent proves awkward; it trades executability for
inertness. Rejected as the default because a template that cannot be run is a template that is never
verified. *An excluded skeleton* — rejected above, and named explicitly so it is refused rather than
rediscovered.

### D-59 — The validator's ceiling is stated in the product, not only in the specification

**Decision.** §34's statement — the validator catches mechanical contract violations and **cannot**
catch wrong business logic, because no static analysis can verify intent it was never told — is
surfaced in the phase-9 authoring page itself, adjacent to the validation results, and in the
authoring documentation. It is added to [spec.md](./spec.md) as **FR-134** rather than left as
commentary here.

**Rationale.** This is a Principle VIII honesty requirement, not a nicety. A panel that reports
"6 checks passed" next to a draft is making a claim, and a developer will reasonably read that claim as
"this agent is correct." It is not: the two most common authoring mistakes — a loop that filters on the
wrong key, and a terminal branch that is unreachable for the inputs that actually arrive — are business
logic and are invisible to every one of the six checks. An interface that renders a partial guarantee
as a complete one is exactly what §6.1 of the standard and constitution Principle VIII forbid, and it
is the same failure mode as an optimistic state rendered as confirmed.

It also costs nothing to be right about. The pre-registration checklist of D-56's sibling item lives in
[contracts/agent-contract.md](./contracts/agent-contract.md) and is precisely the list of things the
validator cannot check — so the honest rendering is not a disclaimer, it is a **next step**: *these six
mechanical checks passed; these four judgements are yours.*

**Alternatives considered.** *Leave it in the docs only* — rejected: the person who most needs the
statement is looking at the validation panel, not at the README. *Weaken the "passed" language without
explaining why* — rejected: vagueness is not honesty, and it forfeits the teaching opportunity that
makes the validator worth building at all (P9.2).
