# Phase 1 — Data Model

**Feature**: 001-anchor-durable-execution-runtime
**Date**: 2026-07-31
**Authority**: [`anchor-spec.md`](../../anchor-spec.md) §7 for the six specified tables;
[research.md](./research.md) D-20/D-21/D-22 for the three approved additions;
[the constitution](../../.specify/memory/constitution.md) → Data Model and Protocol Constraints for
what must be enforced in the database rather than in application code.

Eleven tables plus Alembic's own version table. Every column is listed with its type, nullability,
default, and meaning. **Adding, removing, or repurposing any column below is a schema change and must
be raised before implementation**, per the constitution.

**Incorporates the optimality pass** ([research.md](./research.md) §10): worker incarnations (D-42),
derived step attempts (D-43), tool declaration hashing (D-46), batched non-determinism (D-47),
conditional renewal events (D-48), the `metrics_rollup` tier (D-49), the payload ceiling (D-51), and
the partitioning prohibition (D-52).

**Type conventions.** Timestamps are `timestamptz` and are always written with `now()` — the
transaction clock — never `clock_timestamp()` and never a worker's clock (`I5`, D-09). Payloads are
`jsonb`. Enumerated values are `text` with a table `CHECK`, not PostgreSQL `ENUM` types: forward-only
migrations plus `ALTER TYPE … ADD VALUE` is an operational trap, and `text` renders directly in the
Logs view without a cast (D-13's "explicit beats clever" applied to the schema).

---

## 1. `runs` — one row per agent execution

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | `bigint` identity | no | generated | Run identifier. Rendered `run_{id}` (D-14). |
| `agent_type` | `text` | no | — | Registered agent name. Resolved against the agent registry at claim time. |
| `input` | `jsonb` | no | `'{}'` | The submission payload handed to the agent's first invocation. |
| `client_request_key` | `text` | yes | — | Caller-supplied submission-deduplication key. Unique when present. |
| `status` | `text` | no | `'pending'` | One of `pending`, `running`, `completed`, `failed`, `cancelled`, `needs_review`. |
| `epoch` | `integer` | no | `0` | **The fencing token.** Incremented on every claim. Never decremented. |
| `last_seq` | `bigint` | no | `0` | **The sequence allocator** (D-07). Incremented in the append transaction. |
| `lease_expires_at` | `timestamptz` | yes | — | Ownership expiry, evaluated against the database clock. `NULL` in every terminal state. |
| `owner_worker_id` | `text` | yes | — | Current owner. FK to `workers.id`. `NULL` in every terminal state. |
| `priority` | `smallint` | no | `0` | Claim order; **lower is sooner** (D-11). |
| `attempts` | `integer` | no | `0` | **Denormalized display value only** (D-43). The authoritative per-step attempt count is derived from the log by counting `STEP_FAILED` for that `step_index`; the retry cap reads the derived value, never this column. Holding it in worker memory or per-run would let a poison step retry forever across handoffs. |
| `cancel_requested_at` | `timestamptz` | yes | — | The cooperative cancellation flag, as a timestamp so the audit shows *when*. |
| `is_demo` | `boolean` | no | `false` | Marks runs submitted from the landing surface or the presets. Scopes cancel, resolve, and the reset affordance in demonstration mode (§31). |
| `chaos_run_id` | `bigint` | yes | — | Set when the run was submitted by the harness. FK to `chaos_runs.id`. |
| `created_at` | `timestamptz` | no | `now()` | Submission time. Secondary claim ordering key. |
| `claimed_at` | `timestamptz` | yes | — | Most recent claim time. Powers "started {n}s ago" and recovery measurement. |
| `finished_at` | `timestamptz` | yes | — | Terminal-state time. `NULL` until terminal. |

**Constraints.**

- `PRIMARY KEY (id)`
- `CHECK (status IN ('pending','running','completed','failed','cancelled','needs_review'))`
- `CHECK (epoch >= 0)`, `CHECK (last_seq >= 0)`, `CHECK (attempts >= 0)`
- **`CHECK` — terminal states hold no lease** (D-23):
  `status IN ('completed','failed','cancelled','needs_review')` implies
  `owner_worker_id IS NULL AND lease_expires_at IS NULL AND finished_at IS NOT NULL`.
  This is the constitution's "illegal states unrepresentable" requirement expressed structurally: a
  run cannot be `completed` and hold a lease, and a halted `needs_review` run cannot block reclaim
  while looking healthy.
- **`CHECK` — running implies ownership**: `status = 'running'` implies
  `owner_worker_id IS NOT NULL AND lease_expires_at IS NOT NULL`.
- `UNIQUE (client_request_key)` as a partial unique index where `client_request_key IS NOT NULL`
  (FR-002).
- `FOREIGN KEY (owner_worker_id) REFERENCES workers(id)` — `ON DELETE SET NULL` is **not** used;
  worker rows are never deleted, only aged out of the fleet view.
- `FOREIGN KEY (chaos_run_id) REFERENCES chaos_runs(id)`

**Indexes.**

| Index | Query it serves | Write cost |
|---|---|---|
| `(status, priority, created_at)` partial `WHERE status = 'pending'` | The `pending` branch of the claim query (D-10) | One entry per pending run; entry disappears on claim |
| `(lease_expires_at)` partial `WHERE status = 'running'` | The expired-lease branch of the claim query | Updated on every renewal — accepted, because reclaim latency is the number the product publishes |
| `(status, created_at DESC)` | The runs list, filtered by status, newest first | One entry per run |
| `(is_demo, status)` partial `WHERE is_demo` | The reset affordance and the demo hourly cap | Small |
| `(chaos_run_id)` partial `WHERE chaos_run_id IS NOT NULL` | Invariant checking scoped to one chaos run | Small |

**State machine.**

```
                    ┌──────────────────────────────────────────┐
                    │                                          │
  submit            │  claim / reclaim                         │  resolve: retry
    │               ▼                                          │
    ▼          ┌─────────┐   claim    ┌─────────┐               │
 pending ─────►│ pending │───────────►│ running │───────────────┤
               └─────────┘            └────┬────┘               │
                    ▲                      │                    │
                    │  lease expiry         ├──► completed   (terminal)
                    │  (epoch increments,   ├──► failed      (terminal, dead letter)
                    └── status stays        ├──► cancelled   (terminal)
                        'running')          └──► needs_review ──┘ (halted, leaseless)
```

Reclaim after lease expiry does **not** change `status` — the run stays `running` and the epoch
increments. That is deliberate: `orphaned` is a *derived* display state (lease expired, no live
owner), not a stored one, because storing it would require a writer at the exact moment nobody owns
the run. `needs_review` is the only non-terminal-looking state that is leaseless, and the only state
from which an operator write is permitted (D-24).

---

## 2. `run_events` — the append-only log

The spine of the system. Nothing here is ever updated or deleted (`I2`).

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `run_id` | `bigint` | no | — | Owning run. FK to `runs.id`. |
| `seq` | `bigint` | no | — | Per-run sequence number, strictly increasing, allocated from `runs.last_seq`. |
| `type` | `text` | no | — | One of the 17 event types below. |
| `payload` | `jsonb` | no | `'{}'` | Type-specific body; schemas in §11. |
| `epoch` | `integer` | no | — | **The epoch of the writer.** Validated by trigger against the run's current epoch. |
| `worker_id` | `text` | no | — | The writer. `'operator'` for human resolution writes (D-24), `'api'` for `RUN_SUBMITTED`. |
| `step_index` | `integer` | yes | — | The step this event belongs to; `NULL` for run-scoped events. |
| `created_at` | `timestamptz` | no | `now()` | Database-clock write time. |

**Constraints.**

- **`PRIMARY KEY (run_id, seq)`** — this doubles as the uniqueness constraint the spec calls "the
  single most important constraint in the schema". Making it the primary key rather than a separate
  unique index means there is no ordering of DDL in which the table exists without it.
- `CHECK (type IN (…17 values…))`
- `CHECK (seq > 0)`, `CHECK (epoch >= 0)`
- `FOREIGN KEY (run_id) REFERENCES runs(id)`
- **No `UPDATE`/`DELETE` trigger**: `run_events_immutable` raises on either, so append-only is a
  database property and not a coding convention.
- **`run_events_epoch_gate`** — `BEFORE INSERT`, described in §10.

**Indexes.**

| Index | Query it serves | Write cost |
|---|---|---|
| `PRIMARY KEY (run_id, seq)` | Replay (ordered scan by run), per-run log pagination, backfill after `after_seq` | Unavoidable; compact because `run_id` is `bigint` (D-14) |
| `(type, created_at DESC)` | The global Logs page filtered by event type; metrics series | One entry per event — the most expensive index in the schema, justified by the Logs page and §12's metrics both being spec-required |
| `(worker_id, created_at DESC)` | Logs filtered by worker; per-worker throughput | One entry per event |
| `(run_id, epoch)` | Invariant 3 (single writer per epoch) | Small |

**Retention.** None. The log is the audit trail and the evidence; nothing prunes it. The reset
affordance deletes only completed demo *runs* and cascades their events — and never touches chaos
history (§21.6).

**Payload ceiling.** `payload` is rejected above a configured ceiling (default 1 MiB) with a typed
`PayloadTooLargeError`, which fails the step and eventually dead-letters the run (D-51). This is
enforced in `core/events.append` rather than as a `CHECK`, and the exception to "constraints over
conventions" has a specific reason: a size check requires casting `jsonb` to `text`, that cast is
`stable` rather than `immutable`, and PostgreSQL will not accept a non-immutable expression in a
`CHECK`. **Truncating an oversized payload is forbidden** — replay would then reconstruct different
messages than the original execution, which is replay divergence introduced by a size optimization.

> ### ⚠ Partitioning prohibition (D-52)
>
> **`run_events` MUST NOT be range-partitioned by `created_at`.** PostgreSQL requires every unique
> constraint on a partitioned table to contain the partition key, so a time-partitioned log forces the
> key to `(run_id, seq, created_at)` — which **does not enforce uniqueness of `(run_id, seq)`**. Two
> events for one run with the same sequence number, landing in different time partitions, would both
> be accepted, silently. That deletes the most important constraint in the schema and breaks `I2`,
> while looking like a routine time-series optimization in the diff.
>
> If the log is ever partitioned, the partition key **must contain `run_id`** — which preserves the
> constraint and keeps replay reads pruned. It is not being done now, because partitioning one table
> on one host does not move the single-writer ceiling.

---

## 3. `tool_journal` — the idempotency ledger

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `idempotency_key` | `text` | no | — | Full SHA-256 hex over run id, step index, action name, and canonical arguments (D-12). **Primary key.** |
| `run_id` | `bigint` | no | — | FK to `runs.id`. |
| `step_index` | `integer` | no | — | The step that owns this effect. |
| `tool_name` | `text` | no | — | FK to `tool_registry.name`. |
| `args_canonical` | `jsonb` | no | — | The canonically serialized arguments, stored so a reviewer can see what the key was derived from. |
| `args_hash` | `text` | no | — | SHA-256 of the canonical arguments alone. Backs the display form and cross-step comparison. |
| `intent_at` | `timestamptz` | no | `now()` | When intent was recorded. The uncertainty window opens here. |
| `intent_epoch` | `integer` | no | — | The epoch of the writer that recorded intent. |
| `result` | `jsonb` | yes | — | **Nullable by design.** `NULL` means "no result recorded" — the third state. |
| `result_at` | `timestamptz` | yes | — | When the result was recorded. The uncertainty window closes here. |
| `result_epoch` | `integer` | yes | — | The epoch of the writer that recorded the result. May differ from `intent_epoch` after a handoff. |
| `resolution` | `text` | yes | — | The uncertainty policy applied, if the window was entered: `retry_safe`, `reconcilable`, `unsafe_halted`, `operator_marked_executed`, `operator_marked_not_executed`. `NULL` when the window was never entered. |
| `resolved_at` | `timestamptz` | yes | — | When the resolution was applied. |
| `attempts` | `integer` | no | `1` | Executions attempted for this key. `> 1` only for `retry_safe`. |

**Constraints.**

- `PRIMARY KEY (idempotency_key)` — enforces "exactly one intent row per idempotency key" (`I1`).
- `CHECK (result IS NULL) = (result_at IS NULL)` — the two result columns move together, so
  "result recorded" is never ambiguous.
- `CHECK (resolution IS NULL OR resolution IN (…5 values…))`
- `CHECK (attempts >= 1)`
- `FOREIGN KEY (run_id) REFERENCES runs(id)`, `FOREIGN KEY (tool_name) REFERENCES tool_registry(name)`
- **No `DELETE`**: enforced by trigger, same reasoning as the log.

**The three-state lookup** this table exists to make expressible:

| Row state | Meaning | Action |
|---|---|---|
| Row present, `result IS NOT NULL` | Completed | Skip execution, return `result`, emit `STEP_SKIPPED_ON_REPLAY` |
| No row | Never attempted | Execute normally |
| Row present, `result IS NULL` | **Uncertain** | Apply the tool's declared policy (`I8`) |

**Indexes.**

| Index | Query it serves | Write cost |
|---|---|---|
| `PRIMARY KEY (idempotency_key)` | The three-state lookup on every side-effecting step | Unavoidable |
| `(run_id, step_index)` | Replay's journal reconstruction; run detail's effect counters | One per effect |
| `(tool_name, result_at DESC)` | Tool registry "last used"; uncertainty resolutions by policy | Small |
| partial `WHERE result IS NULL` | **Invariant checking and the Needs review page** — finds every open uncertainty window in one scan | Very small; entries disappear when results land |

---

## 4. `tool_registry` — declared tools and their safety properties

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `name` | `text` | no | — | Tool name. **Primary key.** |
| `safety` | `text` | no | — | `retry_safe`, `reconcilable`, or `unsafe`. **No default** — the decision must be made deliberately. |
| `naturally_idempotent` | `boolean` | no | `false` | Whether the effect is inherently repeatable. |
| `provider_accepts_key` | `boolean` | no | `false` | Whether the provider deduplicates on a passed-through idempotency key. |
| `has_reconcile_fn` | `boolean` | no | `false` | Whether a reconciliation query exists. |
| `default_policy` | `text` | no | — | The policy applied on entering the uncertainty window. |
| `declaration_hash` | `text` | no | — | SHA-256 over the five safety-relevant fields above (D-46). The identity of the *declaration*, as distinct from the tool. |
| `declared_by_version` | `text` | no | — | The `code_version` whose registration wrote the current row. |
| `conflict_at` | `timestamptz` | yes | — | Set when a worker registered a **different** `declaration_hash`. Non-null means **this tool is refused for execution fleet-wide** until resolved. |
| `conflict_version` | `text` | yes | — | The dissenting `code_version`, recorded so the operator can see which two builds disagree. |
| `description` | `text` | yes | — | Shown in the registry page. |
| `registered_at` | `timestamptz` | no | `now()` | First registration. |
| `last_used_at` | `timestamptz` | yes | — | Last execution. Shown in the registry page. |

**Constraints.**

- `PRIMARY KEY (name)`
- `CHECK (safety IN ('retry_safe','reconcilable','unsafe'))`
- `CHECK (default_policy IN ('retry_safe','reconcilable','unsafe'))`
- **`CHECK` — a `reconcilable` tool must have a reconciliation function**:
  `safety = 'reconcilable'` implies `has_reconcile_fn`. FR-046 enforced in the database rather than
  at registration, so a row inserted by any path still satisfies it.
- **`CHECK` — `retry_safe` requires a stated reason**:
  `safety = 'retry_safe'` implies `naturally_idempotent OR provider_accepts_key`. A tool cannot be
  declared retry-safe without naming *why* it is safe to re-execute.

- `CHECK ((conflict_at IS NULL) = (conflict_version IS NULL))` — the conflict columns move together.

The second and third checks are the schema-level expression of §3.3's argument that per-tool
declaration is what lets the runtime be correct across tools with genuinely different
characteristics. A registry row that claims a category it cannot support is exactly the failure that
would turn `I1` into a wish.

**The conflict columns exist because the registry is a table and the declaration is code** (D-46), so
during a rolling deploy the two can disagree — about *the policy that resolves the uncertainty
window*. A tool reclassified from `unsafe` to `retry_safe` between builds means a crash inside that
window **halts for review on one worker and re-executes on another**, in the same fleet,
non-deterministically. `I8` says uncertainty is resolved by the tool's declared policy; if "the
declared policy" is ambiguous, `I8` has no content. Refusing **that tool** — not that worker, and not
the fleet — is the fail-loud reading, and it is why the conflict is stored rather than merely logged.

---

## 5. `workers` — the fleet registry

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | `text` | no | — | Worker identifier, `{label}#{incarnation}` — e.g. `worker-a#3`. **Unique per process lifetime.** Primary key. |
| `label` | `text` | no | — | The fleet **slot** — `worker-a`, `worker-b`, … — claimed from a pool at registration. Survives restarts, and is what the identity hue derives from, so a worker keeps its color across a restart. |
| `incarnation` | `integer` | no | — | Process lifetime counter for this label, from a PostgreSQL sequence. `worker-a#4` is unambiguously the fourth process to hold slot `a`. |
| `hostname` | `text` | no | — | Host or container name. |
| `pid` | `integer` | no | — | Process id. |
| `started_at` | `timestamptz` | no | `now()` | Registration time. Powers uptime. |
| `last_seen_at` | `timestamptz` | no | `now()` | Liveness telemetry. Powers "last heartbeat age" and detects register-then-die. |
| `current_run_count` | `integer` | no | `0` | Runs currently held. |
| `capacity` | `integer` | no | — | Per-worker concurrency limit in force for this process. |
| `code_version` | `text` | no | — | Build identifier. **Powers the Deployments page** with no new instrumentation. |
| `role` | `text` | no | `'runner'` | `runner` or `chaos`. Lets the fleet view distinguish a harness driver from an executor. |
| `stopped_at` | `timestamptz` | yes | — | Set on graceful shutdown. `NULL` after a hard kill — the absence is itself informative. |

**Constraints.** `PRIMARY KEY (id)`; `UNIQUE (label, incarnation)`;
`CHECK (id = label || '#' || incarnation)` — the composite identity and its parts cannot drift apart;
`CHECK (role IN ('runner','chaos'))`;
`CHECK (current_run_count >= 0 AND current_run_count <= capacity)`;
`CHECK (incarnation >= 1)`.

**Index.** `(last_seen_at DESC)` for the fleet view and stale-worker detection; `(label, incarnation DESC)`
for "the current process in slot `a`".

**Why identity carries an incarnation** (D-42). Hostname plus pid is **reused** on a container
platform: a killed worker restarts with the same hostname and can receive the same pid. A reused id
would silently falsify three things the product claims — `runs.owner_worker_id` would point at an id
that now denotes a *different* process, breaking "which worker executed each step"; re-registration
would overwrite `started_at` so uptime described the new process while historical events attributed
work to the id as if it were continuous; and **the Deployments page could not answer its own
question**, since whether an in-flight run is being resumed by a worker on different code is
unanswerable if two code versions can share a worker id. Rows are never updated in place across
incarnations: each process inserts its own row, so the fleet's history is append-only in practice as
well as in principle.

**Note on `current_run_count`.** It is telemetry, not an authority. Admission control is enforced by
the worker against its own in-process count before it attempts a claim (FR-004); this column exists so
the fleet view can display occupancy. Recorded explicitly because using it to *decide* admission would
be a second source of truth for something the worker already knows — an anti-pattern the constitution
names.

---

## 6. `chaos_events` — every injected failure

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | `bigint` identity | no | generated | Event identifier. |
| `chaos_run_id` | `bigint` | yes | — | Owning harness run; `NULL` for a kill issued manually from the console. |
| `type` | `text` | no | — | `worker_kill`, `worker_kill_graceful`, `latency_injected`, `stall_injected`, `tool_failure_injected`, `uncertainty_crash_injected`. |
| `target_worker_id` | `text` | yes | — | The worker acted upon. |
| `affected_run_ids` | `bigint[]` | no | `'{}'` | The runs the injection touched. |
| `params` | `jsonb` | no | `'{}'` | Injection-specific parameters, e.g. latency milliseconds. |
| `created_at` | `timestamptz` | no | `now()` | Injection time. Anchors recovery measurement. |

**Constraints.** `PRIMARY KEY (id)`; `CHECK (type IN (…6 values…))`;
`FOREIGN KEY (chaos_run_id) REFERENCES chaos_runs(id)`. **Immutable**: a trigger raises on `UPDATE`
and `DELETE` in every deployment mode (§31).

**Index.** `(chaos_run_id, created_at)`; `(type, created_at DESC)`.

**Why `created_at` matters more than it looks.** Recovery latency is measured from a `worker_kill`
row's `created_at` to the `RUN_CLAIMED` event that reclaims each affected run. This table is
therefore not documentation of the experiment — it is one of the two inputs to the published number.

---

## 7. `chaos_runs` — one row per harness execution *(new; approved 2026-07-31)*

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | `bigint` identity | no | generated | Chaos run identifier. |
| `status` | `text` | no | `'pending'` | `pending`, `running`, `completed`, `failed`, `abandoned`. |
| `params` | `jsonb` | no | — | Worker count, kill rate, latency injection, failure injection, duration, run count, step mix. |
| `deployment_mode` | `text` | no | — | `demonstration` or `local`. Recorded because the two have different parameter bounds. |
| `config_profile` | `text` | no | — | `demo` or `production`. |
| `lease_duration_ms` | `integer` | no | — | The lease in force, captured at launch. A recovery figure without it is not a measurement. |
| `renewal_interval_ms` | `integer` | no | — | Likewise. |
| `started_at` | `timestamptz` | no | `now()` | Launch time. |
| `ended_at` | `timestamptz` | yes | — | Completion time. |
| `heartbeat_at` | `timestamptz` | yes | — | Last progress write. Drives `abandoned` detection after a restart (D-36). |

**Constraints.** `PRIMARY KEY (id)`;
`CHECK (status IN ('pending','running','completed','failed','abandoned'))`;
`CHECK (deployment_mode IN ('demonstration','local'))`;
`CHECK (config_profile IN ('demo','production'))`;
`CHECK (ended_at IS NULL OR ended_at >= started_at)`.

**Index.** `(started_at DESC)` for the History page.

---

## 8. `chaos_reports` — the permanent invariant record *(new; approved 2026-07-31)*

One row per completed chaos run. **Immutable in every deployment mode**, enforced by a trigger that
raises on `UPDATE` and `DELETE` (§31). This is the published evidence.

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `chaos_run_id` | `bigint` | no | — | **Primary key.** FK to `chaos_runs.id`. |
| `inv_no_duplicate_effects` | `boolean` | no | — | Invariant 1 result. |
| `inv_log_monotonic` | `boolean` | no | — | Invariant 2 result. |
| `inv_single_writer_per_epoch` | `boolean` | no | — | Invariant 3 result. |
| `inv_terminal_reachability` | `boolean` | no | — | Invariant 4 result. |
| `inv_replay_determinism` | `boolean` | no | — | Invariant 5 result. |
| `violations` | `jsonb` | no | `'[]'` | Every violation found, with the run, key, epoch, or seq that failed. Empty is the expected value and is stored explicitly rather than as `NULL`. |
| `duplicate_effect_count` | `integer` | no | — | **The headline figure.** Renders as the hero zero. |
| `stranded_run_count` | `integer` | no | — | Runs that never reached a terminal state. |
| `kills_injected` | `integer` | no | — | Worker kills performed. |
| `runs_total` | `integer` | no | — | Runs submitted. |
| `steps_total` | `integer` | no | — | Steps executed. |
| `recovery_ms_p50` | `integer` | yes | — | Median kill-to-resumption. `NULL` when no kill occurred. |
| `recovery_ms_p95` | `integer` | yes | — | — |
| `recovery_ms_p99` | `integer` | yes | — | — |
| `recovery_ms_max` | `integer` | yes | — | — |
| `replay_steps_mean` | `numeric` | yes | — | Mean steps replayed per resumption. |
| `replay_ms_mean` | `numeric` | yes | — | Mean replay latency. |
| `steps_per_second` | `numeric` | yes | — | Aggregate throughput. |
| `fencing_events` | `integer` | no | `0` | Stale writes rejected. A configuration signal, not just a health one. |
| `uncertainty_entries` | `jsonb` | no | `'{}'` | Count per resolution policy applied. |
| `dead_letter_count` | `integer` | no | `0` | Runs that exhausted retries. |
| `duration_seconds` | `integer` | no | — | Sustained duration. |
| `created_at` | `timestamptz` | no | `now()` | Report time. Drives "last chaos run: 4h ago". |

**Constraints.** `PRIMARY KEY (chaos_run_id)`; `FOREIGN KEY (chaos_run_id) REFERENCES chaos_runs(id)`;
`CHECK (duplicate_effect_count >= 0 AND stranded_run_count >= 0)`;
`CHECK ((recovery_ms_p50 IS NULL) = (kills_injected = 0))` — a recovery figure exists exactly when a
kill happened, which is the schema-level version of §24.2's rule that a zero recovery time on a run
that never lost a worker is not a measurement and invites distrust of the numbers that are real.

**Index.** `(created_at DESC)` — the landing badge and README refresher both read the latest row.

---

## 9. `runtime_config`, `demo_effects`, and `metrics_rollup`

### `runtime_config` *(new; approved 2026-07-31)*

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `key` | `text` | no | — | Setting name, e.g. `lease_duration_ms`. **Primary key.** |
| `value` | `jsonb` | no | — | Typed value. `jsonb` rather than `text` so an integer stays an integer. |
| `version` | `bigint` | no | `1` | Monotonic, incremented on every applied change. Workers compare and re-read. |
| `updated_at` | `timestamptz` | no | `now()` | Last change. |
| `updated_by` | `text` | no | `'seed'` | `seed`, `operator`, or `profile:{name}`. |

**Constraints.** `PRIMARY KEY (key)`; `CHECK (version >= 1)`.

**Seeded keys** — fifteen, because the optimality pass introduced three values that are configuration
rather than constants and therefore may not be hardcoded: `renewal_interval_ms`, `lease_duration_ms`,
`margin_ms`, `step_timeout_ms`, `max_attempts_per_step`, `backoff_base_ms`, `backoff_factor`,
`backoff_jitter_pct`, `backoff_cap_ms`, `per_worker_concurrency`, `global_concurrency_cap`,
`reclaim_poll_interval_ms`, **`lease_renewed_emit_policy`** (`boundaries_and_slow` | `always`, D-48),
**`renewal_latency_warn_pct`** (the fraction of the lease above which a renewal is emitted and
flagged), **`max_event_payload_bytes`** (the D-51 ceiling).

**Enforcement note.** The relationship assertion (`lease_duration >= 4 × renewal_interval`,
`margin == lease_duration − renewal_interval`, `step_timeout > 0`) is validated by the API before the
write and rejects the write. It is **not** a `CHECK`, because it spans rows and PostgreSQL cannot
express a cross-row invariant as a `CHECK` — the honest options were a statement trigger over the
whole table or application validation at the single write path. The trigger is written anyway, as the
backstop, exactly as the epoch gate is: `runtime_config_assert` runs `AFTER` each statement, re-reads
all twelve keys, and raises `AN002` if the relationship is violated. Application validation exists to
produce a good error message; the trigger exists to make the property true.

### `demo_effects` — the proof surface

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `id` | `bigint` identity | no | generated | Effect identifier. |
| `run_id` | `bigint` | no | — | FK to `runs.id`. |
| `step_index` | `integer` | no | — | The step that produced it. |
| `tool_name` | `text` | no | — | The tool that executed. |
| `idempotency_key` | `text` | no | — | FK to `tool_journal.idempotency_key`. |
| `payload` | `jsonb` | no | `'{}'` | What the fake effect "did" — recipient, subject, order id. |
| `executed_at` | `timestamptz` | no | `now()` | Execution time. |

**Constraints.** `PRIMARY KEY (id)`;
**`UNIQUE (idempotency_key)`** — this single constraint is the strongest evidence in the product. It
means a double execution does not merely get counted, it gets *rejected by the database*, and the
rejection is a loud failure rather than a silent duplicate row. `FOREIGN KEY (run_id)`,
`FOREIGN KEY (idempotency_key)`.

**Index.** `(run_id, step_index)` for `GET /api/runs/{id}/effects`.

### `metrics_rollup` — display-only time series *(new; D-49)*

| Column | Type | Null | Default | Meaning |
|---|---|---|---|---|
| `bucket_start` | `timestamptz` | no | — | Start of the time bucket. |
| `bucket_seconds` | `integer` | no | — | Bucket width. Two resolutions are maintained: 10 s for live views, 300 s for long windows. |
| `metric` | `text` | no | — | `steps_completed`, `runs_by_status`, `recovery_ms`, `lease_renewal_ms`, `replay_steps`, `replay_ms`, `fencing_events`, `uncertainty_entries`, `dead_letters`. |
| `dimension` | `text` | no | `''` | Worker label, run status, or resolution policy — empty string for undimensioned metrics, so the key is never partially null. |
| `count` | `bigint` | no | `0` | Observation count. |
| `sum_value` | `numeric` | yes | — | For latency metrics; `sum/count` gives the mean. |
| `histogram` | `jsonb` | yes | — | Bin counts, for the metrics that render as histograms. |

**Constraints.** `PRIMARY KEY (bucket_start, bucket_seconds, metric, dimension)`;
`CHECK (bucket_seconds IN (10, 300))`; `CHECK (count >= 0)`.

**Watermark.** A single-row `metrics_rollup_watermark (last_created_at, last_run_id, last_seq)` records
how far the rollup job has consumed `run_events`. The job reads strictly above the watermark, upserts
buckets, and advances it in the same transaction.

**This table is derived, not authoritative.** Truncating it and replaying the log reconstructs it
exactly, and a tested `REBUILD` path does so. **It is maintained by a periodic job, never by a
trigger** — and that is a correctness decision, not a performance one: an `AFTER INSERT` trigger
upserting the current bucket would make every worker contend on the *same* bucket row, serializing
appends **across runs that currently never contend at all**. It would convert the system's best
property — that the only lock on the append path is the run's own row — into a global write bottleneck,
in service of a sparkline.

**What must never be read from here**: the duplicate-effect count, the stranded-run count, the
`needs_review` list, effect counts, and every chaos-report figure. Those are correctness reads and are
always computed from `tool_journal` and `run_events` at read time. A stale zero on the duplicate
counter is the single most damaging thing this product could display.

---

## 10. Triggers and functions

| Object | Fires | Behaviour |
|---|---|---|
| `run_events_epoch_gate` | `BEFORE INSERT ON run_events` | `SELECT epoch FROM runs WHERE id = NEW.run_id FOR UPDATE`; raise `AN001` when `NEW.epoch < current`, and raise when `NEW.epoch > current` (a writer inventing an epoch). Takes the lock itself so the guarantee does not depend on the caller (D-08). |
| `run_events_immutable` | `BEFORE UPDATE OR DELETE ON run_events` | Raise `AN003`. Append-only becomes a database property. |
| `tool_journal_no_delete` | `BEFORE DELETE ON tool_journal` | Raise `AN003`. |
| `tool_journal_result_once` | `BEFORE UPDATE ON tool_journal` | Permit only the transitions the protocol needs — `NULL → result`, `attempts` increment, and setting `resolution`. Raise `AN004` on any attempt to overwrite a non-null `result` with a different value. **A result, once recorded, is final.** |
| `chaos_reports_immutable` | `BEFORE UPDATE OR DELETE ON chaos_reports` | Raise `AN003` in every deployment mode. |
| `chaos_events_immutable` | `BEFORE UPDATE OR DELETE ON chaos_events` | Raise `AN003`. |
| `runtime_config_assert` | `AFTER INSERT OR UPDATE ON runtime_config` (statement-level) | Re-read all timing keys; raise `AN002` if the relationship assertion fails. |

**SQLSTATE allocation.** `AN001` fenced write · `AN002` configuration relationship violated ·
`AN003` immutable row · `AN004` result overwrite. Each maps to exactly one typed Python error:
`LeaseFencedError`, `ConfigAssertionError`, `ImmutableRecordError`, `ResultOverwriteError`.

`tool_journal_result_once` deserves its own note: it is the constraint that makes "at most one
recorded result per key" true rather than merely intended. Without it, `I1` would hold only for as
long as every write path remembered not to overwrite — which is precisely the class of enforcement the
constitution rejects.

---

## 11. Event payload schemas

Every event's `payload`. Fields marked ● are required. This is the contract replay reads, so a
payload change is a protocol change.

| Event | Payload |
|---|---|
| `RUN_SUBMITTED` | ● `agent_type`, ● `input`, `client_request_key`, ● `is_demo`, `chaos_run_id` |
| `RUN_CLAIMED` | ● `worker_id`, ● `epoch`, ● `reason` (`initial` \| `reclaimed_after_lease_expiry`), ● `lease_expires_at`, `previous_worker_id` |
| `REPLAY_COMPLETED` | ● `steps_replayed`, ● `replay_ms`, ● `last_completed_step_index`, ● `journal_entries_loaded`, ● `nondet_values_loaded` |
| `STEP_STARTED` | ● `step_index`, ● `action_kind` (`tool` \| `model` \| `nondet` \| `done`) |
| `LLM_CALLED` | ● `step_index`, ● `prompt_hash`, ● `response`, ● `model`, ● `latency_ms`, ● `stubbed` (boolean — the demo path states this on the page, so it states it in the log too) |
| `TOOL_INTENT` | ● `step_index`, ● `tool_name`, ● `args_canonical`, ● `idempotency_key`, ● `args_hash`, ● `safety` |
| `TOOL_RESULT` | ● `step_index`, ● `tool_name`, ● `idempotency_key`, ● `result`, ● `latency_ms`, `resolution` |
| `NONDET_RECORDED` | ● `step_index`, ● `entries[]` — each with ● `kind` (`time` \| `random` \| `id`), ● `value`, ● `call_ordinal`. **One event per step, not per call** (D-47), written in the same transaction as that step's `TOOL_INTENT` — or as `STEP_COMPLETED` when the step has no side effect |
| `STEP_COMPLETED` | ● `step_index`, ● `duration_ms`, ● `action_kind` |
| `STEP_SKIPPED_ON_REPLAY` | ● `step_index`, ● `idempotency_key`, ● `tool_name`, ● `original_result_at`, ● `original_epoch` |
| `STEP_FAILED` | ● `step_index`, ● `attempt`, ● `error_type`, ● `error_message`, ● `will_retry`, `backoff_ms` |
| `LEASE_RENEWED` | ● `lease_expires_at`, ● `renewal_latency_ms`, ● `emit_reason` (`first_after_claim` \| `latency_threshold_exceeded` \| `final_before_terminal` \| `always_mode`). **Not emitted on every renewal** (D-48) |
| `WORKER_FENCED` | ● `fenced_worker_id`, ● `stale_epoch`, ● `current_epoch`, ● `detected_by` (`renewer` \| `append`) |
| `RUN_COMPLETED` | ● `output`, ● `total_steps`, ● `total_duration_ms`, ● `handoff_count` |
| `RUN_FAILED` | ● `step_index`, ● `attempts`, ● `error_type`, ● `error_message`, ● `dead_lettered` |
| `RUN_CANCELLED` | ● `requested_at`, ● `step_index`, ● `cancelled_by` |
| `RUN_NEEDS_REVIEW` | ● `step_index`, ● `idempotency_key`, ● `tool_name`, ● `reason`, ● `available_resolutions` |

`call_ordinal` on `NONDET_RECORDED` is the field most likely to be omitted and the one that makes
replay work: a step may call `ctx.now()` twice, and replay must hand back the two values **in the
order they were originally produced**. Without an ordinal, the second call could receive the first
value and the divergence would be invisible.

`stale_epoch` and `current_epoch` on `WORKER_FENCED` are both required because §22.4 requires the
fencing marker to display both.

**Why batching `NONDET_RECORDED` preserves `I6` exactly** (D-47). `ctx.now()` and `ctx.random()` have
no external effect, so a crash before their journal write is safely re-derivable — nothing in the world
observed the discarded value. Durability is therefore required not at the moment of the call but
**before anything depending on the value leaves the process**, and the only such thing is a side
effect, which is already gated behind `TOOL_INTENT`. Writing the batch in that same transaction means
there is no interleaving in which an effect exists whose inputs are unrecorded — including the case
that actually matters, where `ctx.new_id()` feeds the idempotency key, since the key's inputs and the
intent commit atomically. The cost avoided is not cosmetic: per-call journaling would put hundreds of
synchronous round trips on the critical path of a 40-step run, each competing for the same `runs` row
lock that serializes appends.

**Why `LEASE_RENEWED` is conditional** (D-48). It is the only event type replay does not consume — it
contributes nothing to reconstructing agent state, so it is observability rather than audit. At a
1-second interval with 100 concurrent runs, unconditional emission would make roughly four out of five
rows in the log heartbeat, inflating the table, every global index, and the WAL. Renewal latency stays
fully measured in `metrics_rollup`; the log keeps the renewals a human would ever want per run — when
ownership began, whether renewal ever approached the lease, and when it ended.

---

## 12. Derived values — computed, never stored

Recorded so nobody adds a column for them later. Each is a read-time computation, per D-30's rule
against caching a correctness read.

| Value | Derivation |
|---|---|
| `orphaned` display state | `status = 'running' AND lease_expires_at < now()` |
| Worker segments on the run detail | `RUN_CLAIMED` events partition the log by owner; `ended_at IS NULL` identifies the current owner |
| `handoff_count` | Count of `RUN_CLAIMED` with reason `reclaimed_after_lease_expiry` |
| `recovery_seconds` | Kill `chaos_events.created_at` → the reclaiming `RUN_CLAIMED.created_at`; suppressed entirely when `handoff_count = 0` |
| `duplicate_side_effects` | Keys in `tool_journal` with more than one recorded result — structurally zero, and computed **live, always**, because the claim is only worth what its verification is |
| **Per-step attempt count** | **Count of `STEP_FAILED` events for that `step_index`** (D-43). Authoritative for the retry cap, so the cap survives a worker handoff. `runs.attempts` is display only |
| Replayed vs executed segment | Presence of `STEP_SKIPPED_ON_REPLAY` for the step |
| Worker identity hue slot | Claim order within the run: first owner slot 1, second slot 2, third slot 3; beyond three, current owner slot 1 and all prior owners muted. Derived from `workers.label`, so a hue survives a worker restart |
| Step throughput, fencing rate, replay overhead, renewal latency, run-state distribution | Aggregated into `metrics_rollup` by a watermarked periodic job (D-49) — display series only, derived and rebuildable from the log |
| Fleet staleness | `now() - last_seen_at` against a threshold |
| Fleet slot occupancy | The highest `incarnation` per `label`; a rising incarnation is a restart count, which is itself a durability-relevant fact |
