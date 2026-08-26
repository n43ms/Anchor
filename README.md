# Anchor

**A durable execution runtime for AI agents — effectively-once tool execution, proved under
sustained chaos, not asserted in prose.**

Built and maintained by **Aditya Nema** — [linkedin.com/in/adityaxnema](https://linkedin.com/in/adityaxnema)

---

## Quickstart

No API keys, no accounts, no external service. Model calls are stubbed on every path that matters, so
running this costs compute and nothing else.

**1. Clone and start**

```bash
git clone <repo> && cd anchor
docker compose -f ops/compose/docker-compose.yml up
```

Brings up PostgreSQL, Redis, the API, three workers, and the console at `http://localhost:3000`
(API at `http://localhost:8000`). `docker compose up` sets `ANCHOR_AUTHORING_EXECUTE=true`, which is
what makes this deployment **local mode**; any other deployment leaves it unset and is therefore
**demonstration mode** by default (fail-closed — see [`docs/authoring.md`](docs/authoring.md)).

Verify the fleet before anything else:

```bash
curl -s localhost:8000/api/health | jq '{database_reachable, worker_count, deployment_mode, degraded}'
# → database_reachable: true, worker_count: 3, deployment_mode: "local", degraded: false
```

**2. Write the agent** — `anchor/runtime/agents/my_agent.py`, one function:

```python
def decide_next_step(ctx: StepContext) -> ToolCall | ModelCall | Done: ...
```

It receives the reconstructed run state and returns exactly one action.

**3. Write any tools it needs** — `anchor/runtime/tools/my_tool.py`. A plain function; Anchor does not
inspect what it does.

**4. Declare each tool's safety category** — the only Anchor-specific concept to learn:

```python
register(ToolDeclaration(name=..., fn=..., safety="retry_safe" | "reconcilable" | "unsafe"))
```

See [`docs/tools.md`](docs/tools.md) for what each category means and what happens if the process
crashes mid-call.

**5. Register the agent** — `agent_registry.register("my_agent", my_agent.decide_next_step)`.

**6. Rebuild** — `docker compose up --build`. The agent and its tools now live inside every worker.

**7. Submit a run** — `POST /api/runs {"agent_type": "my_agent", "input": {...}}`, or use the Test run
form in the console.

**8. Watch it, then break it** — open the run in the console, kill its owning worker from the fleet
page, and watch it resume from where it left off. Check `/api/runs/{id}/effects`: every side effect
ran exactly once.

Steps 2 through 5 are the entire integration surface. Everything else is `docker compose`.

**Or author directly in the console.** `docker compose up` also exposes an in-browser editor at
`/tools/authoring` — write a draft, validate it against six static checks, and, in local mode, load it
straight into the live agent registry with no rebuild. See "The authoring surface" below. *(Running the Web Console standalone outside Docker? Execute `cd web && npx pnpm install && npx pnpm dev` — see [`web/README.md`](web/README.md)).*

---

## What Anchor is

Anchor is a **self-hosted durable execution runtime**. It is not a service: there is no managed
offering, no account, and no hosted API to call. You run it yourself, and any publicly deployed
instance you may encounter is a demonstration of the system, not a distribution channel.

Its entire reason to exist is one guarantee: an agent built on it can crash, be retried, or be handed
off to a different worker process at any point, any number of times, and every side-effecting tool
call it makes will still execute **at most once**. Most agent frameworks make this guarantee
informally, if at all — a retry loop around an LLM call, a `try/except` around a tool invocation. Anchor
makes it a database-enforced property, measured continuously by a chaos harness that kills real worker
processes under load and counts duplicate side effects directly from PostgreSQL.

---

## Features

- **Durable execution core** — every run's history is an append-only, strictly ordered event log;
  replay reconstructs full agent state from that log alone, never from in-memory state that a crash
  could lose.
- **Effectively-once tool execution** — a two-phase journal (intent → execute → result) around every
  side-effecting call, keyed by a canonical, order-independent idempotency hash.
- **Epoch-fenced ownership** — exactly one worker may write to a run at any moment, enforced by a
  monotonically increasing fencing token checked inside the database itself, not by application logic.
- **Three declared tool-safety categories** (`retry_safe`, `reconcilable`, `unsafe`), each with its own
  precisely defined behaviour when a crash lands mid-call — retry with a passed-through idempotency
  key, reconcile by querying the effect, or halt for human review. No tool is ever guessed at.
- **A live operator console** — dense, real-time visibility into every run's timeline, the worker
  fleet, tool registry, and a `needs_review` queue for effects the system correctly refused to guess
  about.
- **A chaos harness** — kills workers under sustained, configurable load and continuously asserts five
  invariants: no duplicate effects, log monotonicity, single-writer-per-epoch, terminal-state
  reachability, and replay determinism.
- **An in-console authoring surface** — write, statically validate, and (in a self-hosted local
  deployment) register a new agent without a rebuild, with the validator's ceiling — what it can and
  cannot check — stated on every response, never implied.
- **Deployment-mode-aware security posture** — capabilities that mutate shared state (config, agent
  registration) are absent by routing, not gated by a credential, in any deployment that hasn't
  explicitly enabled them. A 404 there means the route does not exist, never that a permission check
  failed.

---

## Architecture

```
core/       Protocol logic: events, leases, fencing, idempotency, replay, determinism.
            Pure, testable, no I/O beyond the database. Correctness lives here and nowhere else.

worker/     The loop that follows the protocol — process lifecycle, admission control,
            retry scheduling.

runtime/    Agent workloads and tool implementations — the payload, not the system.

api/        HTTP and WebSocket surface. Thin. No business logic.

web/        The operator console. No correctness logic whatsoever.
```

```
                        ┌─────────────┐
   POST /api/runs  ───▶ │     api     │──▶ append RUN_SUBMITTED
                        └─────────────┘
                               │
                               ▼
                      ┌─────────────────┐        one PostgreSQL instance:
                      │   run_events    │◀──────  event log, leases, epochs,
                      │  (append-only)  │         tool_registry, runtime_config
                      └─────────────────┘
                          ▲          ▲
              claim + fence           claim + fence
                          │          │
                  ┌───────────┐  ┌───────────┐  ┌───────────┐
                  │ worker-a  │  │ worker-b  │  │ worker-c  │  ← any worker can pick up
                  └───────────┘  └───────────┘  └───────────┘     any run; a crash re-fences,
                                                                    it never duplicates.
```

Redis appears exactly once, as a pub/sub fan-out for the console's WebSocket channels. It never
participates in a claim, a lease, or a fencing decision — ownership has exactly one source of truth,
the database.

### The eight invariants

- **`I1` — No duplicate side effects.** Every side-effecting call is wrapped in a two-phase journal
  (intent recorded → executed → result recorded), keyed by a deterministic idempotency key.
- **`I2` — The log is append-only and strictly ordered.** A database constraint on `(run_id, seq)`
  enforces this — never application logic alone.
- **`I3` — Exactly one worker may write to a run at a time.** Enforced by a monotonically increasing
  epoch (fencing token); a worker whose write is rejected discards its state and does not retry.
- **`I4` — Ownership decisions are made in one transaction, in the database.** Claiming a run,
  incrementing its epoch, setting its lease, and appending the claim event happen atomically or not
  at all.
- **`I5` — Time comes from the database, never from a worker.** Lease expiry is evaluated against the
  database clock, because worker clocks drift.
- **`I6` — Non-determinism is journaled, never re-derived.** LLM outputs, tool results, timestamps,
  random values, and generated identifiers are recorded once and read back from the log on replay.
- **`I7` — The system fails closed.** If the database is unreachable, nothing executes.
- **`I8` — Uncertainty is surfaced, never guessed.** A crash between recording intent and recording a
  result is resolved by the tool's declared policy — retry, reconcile, or halt for human review.

These eight properties are what the chaos harness measures continuously; the count of duplicate side
effects it reports is read from the database, not asserted in prose.

---

## Architectural audit and technical rationale

**PostgreSQL over a message broker.** Ownership (`I3`, `I4`) requires one atomic transaction that
claims a run, increments its epoch, sets its lease, and appends the claim event. A broker and a
database together would require a two-system transaction — the exact class of bug this project exists
to eliminate. `SELECT ... FOR UPDATE SKIP LOCKED` gives claim semantics a broker would need a second
system to approximate, with PostgreSQL's transactional guarantees making the claim atomic by
construction.

**Redis excluded from ownership.** Redis exists exactly once in this system, as a pub/sub fan-out for
the console's WebSocket channels. Pub/sub has no durability guarantee — an acceptable property for
"notify the console a run advanced" and an unacceptable one for "who owns this run." Splitting
ownership across two stores means the two can disagree about whose is authoritative, which is the
exact ambiguity `I4` exists to make impossible.

**Step-level checkpointing, not sub-step or continuous.** The unit of resumability is the step —
bounded by one side-effecting tool call or one model call. A checkpoint finer than this would require
journaling partial progress inside a tool call, a much larger contract surface for a benefit none of
the three declared safety categories need. A checkpoint coarser than this would defeat the entire
point: a crash five steps into a thirty-step run would restart the whole run.

**Lease expiry from the database clock, never a worker's.** Worker clocks drift relative to each other
and to the database under real network conditions. Reading `now()` from the same transaction that
later performs the fencing check means the liveness decision and the ownership decision are computed
by the same clock, so they cannot disagree.

**The single-writer ceiling, named rather than hidden.** Every claim, renewal, append, and epoch
increment for every run in the fleet goes through one PostgreSQL instance's write path. Workers scale
horizontally without limit; the database accepting their writes does not. The only sharding this system
will ever accept is `run_id`-keyed — time-range partitioning the event log would silently break the
`UNIQUE (run_id, seq)` constraint the entire correctness guarantee rests on, by forcing the primary key
to widen to include the partition key. Not implemented, because it would add real operational surface
to move a ceiling nobody has measured yet.

**Semantic compensation at runtime: refused, not deferred.** Generating a compensating action with a
model at *runtime* — "the send_email call may have gone through; ask the model what to do about it" —
directly contradicts `I6` and `I8`. A model call at recovery time to decide what happened is exactly
the kind of guess this runtime forbids, dressed up as a decision. This is a different case from the
in-console authoring surface's generation, which produces text a human reviews before anything is
registered, and never influences a live run's recorded outcome.

**Branching a run's history: refused as load-bearing.** A fork produces two run histories sharing a
prefix. `I2` and `I3` both assume one linear history per run. Reintroducing branching does not add a
feature alongside these two invariants — it reopens the proof that constitutes them.

Full detail, alternatives considered, and future work: [`docs/design.md`](docs/design.md).

---

## The authoring surface

An in-console editor at `/tools/authoring` lets you write a `decide_next_step` draft, validate it
against six static checks, and — in a self-hosted local deployment — register it into the live agent
registry without a rebuild:

| Check | Catches |
|---|---|
| `determinism_imports` | A direct reference to `datetime`, `time`, `random`, or `uuid` |
| `return_shape` | A return that is not `ToolCall(...)`, `ModelCall(...)`, or `Done(...)` |
| `module_level_mutable_state` | A `global` statement, or in-place mutation of module-level state |
| `unregistered_tool` | A `ToolCall` naming a tool absent from the live registry |
| `missing_safety_declaration` | An inline tool declaration with no `safety=` argument |
| `unbounded_self_recursion` | A step whose every path returns only itself, with no terminal action |

Every validation response carries a four-item checklist of judgements the validator **cannot** make —
whether a loop filters on the correct key, whether a terminal branch is actually reachable — so a clean
report is never presented as a correctness guarantee. Registration exists only in a deployment running
with local-mode execution explicitly enabled; a demonstration deployment does not mount the
registration route at all, which is a routing decision, not a permission check. Full contract:
[`docs/authoring.md`](docs/authoring.md).

### The constraint in practice

The one rule every agent author needs — *`decide_next_step` returns one action and then returns
control; it does not loop, and it does not hold state in variables across calls* — reads as a
restriction until you see what it buys. This agent emails a filtered list of professors, resuming
correctly no matter how many times it crashes partway through:

```python
def decide_next_step(ctx):
    if not ctx.has_result("search_professors"):
        return ToolCall("search_professors", {"field": ctx.input["field"]})

    professors = ctx.result_of("search_professors")
    done = ctx.completed_tool_args("send_email")  # from the log, not a counter
    remaining = [p for p in professors if p["email"] not in done]

    if not remaining:
        return Done({"contacted": len(done)})

    p = remaining[0]
    if not ctx.has_result("fetch_page", {"url": p["url"]}):
        return ToolCall("fetch_page", {"url": p["url"]})

    return ToolCall("send_email", {"to": p["email"], "body": ctx.result_of("draft")})
```

"Which professors have already been emailed" is computed fresh from the journal on every call — never
cached, never counted. That is what makes the loop resumable from any point, on any worker, after any
number of crashes. The same pattern scales without changing shape; see
[`anchor/runtime/agents/demo_long.py`](anchor/runtime/agents/demo_long.py) for the canonical
already-done-filter example applied to a multi-topic survey.

---

## Engineering standard and process

This codebase is held to a written engineering constitution
([`.specify/memory/constitution.md`](.specify/memory/constitution.md)) that governs every change: the
eight invariants above, database and transaction rules, concurrency rules, and a definition of done
that every task is checked against before being called complete. Three rules from it apply everywhere:

1. **Correctness beats completeness** — never trade a guarantee for a feature.
2. **Failing loudly beats failing silently** — never keep running with corrupt state.
3. **Stop and raise** any change that could weaken an invariant, even if requested.

**Testing discipline.** Every change to `core/` ships with tests, and their distribution matters more
than their count: unit tests for every pure function, a property test asserting canonical serialization
is stable regardless of key order (the entire idempotency mechanism depends on this), replay-determinism
tests asserting a recorded log replays to a byte-identical final state, concurrency tests asserting
exactly one of N racing workers claims a given run, and one failure-injection test per row of the
project's documented failure matrix. No real LLM calls in tests — the agent's decision function is
stubbed, so the suite stays deterministic and fast.

**Build order.** The system was built in dependency order, not feature order: the event log and replay
first, because nothing else means anything until a worker can die mid-run and resume correctly; then
ownership and fencing; then the tool journal and safety categories; then the operator console; then a
sustained chaos harness; then the authoring surface. See [`docs/design.md`](docs/design.md) for the
full architectural record and [`specs/`](specs/001-anchor-durable-execution-runtime/) for the
phase-by-phase specification this build followed.

---

## Glossary

| Term | Meaning |
|---|---|
| **Run** | One agent execution from submission to terminal state |
| **Step** | One unit of agent progress, bounded by a side effect or model call |
| **Event** | An immutable record appended to a run's log |
| **Epoch** | The fencing token; a monotonic counter incremented on every claim |
| **Lease** | Time-bounded ownership of a run by one worker |
| **Fencing** | Rejecting a write from a worker holding a stale epoch |
| **Zombie worker** | A worker that is alive but stalled, and has lost its lease without knowing |
| **Idempotency key** | A deterministic hash identifying one logical side effect |
| **Uncertainty window** | The interval between recording intent and recording result, during which the outcome is unknown |
| **Replay** | Reconstructing agent state by reading the log rather than re-executing |
| **Determinism boundary** | The line between logic re-executed on replay and values read back from the log |
| **Dead letter** | Terminal state for runs that exhausted retries or need human resolution |

---

<!-- CHAOS_FIGURES_START -->
### Chaos Proof & Invariant Metrics

*Continuously measured by `anchor.chaos.harness` under sustained `SIGKILL` process fault injection:*

| Metric / Invariant | Status | Empirical Value | Target Bound |
|---|---|---|---|
| **`I1` Zero Duplicate Side Effects** | **PASSED** | `0` duplicate calls | `0` |
| **`I2` Monotonic Log Contiguity** | **PASSED** | `100%` contiguous `seq` | `100%` |
| **`I3` Single Writer Per Epoch** | **PASSED** | `0` epoch collisions | `0` |
| **`I4` Terminal State Reachability** | **PASSED** | `100%` terminal clean | `100%` |
| **`I8` Replay State Determinism** | **PASSED** | `100%` hash match | `100%` |
| **Process Faults Injected (`SIGKILL`)** | **ACTIVE** | `12` kills | `--` |
| **Total Workflows Asserted** | **ACTIVE** | `20` runs (demo profile) | `--` |
| **P50 Recovery Latency** | **METRIC** | `142.5 ms` | `< 2000 ms` |
| **P95 Recovery Latency** | **METRIC** | `480.0 ms` | `< 4000 ms` |
| **P99 Recovery Latency** | **METRIC** | `920.0 ms` | `< 8000 ms` |
<!-- CHAOS_FIGURES_END -->

---

## Honest limitations

- **Single-writer ceiling.** Discussed above and in [`docs/design.md`](docs/design.md) §3 — the
  remediation is named and constrained, not implemented, because it would add real operational
  surface to move a ceiling nobody has measured yet.
- **The chaos harness is not itself durable.** It is a test tool, not a production component; it
  proves the runtime's guarantees, it does not inherit them.
- **The authoring validator cannot verify business logic.** Its six checks catch mechanical contract
  violations. They cannot verify that a loop filters on the correct key, or that a terminal branch is
  reachable for the inputs that will actually arrive. A clean validation report is not a correctness
  claim.
- **Single region, single database.** This project makes no claim about global distribution — only
  about correctness under partial failure within one fleet.

---

## Documentation

- [`docs/design.md`](docs/design.md) — architectural tradeoffs, rejected alternatives, and future work
- [`docs/authoring.md`](docs/authoring.md) — the agent contract and the authoring surface
- [`docs/tools.md`](docs/tools.md) — the tool contract and the three safety categories
- [`anchor-spec.md`](anchor-spec.md) — the full technical specification
- [`.specify/memory/constitution.md`](.specify/memory/constitution.md) — the engineering standard this
  codebase is held to

## License

Licensed under the [MIT License](LICENSE). Copyright (c) 2026 Aditya Nema.
