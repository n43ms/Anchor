# Feature Specification: Anchor — Durable Execution Runtime for AI Agents

**Feature Branch**: `001-anchor-durable-execution-runtime`

**Created**: 2026-07-31

**Status**: Draft

**Input**: User description: "use @anchor-spec.md to understand and develop a holistic plan for this
project. every field and every phase of the project should be considered, and nothing should be left
out."

**Source of intent**: [`anchor-spec.md`](../../anchor-spec.md) — the standalone product and
engineering specification (§0–§36 including Addenda A–F). This document does not replace it and does
not restate it. It is the Spec Kit projection of that document: user journeys, numbered functional
requirements, entities, and measurable success criteria, so that `/speckit-plan`, `/speckit-tasks`,
and `/speckit-analyze` have traceable anchors. **Where this document and `anchor-spec.md` differ on
intent, `anchor-spec.md` governs**, subject to the precedence order in
[the constitution](../../.specify/memory/constitution.md) — in particular §31 governs any deployment
capability conflict, and Addendum C §25 supersedes §6.1's first subtlety and §10.3's recovery figure.

**Governing conduct**: the constitution (v1.0.0). Its eight invariants `I1`–`I8` are the acceptance
bar for every story below.

---

## User Scenarios & Testing *(mandatory)*

The product has three distinct readers, and conflating them is the most likely specification error.
A **reviewer** lands cold and must be convinced in under a minute. An **operator** watches runs
execute and intervenes. A **developer** wants to run their own agent on the runtime. Stories are
labelled with the reader they serve.

### User Story 1 - A run survives the death of the machine executing it (Priority: P1)

*Reader: operator. Build phases 1–3.*

An agent run is submitted. A worker claims it and executes steps, appending every step to an
append-only log in PostgreSQL rather than holding state in process memory. The worker is killed
mid-run. Its lease expires. Another worker claims the run, replays the log to reconstruct the exact
context, and continues from the step where the first worker stopped — with no human intervention and
no manual replay.

**Why this priority**: this is the product. Every other story is either an elaboration of it, a proof
of it, or a surface over it. Section 20 of the source spec is explicit: until a worker dies mid-run
and resumes correctly, nothing else in the system means anything.

**Independent Test**: submit a run of the demo agent, `kill -9` the owning worker at a known step,
and assert from the event log alone that a different worker id claimed the run, that
`REPLAY_COMPLETED` records the expected number of replayed steps, and that execution continued from
the correct step index with the accumulated context intact.

**Acceptance Scenarios**:

1. **Given** a submitted run and an idle fleet, **When** a worker polls for work, **Then** exactly
   one worker claims it, the run's epoch increments, its lease is set from the database clock, and a
   `RUN_CLAIMED` event is appended with reason `initial` — all in one transaction.
2. **Given** a run executing on worker A, **When** worker A is hard-killed mid-step, **Then** no
   further events are appended for that run until the lease expires, and the run is visibly
   `orphaned` rather than silently stalled.
3. **Given** an expired lease, **When** any worker polls, **Then** it claims the run with reason
   `reclaimed_after_lease_expiry`, the epoch increments again, and a `RUN_CLAIMED` event records the
   new owner.
4. **Given** a reclaimed run, **When** the new owner replays the log, **Then** the reconstructed
   context contains every prior message, the index of the last completed step, every journaled tool
   result keyed by idempotency key, and every journaled non-deterministic value.
5. **Given** a completed replay, **When** execution resumes, **Then** steps already recorded as
   complete are not re-executed, and the run reaches a terminal state exactly as if no kill had
   occurred.
6. **Given** two workers polling simultaneously with one available run, **When** both attempt to
   claim, **Then** exactly one succeeds and the other receives no row and backs off with jitter.

---

### User Story 2 - A stalled-but-alive worker cannot corrupt a run (Priority: P1)

*Reader: operator. Build phase 4.*

A worker is not dead but stalled — a long garbage-collection pause, a network partition, a suspended
VM. Its lease expires and another worker takes over. The original then wakes up still believing it
owns the run and attempts to write. The database rejects the write because the worker's epoch is
below the run's current epoch. The stale worker observes that it has been fenced, discards all
in-memory state, writes nothing further, and returns to the idle pool.

**Why this priority**: split-brain is the failure mode that makes durable execution hard rather than
merely tedious, and the fencing token is the mechanism that makes it structurally impossible. Item 6
of the source spec's definition of done — being able to whiteboard this cold — is stated there as
"the real bar."

**Independent Test**: construct a zombie worker in a test by holding a stale epoch across a
simulated stall, allow a second worker to reclaim, then attempt an append with the stale epoch and
assert the database raises the dedicated `SQLSTATE`, that no partial write landed, and that the
fenced worker performs no subsequent write of any kind.

**Acceptance Scenarios**:

1. **Given** a run at epoch 5 owned by worker A, **When** worker B reclaims it after lease expiry,
   **Then** the run's epoch becomes 6 and worker B's writes are accepted.
2. **Given** worker A still holding epoch 5, **When** it attempts to append any event, **Then** the
   database rejects the insert, no row is written, and the error surfaces to worker A as a typed
   `LeaseFencedError`.
3. **Given** a fenced worker, **When** it handles the rejection, **Then** it writes nothing further —
   including no error event through that run's log — does not retry, discards in-memory state, and
   returns to the idle pool.
4. **Given** a fenced worker whose lease renewal was rejected on a background task, **When** the
   renewer cancels the run's execution task, **Then** no write occurs after cancellation, verified
   by asserting the log's final sequence number is unchanged.
5. **Given** a worker whose event loop is blocked entirely, **When** the lease elapses, **Then** the
   run is reclaimed — the background renewer MUST NOT be able to signal liveness that outlives a
   stalled process.

---

### User Story 3 - No tool executes twice, and ambiguity is surfaced rather than guessed (Priority: P1)

*Reader: operator and developer. Build phase 5.*

Every side-effecting call is wrapped in a two-phase journal: intent recorded with a deterministic
idempotency key, then execution, then result recorded under the same key. On replay, the worker
looks the key up before invoking anything. A completed key returns the recorded result and the step
is marked skipped-on-replay. An absent key executes normally. **A key with an intent but no result
is the uncertainty window**, and it is resolved by the tool's declared policy — never by a guess.

**Why this priority**: this is the guarantee that lets an agent be trusted with a refund. It is also
the one the product's headline number measures.

**Independent Test**: run the demo agent to completion, then replay its log and assert that every
`send_email` idempotency key carries at most one result and that the `demo_effects` table holds
exactly one row per logical side effect. Separately, inject a crash between `TOOL_INTENT` and
`TOOL_RESULT` for one tool of each declared category and assert the documented resolution for each.

**Acceptance Scenarios**:

1. **Given** a tool call about to execute, **When** the runtime prepares it, **Then** a
   `TOOL_INTENT` event carrying the idempotency key is appended and committed **before** the tool is
   invoked.
2. **Given** a key whose intent and result are both journaled, **When** the step is replayed,
   **Then** the tool is not invoked, the recorded result is returned, and a
   `STEP_SKIPPED_ON_REPLAY` marker is emitted so the console can render it distinctly.
3. **Given** structurally identical arguments serialized in different key orders, **When** the
   idempotency key is derived, **Then** the key is identical — canonical serialization makes
   argument ordering, nesting traversal, and numeric formatting irrelevant.
4. **Given** an intent with no result on a `retry_safe` tool, **When** the run resumes, **Then** the
   tool is re-executed with the idempotency key passed through to the provider for deduplication.
5. **Given** an intent with no result on a `reconcilable` tool, **When** the run resumes, **Then**
   the reconciliation query runs and execution branches on its answer, and the resolution applied is
   recorded on the journal row.
6. **Given** an intent with no result on an `unsafe` tool, **When** the run resumes, **Then** the run
   is set to `needs_review`, halts, and appears on the Needs review page with the specific ambiguous
   call, its declared policy, and the available resolution actions.
7. **Given** any registered tool, **When** registration is attempted without a declared safety
   category, **Then** registration fails.

---

### User Story 4 - Behaviour under load and repeated failure is predictable (Priority: P2)

*Reader: operator. Build phase 6.*

Runs queue rather than overwhelm the fleet. A transiently failing step is retried with exponential
backoff and jitter up to a per-step cap. A poisonous run stops retrying, lands in a dead-letter view,
and does not block anything else. A run can be cancelled cooperatively. A saturated fleet leaves new
runs `pending` rather than degrading every run uniformly.

**Why this priority**: it is what separates a demonstration from something that could be deployed,
and every mechanism here is cheap once the log and the lease exist.

**Independent Test**: submit more runs than the global concurrency cap permits and assert the excess
stay `pending` with no worker exceeding its per-worker limit; separately, register a tool that fails
deterministically and assert the run reaches `failed` after exactly `max_attempts_per_step` attempts
with backoff intervals inside the jittered bounds.

**Acceptance Scenarios**:

1. **Given** a step that fails transiently, **When** the attempt count is below the cap, **Then** a
   `STEP_FAILED` event is appended and the step is retried after exponential backoff with jitter.
2. **Given** a step that has exhausted its attempts, **When** it fails again, **Then** `RUN_FAILED`
   is appended, the run's status becomes `failed`, and it appears in the dead-letter view with the
   failing step highlighted.
3. **Given** a worker at its configured concurrency limit, **When** it polls, **Then** it does not
   claim additional work and sleeps briefly instead.
4. **Given** a run with its cancellation flag set, **When** the worker reaches a step boundary,
   **Then** the run finalizes as `cancelled` and the worker exits the run cleanly. Cancellation is
   never checked mid-step.
5. **Given** the database is unreachable, **When** a worker attempts to claim or append, **Then**
   nothing executes, the worker backs off and retries, and no side effect occurs without a durable
   record.
6. **Given** Redis is unreachable, **When** the console is open, **Then** live push degrades to
   polling and execution is entirely unaffected.
7. **Given** a run submitted twice with the same client request key, **When** the second submission
   arrives, **Then** it is deduplicated to the same run rather than creating a second one.

---

### User Story 5 - Any run is completely auditable from the console (Priority: P2)

*Reader: operator. Build phase 7.*

For any run, the operator can see every step, every input, every output, every retry, every
ownership change, and which worker executed each step. The run detail view makes the handoff between
workers unmissable: stacked per-worker bars in each worker's identity hue, a handoff divider naming
the expired lease, per-segment logs attributed to the worker that wrote them, and a thread view whose
markers distinguish an ordinary step from an executed side effect from a confirmed non-duplicate.

**Why this priority**: auditability is the third of the four product guarantees, and the console is
the only channel through which the other guarantees become observable.

**Independent Test**: render the run detail component against recorded mock data for a run with two
workers, one handoff, five steps and zero duplicate side effects, and assert the handoff divider, the
per-worker hues, the ghosted replayed segments, and the footer's suppressed recovery figure all
appear as specified — with no live backend.

**Acceptance Scenarios**:

1. **Given** a run that changed hands, **When** the run detail is opened, **Then** each worker's
   segment renders in that worker's identity hue and the handoff divider reads
   `{worker_id} lease expired` and is never collapsed or hidden.
2. **Given** replayed steps, **When** the timeline renders, **Then** they are ghosted and executed
   steps are solid, and the distinction remains legible with the display in grayscale.
3. **Given** a run with zero handoffs, **When** the footer renders, **Then** the recovery figure is
   suppressed entirely rather than displayed as `0.0s`.
4. **Given** any run state, **When** a status is displayed anywhere, **Then** it carries an icon and
   a text label in addition to color — no bare colored dots.
5. **Given** a currently-orphaned run where no segment is the current owner, **When** the component
   renders, **Then** it shows the orphaned gap with a pulsing hairline and a lease-expiry countdown
   rather than an error or an empty state.
6. **Given** a fencing event, **When** the timeline renders, **Then** it appears as a full-height
   labelled marker on the track showing both the stale and current epoch, never as a buried log line.
7. **Given** a dropped WebSocket, **When** the console is open, **Then** staleness is stated on
   screen and data is not presented as live.

---

### User Story 6 - The guarantee is measured continuously, not asserted (Priority: P2)

*Reader: reviewer. Build phase 8.*

A chaos harness launches workers and runs, kills workers randomly, injects latency, stalls, tool
failures and crashes inside the uncertainty window, and runs for a sustained period. It asserts five
invariants continuously and emits a permanent report. Every past report is preserved and inspectable,
so the claim becomes an accumulating body of evidence rather than one successful demo.

**Why this priority**: it is the answer to "how do you know it works", and the source spec is
explicit that a number which regenerates is more credible than a number that was true once.

**Independent Test**: run the harness for a bounded duration against a local fleet and assert all
five invariant checks pass, that a report row is written with the measured distributions, and that
the reported numbers are read back by the metrics endpoint rather than hardcoded anywhere.

**Acceptance Scenarios**:

1. **Given** a sustained chaos run, **When** the harness completes, **Then** every idempotency key in
   the window carries at most one recorded result.
2. **Given** a sustained chaos run, **When** the log is audited, **Then** sequence numbers within
   every run are strictly increasing with no duplicates and no gaps.
3. **Given** a sustained chaos run, **When** events are grouped by run and epoch, **Then** no epoch
   carries events from two different worker ids.
4. **Given** a sustained chaos run, **When** it ends, **Then** every submitted run has reached a
   terminal state within the bounded time — nothing is stranded.
5. **Given** any completed run, **When** its log is replayed, **Then** the reconstructed final state
   is identical to the recorded final state.
6. **Given** a completed chaos run, **When** its report is stored, **Then** it is immutable in every
   deployment mode and remains visible in chaos history permanently.
7. **Given** a published recovery figure, **When** it is displayed anywhere, **Then** the profile and
   lease duration it was measured under are displayed with it.

---

### User Story 7 - A cold reviewer is convinced in under a minute (Priority: P2)

*Reader: reviewer. Build phase 8, after the chaos console.*

A reviewer arrives at the deployed URL with no context, no account, and no intention of reading. A
live status strip proves the system is running. One click submits a real run. The timeline populates
inline. A highlighted control offers to kill the worker executing step 6. The timeline stalls
visibly with a lease countdown, then a new worker id appears, the prior steps are marked as replayed
rather than re-executed, and a line of copy states the conclusion outright.

**Why this priority**: the engineering is worthless if nobody reaches it. This story gates whether
any of the others are ever evaluated.

**Independent Test**: in a fresh private window against the deployed instance, complete the four-step
guided sequence without scrolling past the first viewport, without an account, and without navigating
away — then confirm from the fleet page that the killed worker really was killed and has respawned.

**Acceptance Scenarios**:

1. **Given** a first visit, **When** the landing page loads, **Then** the live status strip shows
   worker count, run count and duplicate-effect count read from the real health and metrics
   endpoints, and reports degradation honestly when the fleet is degraded.
2. **Given** the guided demo, **When** the reviewer clicks once, **Then** a real run is submitted
   with no form, no options and no modal, and its timeline appears inline already populating.
3. **Given** a run mid-execution, **When** the kill control is used, **Then** it calls the real kill
   endpoint — not a simulation — and the interface says so.
4. **Given** the kill, **When** the lease is expiring, **Then** the stall is shown with a countdown
   and labelled `orphaned — lease expiring` rather than smoothed over or hidden.
5. **Given** the handoff, **When** the new worker resumes, **Then** the replayed steps are visually
   distinct and one sentence of copy states that the tool calls in them did not run a second time.
6. **Given** the evidence band, **When** it renders, **Then** the hero figure is the duplicate count
   generated by the harness with its timestamp, and no figure on the page is hardcoded.
7. **Given** a reviewer with `prefers-reduced-motion` set, **When** they complete the sequence,
   **Then** no information is lost — the explainer falls back to a labelled static frame and the
   orphaned countdown remains as changing text.
8. **Given** a visitor who kills every worker, **When** they wait seconds, **Then** the fleet has
   self-healed to its full complement.

---

### User Story 8 - A developer runs their own agent on Anchor (Priority: P3)

*Reader: developer. Spans phases; documented once the contract is stable.*

A developer clones the repository, brings the stack up with one command, writes an agent function
against the step-context contract, writes plain tool functions, declares each tool's safety
category, registers the agent, rebuilds, submits a run, and then kills a worker to watch their own
agent resume. They write zero durability code.

**Why this priority**: it is the difference between a project that demonstrates a capability and a
tool that has one, and it is the section a reviewer reads to answer "could I actually use this?"

**Independent Test**: from a clean clone on a machine that has never run the project, follow the
eight-step quickstart verbatim, by someone other than the author, and reach a resumed run of a
newly-authored agent.

**Acceptance Scenarios**:

1. **Given** a clean clone, **When** `docker compose up` runs, **Then** PostgreSQL, Redis, the API
   and three or more workers come up with no configuration required and the console is reachable.
2. **Given** an agent function, **When** it is invoked by the runtime, **Then** it receives
   reconstructed state through the step context and returns exactly one action — a tool call, a model
   call, or done.
3. **Given** agent code that references the clock, a random source, or an id generator directly,
   **When** the test suite runs, **Then** it fails and names the offending module.
4. **Given** a tool registered without a safety category, **When** registration runs, **Then** it
   fails with a message that forces the category decision.
5. **Given** a loop expressed as a function of journaled history, **When** the run is interrupted
   repeatedly, **Then** progress is preserved without the agent tracking it — for example, already
   emailed recipients are not emailed again.

---

### User Story 9 - The agent contract is legible without a clone (Priority: P3, stretch)

*Reader: reviewer and developer. Build phase 9 — optional, only after phase 8.*

A console page carries an editor preloaded with the agent contract and the demo agents as worked
examples, a validator that statically rejects contract violations with messages that teach the
invariant, and an optional model-backed draft generator whose output is always routed through the
validator. On the public instance the page authors and validates but cannot execute, and it states
that mode in its header at all times.

**Why this priority**: it proves nothing the runtime does not already prove. It is strictly additive
and must not consume hours that phases 4 and 5 need.

**Independent Test**: on a public-mode instance, submit a draft that calls `datetime.now()` and
assert the validator rejects it with a message naming the step-context replacement; then assert the
register endpoint returns 404 rather than 401 or 403.

**Acceptance Scenarios**:

1. **Given** a draft referencing `datetime`, `time`, `random` or `uuid`, **When** validation runs,
   **Then** it is rejected with the line number and the step-context call that replaces it.
2. **Given** a draft returning an unrecognised action shape, module-level mutable state, an
   unregistered tool name, a tool with no safety declaration, or unbounded self-recursion, **When**
   validation runs, **Then** each is rejected with its own specific message.
3. **Given** a generated draft, **When** it reaches the editor, **Then** validation has already run
   and any violations are already marked.
4. **Given** no model API key configured, **When** the page loads, **Then** the editor and validator
   work and the generate control is disabled with a plain statement of why.
5. **Given** demonstration mode, **When** the register route is requested, **Then** it returns 404
   because the route is not mounted, and no import path in the API package reaches registry-mutation
   code.

---

### Edge Cases

Every row of the source spec's §9 failure matrix is an edge case with a required test. Restated as
questions:

- What happens when a worker is killed between `TOOL_INTENT` and `TOOL_RESULT`? → the uncertainty
  window, resolved by the tool's declared policy; never a guess.
- What happens when a worker stalls for longer than its lease but is not dead? → its next write is
  rejected by epoch; it discards state and withdraws silently.
- What happens when two workers race for the same run? → structurally impossible; one locking
  transaction that skips rows locked elsewhere.
- What happens when a duplicate `(run_id, seq)` is appended? → rejected by the unique constraint,
  loudly, not silently overwritten.
- What happens when an idempotency key differs across replay? → prevented by canonical
  serialization; if it ever occurs, the invariant checker catches it.
- What happens when agent code calls the clock directly? → replay diverges, which is why the
  contract forbids it and a test enforces the ban.
- What happens when the database is unavailable? → nothing executes. Fail closed, by design.
- What happens when Redis is unavailable? → the console loses live push and polls. Execution is
  unaffected.
- What happens when worker clocks disagree? → irrelevant; expiry is evaluated on the database clock.
- What happens when a WebSocket client is too slow to keep up? → dropped past a buffer threshold, and
  able to resubscribe and backfill from the log.
- What happens when the fleet is saturated? → new runs stay `pending`; admission control prevents
  overload rather than degrading everything uniformly.
- What happens when a worker registers and then dies immediately? → detected via stale `last_seen`
  and surfaced in the fleet view.
- What happens when a step runs longer than the lease duration? → nothing; the background renewer
  extends the lease independently of step progress.
- What happens when a step exceeds its step timeout? → the step fails, the renewer stops, and the
  lease lapses so the run is reclaimed rather than held.
- What happens when an operator sets the lease equal to the renewal interval? → the edit is
  rejected with the violated relationship named. The fleet is never reconfigured into self-fencing.
- What happens when a visitor kills every worker on the public instance? → they respawn within
  seconds; the kill endpoint is rate-limited only so the fleet view stays readable.
- What happens when a chaos run uses more than three workers? → identity is direct-labelled and
  color falls back to emphasis rather than extending the validated three-hue set.
- What happens when no chaos report exists yet? → the evidence badge is absent rather than showing a
  placeholder.

---

## Requirements *(mandatory)*

### Functional Requirements

**Run submission and admission**

- **FR-001**: System MUST accept a run submission carrying an agent type and an input payload, and
  MUST return a run identifier.
- **FR-002**: System MUST deduplicate submissions on a client-supplied request key, returning the
  existing run rather than creating a second one.
- **FR-003**: System MUST enforce a fleet-wide global concurrency cap **inside the claim transaction**,
  leaving excess runs `pending` rather than rejecting their submission. The API MUST report the cap
  and the current running count but MUST NOT refuse a submission because the fleet is saturated.
- **FR-004**: System MUST enforce a per-worker concurrency limit, checked by the worker before it
  attempts to claim.
- **FR-005**: System MUST append a `RUN_SUBMITTED` event on acceptance, so that even submission is
  recoverable from the log.
- **FR-006**: System MUST rate-limit submission by IP address and cap demo runs per hour in
  demonstration mode.

**Claiming, leasing, and ownership**

- **FR-007**: System MUST claim a run by selecting one eligible row — `pending`, or `running` with an
  expired lease — ordered by priority then creation time, under row-level locking that skips rows
  locked by other transactions, limited to one row.
- **FR-008**: System MUST perform the claim, the epoch increment, the owner assignment, the lease
  extension, the status transition and the `RUN_CLAIMED` append **in one transaction**.
- **FR-009**: System MUST handle new runs and expired-lease runs in a single claim statement, never
  as two queries.
- **FR-010**: System MUST evaluate lease expiry against the database clock exclusively.
- **FR-011**: System MUST record on `RUN_CLAIMED` whether the claim was `initial` or
  `reclaimed_after_lease_expiry`.
- **FR-012**: System MUST extend the lease from a concurrent renewer on its own timer, independent
  of step progress, and MUST NOT emit any liveness signal other than lease extension.
- **FR-013**: System MUST stop renewing when a step exceeds its step timeout, so a worker that is no
  longer progressing lapses its lease.
- **FR-014**: System MUST back off with jitter when no run is available, so idle workers do not
  synchronize into a polling convoy.

**Fencing**

- **FR-015**: System MUST carry a monotonically increasing epoch on every run, incremented on every
  claim.
- **FR-016**: System MUST stamp every event with the writing worker's epoch.
- **FR-017**: System MUST reject, **in the database**, any event whose epoch is below the run's
  current epoch, via a trigger raising a dedicated `SQLSTATE`.
- **FR-018**: System MUST map that rejection to a typed fencing error distinguishable from every
  other failure.
- **FR-019**: System MUST, on fencing, discard in-memory state, write nothing further through that
  run — including no error event — perform no retry, and return the worker to the idle pool.
- **FR-020**: System MUST append a `WORKER_FENCED` event from the *surviving* writer's perspective
  where the fencing is observable, so the console can render the marker.
- **FR-021**: System MUST cancel the run's execution task when the renewer detects fencing, and MUST
  guarantee no write follows that cancellation.

**The log**

- **FR-022**: System MUST store all run history as append-only events; events MUST never be updated
  or deleted.
- **FR-023**: System MUST enforce uniqueness of `(run_id, seq)` as a database constraint.
- **FR-024**: System MUST allocate `seq` from a per-run counter incremented in the same transaction
  as the append, so allocation is uncontended and a rollback leaves no gap.
- **FR-025**: System MUST support the full event vocabulary: `RUN_SUBMITTED`, `RUN_CLAIMED`,
  `REPLAY_COMPLETED`, `STEP_STARTED`, `LLM_CALLED`, `TOOL_INTENT`, `TOOL_RESULT`,
  `NONDET_RECORDED`, `STEP_COMPLETED`, `STEP_SKIPPED_ON_REPLAY`, `STEP_FAILED`, `LEASE_RENEWED`,
  `WORKER_FENCED`, `RUN_COMPLETED`, `RUN_FAILED`, `RUN_CANCELLED`, `RUN_NEEDS_REVIEW`.
- **FR-026**: System MUST expose the raw log per run, paginated, and globally, filterable by event
  type, worker, epoch and time range.

**Replay**

- **FR-027**: System MUST reconstruct in-memory context solely by reading the log in sequence order.
- **FR-028**: System MUST reconstruct accumulated messages and agent state, the index of the last
  completed step, every journaled tool result keyed by idempotency key, and every journaled
  non-deterministic value.
- **FR-029**: System MUST record the number of steps replayed and emit a `REPLAY_COMPLETED` marker so
  replayed steps are distinguishable from freshly executed ones.
- **FR-030**: System MUST produce an identical final state when a completed run's log is replayed.

**The determinism boundary**

- **FR-031**: System MUST expose journaled time, randomness and identifier generation to agent code
  through the step context, recording them as `NONDET_RECORDED` with a per-step call ordinal. Values
  MAY be batched into one event per step, but that event MUST be committed **no later than the
  transaction that records the step's `TOOL_INTENT`**, so no side effect can exist whose
  non-deterministic inputs are unrecorded.
- **FR-032**: System MUST return the recorded value on replay for every non-deterministic call rather
  than re-deriving it.
- **FR-033**: System MUST name identifier generation separately from randomness in both the API and
  the log, because an identifier differing across replay is the specific failure that defeats
  deduplication.
- **FR-034**: System MUST journal model completions and return the recorded completion on replay
  without calling any provider.
- **FR-035**: System MUST fail the test suite if any module under the agents package references the
  clock, the time module, a random source or an identifier generator directly.
- **FR-036**: System MUST stub model calls by default in the demo path, in chaos runs and in tests,
  and MUST state on the page that they are stubbed.

**The idempotency journal**

- **FR-037**: System MUST derive the idempotency key from the run id, step index, action name and a
  canonical serialization of the arguments.
- **FR-038**: System MUST produce identical keys for structurally identical arguments regardless of
  mapping key order, nesting traversal order or numeric formatting.
- **FR-039**: System MUST append and commit `TOOL_INTENT` before invoking any side-effecting tool.
- **FR-040**: System MUST append `TOOL_RESULT` under the same key after execution.
- **FR-041**: System MUST enforce uniqueness of the idempotency key in the database, with exactly one
  intent row per key.
- **FR-042**: System MUST represent result-absent as a distinct, queryable state via a nullable
  result column.
- **FR-043**: System MUST skip execution and return the recorded result when a key already carries
  one, emitting `STEP_SKIPPED_ON_REPLAY`.
- **FR-044**: System MUST record which uncertainty policy was applied when the window was entered.

**Uncertainty policies**

- **FR-045**: System MUST require every registered tool to declare a safety category of
  `retry_safe`, `reconcilable` or `unsafe`, and MUST refuse registration otherwise.
- **FR-046**: System MUST require a reconciliation function for every `reconcilable` tool.
- **FR-047**: System MUST re-execute a `retry_safe` tool with the idempotency key passed through to
  the provider.
- **FR-048**: System MUST run the reconciliation query for a `reconcilable` tool and branch on its
  result.
- **FR-049**: System MUST set the run to `needs_review`, halt it, and surface the ambiguous call for
  an `unsafe` tool — and MUST NOT assume either success or failure.
- **FR-050**: System MUST expose a resolution action for a `needs_review` run, scoped to demo runs in
  demonstration mode.

**Retry, dead-lettering, cancellation**

- **FR-051**: System MUST retry at step granularity, never at run granularity.
- **FR-052**: System MUST apply exponential backoff with jitter, bounded by a cap.
- **FR-053**: System MUST stop retrying at a per-step attempt cap, append `RUN_FAILED`, set status
  `failed`, and place the run in the dead-letter view. The attempt count MUST be derived from the log
  so that the cap survives a worker handoff (see FR-130).
- **FR-054**: System MUST check a cooperative cancellation flag between steps and never mid-step, and
  MUST finalize as `cancelled`.
- **FR-055**: System MUST bound every external call with a timeout.

**Failing closed**

- **FR-056**: System MUST NOT execute any step when the database is unreachable; workers back off and
  retry.
- **FR-057**: System MUST NOT allow any side effect to occur without a preceding committed journaled
  intent.
- **FR-058**: System MUST treat Redis as non-authoritative — never lease state, never ownership — and
  MUST continue executing correctly when Redis is unavailable.

**Configuration**

- **FR-059**: System MUST hold lease duration, renewal interval, step timeout, retry limits and
  concurrency caps in one configuration module, with no such constant hardcoded elsewhere.
- **FR-060**: System MUST assert `lease_duration >= 4 × renewal_interval`,
  `margin == lease_duration − renewal_interval` and `step_timeout > 0` before accepting any work,
  and MUST refuse to start naming the violated relationship and the offending values.
- **FR-061**: System MUST provide two named profiles — demo/chaos and production — and MUST report
  the active profile alongside any published measurement.
- **FR-062**: System MUST allow lease duration, renewal interval, step timeout, retry caps and
  concurrency caps to be edited live in local mode without a redeploy.
- **FR-063**: System MUST re-run the startup assertion on every applied configuration change and
  **reject the change**, never the fleet.
- **FR-064**: System MUST NOT permit configuration editing in demonstration mode.

**Worker fleet**

- **FR-065**: System MUST self-register every worker with hostname, process id, start time, capacity
  and code version, and MUST refresh a last-seen timestamp.
- **FR-066**: System MUST expose fleet state including current run count, uptime, last heartbeat age
  and code version.
- **FR-067**: System MUST detect a worker that registered but never heartbeated, via a stale
  last-seen value.
- **FR-068**: System MUST expose a kill endpoint that hard-exits a worker process, presented as a
  first-class product feature.
- **FR-069**: System MUST respawn killed workers automatically so the fleet self-heals.
- **FR-070**: System MUST run three or more always-on workers in every deployment, local and hosted.

**Observability**

- **FR-071**: System MUST expose run state distribution over time, step throughput per worker and in
  aggregate, recovery latency as a distribution, replay overhead, fencing rate, uncertainty-window
  entries by policy applied, lease renewal latency, and dead-letter volume with failure reasons.
- **FR-072**: System MUST expose a health endpoint reporting database reachability, fleet size and
  lag.
- **FR-073**: System MUST stream run events and fleet state over WebSocket channels, with backfill
  from the log on resubscribe.
- **FR-074**: System MUST drop a WebSocket client that exceeds a buffer threshold rather than growing
  a buffer without bound.

**Chaos harness**

- **FR-075**: System MUST launch a configured number of workers and submit a configured number of
  runs with a deliberate mix of step counts, tool types and durations.
- **FR-076**: System MUST kill workers randomly at a configurable rate, at random points in a run.
- **FR-077**: System MUST inject artificial latency and simulated stalls specifically to trigger the
  fencing path.
- **FR-078**: System MUST inject tool failures at a configurable rate to exercise retry and
  dead-lettering.
- **FR-079**: System MUST inject crashes inside the uncertainty window to exercise every declared
  policy.
- **FR-080**: System MUST run continuously for a sustained period, not a single pass.
- **FR-081**: System MUST record every injected failure with its type, target worker, timestamp and
  affected run ids.
- **FR-082**: System MUST assert all five invariants and MUST produce a permanent report containing
  the duplicate-effect count, stranded-run count, recovery distribution and replay overhead.
- **FR-083**: System MUST preserve every past report permanently and MUST NOT permit its deletion or
  alteration in any deployment mode.

**Console**

- **FR-084**: System MUST present a persistent left sidebar with a workspace slot, seven grouped
  sections, and a docs link pinned at the bottom.
- **FR-085**: System MUST provide the pages of the canonical inventory: Dashboard; All runs, Run
  detail, Needs review; Fleet, Deployments; Chaos console, Chaos history; Tool registry, Test run;
  Metrics, Logs; Environment.
- **FR-086**: System MUST surface `needs_review` runs on their own page, not only as a filter.
- **FR-087**: System MUST NOT ship a conditional page as an empty shell — Scheduled, API keys and
  Webhooks are absent unless built.
- **FR-088**: System MUST render the run detail as stacked per-worker bars with per-segment logs,
  handoff dividers, a reusable thread view with a compact mode, the replayed-step encoding, the raw
  event log, effect counters and a kill control targeting the current owner.
- **FR-089**: System MUST render the owning worker id on every timeline segment, moving the label to
  a continuous rail rather than clipping it.
- **FR-090**: System MUST distinguish tool calls from model calls by shape, not only by hue.
- **FR-091**: System MUST render every status as icon plus label plus color.
- **FR-092**: System MUST render exactly one hero figure per view, MUST NOT use a dual-axis chart,
  MUST provide a table view for every chart, and MUST provide a legend for every chart with two or
  more series.
- **FR-093**: System MUST honor `prefers-reduced-motion` without losing information.
- **FR-094**: System MUST define both dark and light token sets with no hardcoded colors.
- **FR-095**: System MUST state staleness on screen and MUST NOT render optimistic state as
  confirmed.
- **FR-096**: System MUST display zero explicitly wherever the duplicate-effect count appears.
- **FR-097**: System MUST use the same vocabulary in the interface as in the logs and documentation,
  in sentence case throughout.

**Landing surface**

- **FR-098**: System MUST present a landing page whose first viewport states the claim in two
  sentences and shows a live status strip read from the health and metrics endpoints.
- **FR-099**: System MUST present a hand-built SVG or CSS mechanism explainer under a few kilobytes,
  with no animation library and no video file, that falls back to a labelled static frame under
  reduced motion.
- **FR-100**: System MUST run the four-step guided demo inline, with no navigation, no account and
  no configuration required.
- **FR-101**: System MUST call the real kill endpoint from the guided demo and MUST label it as real.
- **FR-102**: System MUST narrate the orphaned stall with a lease countdown rather than hiding it.
- **FR-103**: System MUST state in words that the replayed steps did not re-execute their tool calls.
- **FR-104**: System MUST generate the evidence figures from the harness with a timestamp, and MUST
  omit the evidence badge entirely when no report exists.
- **FR-105**: System MUST state the prior art, the effectively-once framing and the single-writer
  ceiling in plain type on the page.
- **FR-106**: System MUST provide the three one-click presets — short run, long run, and an
  unsafe-tool run that crashes inside the uncertainty window.
- **FR-107**: System MUST write one `demo_effects` row per side-effect execution and MUST surface
  that count as the ground truth for "it ran once".
- **FR-108**: System MUST provide a reset affordance that prunes completed demo runs and MUST NOT
  let it touch chaos history.
- **FR-109**: System MUST present the outbound surface: wordmark, repository link, console link,
  live evidence badge, one-line attribution, and a footer with repository, license, the
  self-hosting statement and — if the design document was written — a link to it. The system MUST
  exclude newsletter signups, social buttons, notification prompts, feature grids, testimonials,
  pricing, and any analytics-driven modal or cookie banner beyond the legal minimum. **No modal may
  stand between an arriving reviewer and the demo**, which is the reason the last exclusion is
  stated rather than assumed.

**Deployment modes**

- **FR-110**: System MUST determine mode at process start from configuration, never from a request, a
  session or a user.
- **FR-111**: System MUST default to demonstration mode when configuration is absent.
- **FR-112**: System MUST NOT mount the agent-registration route in demonstration mode, and that
  route MUST return 404 rather than 401 or 403.
- **FR-113**: System MUST expose no code path in demonstration mode that executes visitor-supplied
  code.
- **FR-114**: System MUST gate every capability on deployment mode alone, with no authentication, no
  accounts, no sessions and no per-user server-side state anywhere in the product.
- **FR-115**: System MUST scope cancel and resolve actions to demo runs in demonstration mode.
- **FR-116**: System MUST bound chaos duration and worker count in demonstration mode while keeping
  the capability available.
- **FR-135**: System MUST expose no write path by which one visitor's action reaches another
  visitor's run other than the deployment-wide affordances already enumerated — killing a worker,
  running chaos, and the demo reset. **No endpoint MUST accept a run id it may then mutate on behalf
  of a caller who did not create it**, and this MUST hold by the absence of such a path rather than
  by a check on one. The final row of the §31.1 matrix is the requirement, and it is the only row
  whose satisfaction is a statement about code that does not exist.

**Developer path**

- **FR-117**: System MUST bring up the full stack — database, Redis, API, three or more workers —
  with one command and no configuration.
- **FR-118**: System MUST accept an agent as a single function that receives the step context and
  returns exactly one action.
- **FR-119**: System MUST accept tools as plain functions with a separate safety declaration.
- **FR-120**: System MUST expose registered agents and their contracts, and the tool registry with
  safety categories, over the API.
- **FR-121**: System MUST document the one conceptual constraint — one action then return control, no
  state in variables across steps — in the first paragraph of the authoring documentation.
- **FR-122**: System MUST state in the README's first paragraph that Anchor is self-hosted and that
  the deployed instance is a demonstration instance.
- **FR-138**: System MUST include the professor-outreach agent verbatim in the README, immediately
  after the constraint of FR-121, and MUST point at the long-run demo agent as the canonical worked
  example of the already-done filter pattern. The example is required rather than optional because
  it is the only place the constraint is shown to **buy** something rather than merely to cost
  something. *(§26.4, §35.)*
- **FR-139**: System MUST state the shape of a framework adapter in the design documentation — a
  graph-based framework is driven one node per `decide_next_step` invocation, with its state object
  rehydrated from the step context on each call, rather than by calling the framework's own
  end-to-end execution method — and MUST NOT build one. *(§26.5; §18's cut stands. The shape is
  stated because a reviewer familiar with such a framework will ask, and because a contract that
  cannot answer the question is a contract with an undiagnosed constraint.)*

**Authoring surface (stretch)**

- **FR-123**: System MUST statically validate a draft against the contract on keystroke pause and on
  submission, rejecting determinism-boundary violations, invalid return shapes, module-level mutable
  state, unregistered tool names, missing safety declarations and unbounded self-recursion.
- **FR-124**: System MUST phrase validator errors to teach the invariant, naming the line and the
  step-context call that replaces the offending one.
- **FR-125**: System MUST route generated drafts through the validator before display, MUST NOT
  register or execute them, and MUST seed the generator with the contract, the constraint, the tool
  registry and the demo agents.
- **FR-126**: System MUST degrade honestly with no provider key — editor and validator work, generate
  is disabled with a stated reason.
- **FR-127**: System MUST state the deployment mode in the page header at all times.
- **FR-134**: System MUST state, adjacent to the validation results and in the authoring
  documentation, that the checks are mechanical and **cannot** detect incorrect business logic — a
  loop filtered on the wrong key, or a terminal branch unreachable for the inputs that will actually
  arrive. The system MUST NOT render "all checks passed" in a way that reads as "this agent is
  correct", and SHOULD render the pre-registration checklist as the stated next step rather than as a
  disclaimer. *(§34; [research.md](./research.md) D-59.)*
- **FR-136**: System MUST NOT persist authoring drafts server-side — no saved drafts, no per-user
  workspaces, no draft state surviving the session beyond the browser. A draft lives in the editor
  and in the developer's clipboard. *(§27.5; this is what keeps §21.7's "no per-user server-side
  state" true once an editor exists.)*
- **FR-137**: System MUST state, in the specification and in the authoring documentation, that the
  draft generator operates at **authoring time on text a human then reviews**, and that this is
  categorically distinct from generating behaviour at runtime, which the governing rule forbids. The
  distinction MUST NOT be documented only at the API layer.

**Fleet and deployment integrity** *(added by the optimality pass; see [research.md](./research.md) §10)*

- **FR-128**: System MUST apply migrations in a dedicated one-shot step that completes before any API
  or worker process starts, and every process MUST compare the applied schema revision against the
  revision its code was built against and **refuse to start** on a mismatch, naming both revisions.
  A long-running process MUST NOT apply migrations itself.
- **FR-129**: System MUST assign each worker process an identity that is unique for that process
  lifetime and never reused, comprising a stable fleet-slot label and an incarnation counter. A
  restarted worker MUST be distinguishable in the log from the process it replaced.
- **FR-130**: System MUST derive a step's attempt count from the log rather than from process memory or
  a per-run counter, so that the retry cap and dead-lettering survive an arbitrary number of worker
  handoffs. A poison step under worker churn MUST NOT retry indefinitely.
- **FR-131**: System MUST hash each tool's safety declaration and detect disagreement between code
  versions. On conflict it MUST refuse to execute **that tool** fleet-wide, record both dissenting code
  versions, and surface the conflict — and MUST NOT resolve the uncertainty window using an ambiguous
  declaration.
- **FR-132**: System MUST reject an event payload above a configured ceiling with a typed error that
  fails the step and eventually dead-letters the run, and MUST NOT truncate a payload to fit.
- **FR-133**: System MUST serve display-only time series from a derived, watermarked rollup that is
  rebuildable from the log, and MUST continue to compute the duplicate-effect count, the stranded-run
  count and every chaos-report figure live from source. The rollup MUST NOT be maintained by a trigger
  on the append path.

### Key Entities *(include if feature involves data)*

- **Run**: one agent execution from submission to terminal state. Carries the fencing epoch, the
  lease, the owner, the sequence allocator, the client request key, priority, attempt count and the
  cancellation flag. Status is one of `pending`, `running`, `completed`, `failed`, `cancelled`,
  `needs_review`.
- **Run event**: an immutable record appended to a run's log, carrying its sequence number, type,
  payload, the writer's epoch and worker id. The unit of durability.
- **Tool journal entry**: the idempotency ledger row for one logical side effect — key, canonical
  arguments, argument hash, intent timestamp, nullable result and result timestamp, and the
  resolution policy applied if the uncertainty window was entered.
- **Tool registry entry**: a declared tool and its safety properties — natural idempotency, provider
  key support, reconciliation availability, and default uncertainty policy.
- **Worker**: one **process lifetime** — a stable fleet-slot label plus an incarnation counter, with
  host, process, capacity, code version and liveness telemetry. Identity is never reused, so a restart
  is visible rather than inferred.
- **Chaos event**: one injected failure, with type, target and affected runs.
- **Chaos run**: one harness execution with its configuration, timing and status. *(New; approved
  2026-07-31.)*
- **Chaos report**: the permanent invariant result and metric set for one chaos run. Immutable in
  every deployment mode. *(New; approved 2026-07-31.)*
- **Runtime configuration**: the live-editable timing, retry and concurrency values, authoritative in
  PostgreSQL, with Redis used only as a change notification. *(New; approved 2026-07-31.)*
- **Demo effect**: one row per side-effect execution by the demo agent — the externally verifiable
  ground truth for the effectively-once claim.
- **Metrics rollup bucket**: a pre-aggregated, watermarked, **display-only** time-series bucket,
  derived from the log and rebuildable from it. Never a source for a correctness figure. *(New;
  research.md D-49.)*

### Invariant Impact *(mandatory)*

This specification covers the whole runtime, so it touches all eight invariants. Each is preserved
by the mechanism named, and each has the listed acceptance coverage.

- **`I1` no duplicate side effects**: touched. Preserved by the two-phase journal with a canonically
  derived key, a unique key constraint, and the three declared policies. Covered by US3, FR-037–050,
  and chaos invariant 1.
- **`I2` append-only, strictly ordered log**: touched. Preserved by append-only writes, the
  `(run_id, seq)` unique constraint, and transactional counter allocation. Covered by FR-022–024 and
  chaos invariant 2.
- **`I3` one writer per run**: touched. Preserved by the monotonic epoch and a database trigger that
  rejects stale writes, plus silent withdrawal on fencing. Covered by US2, FR-015–021, and chaos
  invariant 3.
- **`I4` ownership decided in one database transaction**: touched. Preserved by the single-statement
  skip-locked claim that also increments the epoch, sets the lease and appends the claim event.
  Covered by US1 scenario 1 and FR-007–009.
- **`I5` time from the database**: touched. Preserved by evaluating expiry server-side exclusively.
  Covered by FR-010 and the clock-skew edge case.
- **`I6` non-determinism journaled**: touched. Preserved by the step-context surface, the
  `NONDET_RECORDED` event, and a test that bans direct clock, random and identifier access in agent
  code. Covered by US8 scenario 3 and FR-031–036.
- **`I7` fail closed**: touched. Preserved by refusing to execute without a durable record, and by
  demonstration mode being the default when configuration is absent. Covered by FR-056–058,
  FR-111–113.
- **`I8` uncertainty surfaced**: touched. Preserved by the three-state journal lookup and the
  per-tool declared policy, with `needs_review` as the honest terminal for the unsafe case. Covered
  by US3 scenarios 4–6 and FR-045–050.

**Build phase**: this specification spans phases 1–9. It is deliberately whole-project rather than
per-phase; the implementation plan fragments it, and `/speckit-tasks` is to be run per phase so that
no phase's task list is polluted with a later phase's work. **No later-phase work may be pulled
forward** — in particular, no console before phase 4 and no landing surface before phase 8.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across a sustained chaos run with hundreds of randomized worker kills, **zero
  duplicate tool executions** are observed — every idempotency key carries at most one recorded
  result, and `demo_effects` holds exactly one row per logical side effect.
- **SC-002**: **Zero stranded runs** — every submitted run reaches a terminal state within the
  bounded time, under arbitrary worker churn.
- **SC-003**: Median and p99 recovery from worker death to resumption are measured and published
  **with the profile and lease duration they were measured under**, and fall within the derived
  bound `lease_duration − renewal_interval / 2 + reclaim_poll_interval / 2`.
- **SC-004**: Sequence numbers are strictly increasing with no duplicates and no gaps across every
  run in the corpus.
- **SC-005**: No epoch on any run carries events written by two different worker ids.
- **SC-006**: Replaying any completed run's log reproduces an identical final state.
- **SC-007**: Every row of the source spec's §9 failure matrix has an integration test that induces
  the failure and asserts the documented handling.
- **SC-008**: A reviewer who has never heard of the project reaches the deployed URL and, within
  sixty seconds, without reading the README, without an account, and without navigating away from
  the landing page, has watched a worker die mid-run and another resume it, and has seen the
  evidence that nothing ran twice.
- **SC-009**: The landing page reaches "I just watched it do the hard thing" **with no scrolling on
  a laptop viewport and with the prose unread**.
- **SC-010**: The replayed-versus-executed distinction is verifiable **with the display in
  grayscale**.
- **SC-011**: A reviewer with `prefers-reduced-motion` enabled loses no information anywhere in the
  product.
- **SC-012**: The quickstart has been executed end to end from a clean clone, on a machine that has
  never run the project, **by someone other than the author**, with every step working as written or
  corrected.
- **SC-013**: Throughput as a function of worker count is measured and plotted against an
  ideal-linear reference, and the divergence point is attributable to the single PostgreSQL writer
  with a stated sharding remediation.
- **SC-014**: Fencing rate is observable over time and interpretable as a configuration signal —
  a rising rate reads as a lease too short relative to renewal latency.
- **SC-015**: In demonstration mode, the agent-registration route returns 404 and no import path in
  the API package reaches registry-mutation code.
- **SC-016**: A visitor can kill every worker and find the fleet at full complement within seconds.
- **SC-017**: The published headline figures are generated from the most recent chaos report and are
  never hand-typed; the evidence badge is absent rather than stale when no report exists.
- **SC-018**: The fencing token mechanism — the zombie timeline, why the epoch must be monotonic, and
  why the check must live in the database — can be whiteboarded cold, without notes.

## Assumptions

- **`anchor-spec.md` is authoritative for intent and stays at the repository root** under that name.
  The constitution's precedence order references it by path, and the specification's internal
  cross-references (§-numbers across five addenda) presume a single document. This feature spec
  therefore derives from it rather than replacing or renaming it.
- **The workload is self-generating.** There is no external API dependency, no data feed and no user
  required for the system to run or demonstrate. Submitting runs and killing workers is the product.
- **Model calls are stubbed on every path that matters.** The runtime cannot tell the difference, by
  construction of the determinism boundary, so a stub removes API keys, cost, rate limits and
  non-determinism from the demo, chaos and test paths. A real provider adapter is out of scope until
  phases 1–8 are complete.
- **Agent workloads are deliberately simple.** The runtime is agnostic to the agent; a complex agent
  would obscure the mechanism being demonstrated.
- **Scale is not the claim.** Single region, single PostgreSQL writer, modest throughput. The claim is
  measured correctness under adversarial failure.
- **Hosting is a paid tier with three or more always-on workers.** A worker that sleeps is not a
  fault-tolerant runtime, so free-tier hosting is disqualifying.
- **No authentication anywhere, in any phase.** Restrictions are a function of deployment mode alone.
- **Three worker identity hues is the validated ceiling**, which is why the deployment specifies
  three always-on workers. Beyond three, identity is carried by direct labels and emphasis.
- **Prior art is named rather than implied.** Anchor is a durable execution engine in the Temporal
  lineage, specialized for agent workloads and built to be demonstrated rather than deployed at
  scale.
- **Four tables beyond the source spec's §7**: `chaos_runs`, `chaos_reports` and `runtime_config`
  (approved 2026-07-31), plus `metrics_rollup` (research.md D-49), which is derived and rebuildable
  from the log rather than a new source of truth. `runs.last_seq` was already introduced by
  Addendum C §25.1.
- **An optimality pass on 2026-07-31 closed three correctness holes** that the first design would have
  shipped: a retry cap that reset on every worker handoff (letting a poison step retry forever), a
  global concurrency cap that enforced nothing, and worker identity reused across container restarts.
  FR-128 – FR-133 record the resulting requirements; research.md §10 records the reasoning. None of it
  required a constitution amendment.
- **The Python packages are wrapped in an `anchor/` package directory** — a documented one-level
  deviation from the §5.1 tree, approved on 2026-07-31, with `web/` and `ops/` remaining siblings at
  the repository root.
- **`Scheduled`, `API keys` and `Webhooks` are not built** unless their add-if-early features are,
  and their sidebar entries are absent rather than empty.
- **Branching and fork-from-checkpoint are cut, and the cut is load-bearing.** Forking a run at step
  N, altering an input and re-executing forward on the journaled prefix is a natural extension of an
  event-sourced runtime and would render well in the thread view — and it is cut on prior-art grounds
  (§28.3), because it already ships in a widely-used agent framework and in a commercial debugging
  product. The reason it is recorded here rather than merely omitted is the second one: **a fork
  produces two histories sharing a prefix, and both `I2` (append-only, ordered, gap-free per run) and
  `I3` (exactly one writer per run per epoch) currently assume one linear history per run.**
  Reintroducing branching therefore means reopening the two invariants that constitute the project's
  proof, which makes it a constitution amendment under Principle IX and not a feature request.
- **The four research-flavoured extensions are recorded as future work, not pursued** (§28.4):
  divergence-aware replay, cost-aware recovery, a generic reconciliation protocol, and semantic
  compensation. The last is additionally **refused rather than merely deferred** — generating
  compensating actions with a model at runtime contradicts the governing rule directly, unlike the
  authoring-time generation of §27.4, which does not.
- **Addendum F (§34–§36) is deferred and unscheduled.** It is agent-authoring boilerplate, and §36
  states the sequencing: none of it is built until phases 1–8 are working and demoed. It carries no
  phase, no work packages and no traceability row; see [plan.md](./plan.md) → *Deferred backlog* and
  [research.md](./research.md) §11. **One of its four items is pulled forward** — the demo agents are
  written as reference implementations in phase 5 rather than improved afterward, because they are
  also the chaos harness's workloads and rewriting a fixture after phase 8 would invalidate the
  evidence captured with it (D-57). Its pre-registration checklist is already recorded in
  [contracts/agent-contract.md](./contracts/agent-contract.md), being documentation of an existing
  contract rather than new product surface.
