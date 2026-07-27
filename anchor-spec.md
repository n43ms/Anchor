# Anchor — Technical Specification & Build Audit

**Document type:** Standalone product and engineering specification, written for spec-driven development.
**Version:** 1.0
**Format note:** No implementation code. Architecture, protocols, and flow are expressed as text diagrams and procedures. Every section is written to be handed directly to an AI coding agent or used as a personal build spec.
**Scope note:** This document is complete in itself. It assumes no other project and references none.

---

## 0. Executive summary

Anchor is a durable execution runtime for AI agents. Agent runs are stored as append-only event logs in a database rather than held in a process's memory, so the machine executing a run can die at any moment and another worker resumes from the exact step where it stopped — without re-executing any side effect that already happened.

The system is **self-sufficient**: it generates its own workload. There is no external API dependency, no data feed to babysit, and no users required for it to run or demonstrate. Submitting runs and killing workers is the product.

The engineering claim is specific and measurable: **agent execution that survives arbitrary worker failure with no duplicate side effects, verified by continuous adversarial testing rather than asserted.**

The governing design rule is stated once here and enforced throughout: **all ownership, sequencing, and idempotency decisions are made by deterministic database logic inside a single transaction. No component outside the database is ever authoritative about who owns a run.**

---

## 1. The business problem

### 1.1 What an agent run actually is

An AI agent is not one request and one response. It is a chain of dependent steps, each slow, and several of which reach out and change something in the world.

```
Task: "Research this company and email the client a summary."

  step  1   LLM   decide to search                     ~4s
  step  2   TOOL  web_search("company earnings")       ~2s
  step  3   LLM   evaluate which results matter        ~6s
  step  4   TOOL  fetch_page(url_a)                    ~3s
  step  5   TOOL  fetch_page(url_b)                    ~3s
  step  6   LLM   synthesize findings                 ~18s
  step  7   TOOL  fetch_filing(company_id)             ~5s
  step  8   LLM   draft the summary                   ~22s
  step  9   LLM   self-review the draft               ~11s
  step 10   TOOL  send_email(client, draft)            ~1s
                                                      ─────
                                                      ~75s
```

Real agents run for minutes. Some run for hours. Some pause mid-run waiting on human approval and resume the next day.

### 1.2 The failure that wastes everything

In the standard implementation, that entire chain lives in one process's memory. The conversation history is a variable. The accumulated research is a variable. The draft is a variable. Nothing is written down until the run completes.

Now the process dies at step 8.

The causes are mundane and constant: a container is rescheduled, a deploy rolls out, the host runs out of memory, the cloud provider migrates the workload, a network partition isolates the machine, an operator restarts the service.

**Result: everything intermediate is gone.** The searches, the fetched pages, the filing, the draft. There is no record of what the agent did or how far it got. The only available recovery is to start over from step 1, paying the full time cost and the full API cost a second time.

At one agent this is an annoyance. At five hundred concurrent agents on a machine that dies, it is an operational failure with a real invoice attached.

### 1.3 The failure that is actually dangerous

Change one detail. Suppose the process dies not at step 8 but *immediately after step 10 executed* — the email was sent, the client received it, and the process died before anything recorded that it happened.

The system restarts the run. It has no memory of the previous attempt. It replays from step 1. At step 10, it **sends the email again**.

Substitute a different tool and the severity scales:

| Tool | Consequence of double execution |
|---|---|
| `send_email` | Client receives two copies. Embarrassing. |
| `create_ticket` | Duplicate tickets. Operational noise. |
| `post_message` | Duplicate posts in a shared channel. Visible failure. |
| `place_order` | Duplicate order. Financial and fulfilment cost. |
| `charge_card` | Customer billed twice. Unacceptable. |
| `delete_records` | Potentially irreversible. |

**This is the actual reason organizations don't let agents do consequential work.** Not that the model reasons poorly — that a crash at the wrong instant can cause a real-world action to occur twice, and afterwards nobody can determine whether it did.

### 1.4 The problem told as a story

A team builds an agent that handles refund requests. It reads the ticket, checks the order, decides eligibility, issues the refund, and replies to the customer. It works in testing. They ship it.

Two weeks later, a routine deploy restarts the service. Eleven refunds are issued twice.

The engineering response is predictable and inadequate: they revoke the agent's ability to issue refunds. It now drafts a refund for a human to approve. The automation value is gone. The underlying problem — that agent execution is not durable — was never addressed; it was routed around.

**Anchor is the missing layer.** With it, the agent can be trusted with the refund, because the runtime guarantees the refund executes once regardless of how many times the run is interrupted and resumed.

### 1.5 Why existing infrastructure doesn't cover this

**Job queues** (Celery, RQ, SQS-backed workers) are designed for short, stateless units of work that are cheap to retry from the beginning. "Resize this image" fits the model perfectly. An agent does not: it is long-running, it accumulates large state between steps, and retrying from step one is both expensive and — because of side effects — unsafe.

**Retry wrappers** retry the entire call. That is the wrong granularity by a factor of ten.

**Checkpointing to local disk** loses the checkpoint when the machine is the thing that died.

**Application-level "resume" logic** written per-agent is where most teams end up. It is duplicated, inconsistent, untested against real failure, and invariably missing the uncertainty window.

**Workflow engines** — Temporal, Restate, AWS Step Functions — genuinely do solve this class of problem. That is the strongest available evidence that the problem is real, hard, and worth solving. Anchor is an implementation in the same lineage, scoped specifically to agent workloads.

**State this openly.** In an interview, say: *"This is a durable execution engine in the Temporal lineage, specialized for agent runs."* Naming the prior art demonstrates you understand where your work sits. Implying you invented the category demonstrates the opposite.

---

## 2. Users and end goals

### 2.1 Who this is for

The user is a developer running agents that do something consequential. They are not looking for a better agent framework — they already have one. They are looking for the guarantee that the framework doesn't provide.

### 2.2 The four guarantees the product delivers

1. **A run survives the death of the machine executing it.** Recovery is automatic and completes in seconds, with no human intervention and no manual replay.
2. **No tool executes twice** — across arbitrary crash points, arbitrary numbers of resumptions, and arbitrary worker churn.
3. **Complete auditability.** For any run, the developer can see every step, every input, every output, every retry, every ownership change, and which worker executed each step.
4. **Predictable behaviour under load.** Runs queue rather than overwhelm. A stuck run does not block others. A poisonous run does not retry forever.

### 2.3 The interaction that defines success

A developer submits a run and watches the timeline populate step by step. Mid-run, they click "kill" on the worker executing it. The timeline stalls for two seconds, shows the run as orphaned, then resumes — under a different worker id, from the step it stopped on, with the already-completed tool calls visibly marked as skipped rather than re-run.

Everything in this document exists to make that ten seconds true and provable.

---

## 3. The four core concepts

These are the intellectual content of the project. You must be able to explain each one in plain language and defend the design choices behind it.

### 3.1 Event sourcing — state lives in the log, not in memory

Anchor never stores "the current state of the agent." It stores an **append-only sequence of everything that has happened** and reconstructs state by replaying that sequence.

```
run_47 | seq 1 | RUN_CLAIMED     | worker-a | epoch 1
run_47 | seq 2 | STEP_STARTED    | step 1
run_47 | seq 3 | LLM_CALLED      | prompt_hash abc | response "I should search..."
run_47 | seq 4 | TOOL_INTENT     | web_search{q:"..."} | key run47:s1:a91f
run_47 | seq 5 | TOOL_RESULT     | key run47:s1:a91f  | result [...]
run_47 | seq 6 | STEP_COMPLETED  | step 1
run_47 | seq 7 | STEP_STARTED    | step 2
   ...
```

To resume, a worker reads the log in order and rebuilds the agent's context exactly as it was. The process is disposable; the log is the truth.

**Why append-only rather than mutable state.** Mutation is where corruption comes from. If two workers race to update a "current state" row, the result can be an incoherent blend of two states with no indication that anything went wrong. Appending with a strictly increasing sequence number per run makes conflicts *detectable* — a duplicate sequence number is a constraint violation, not a silent overwrite.

**Why this is a database concern, not an application concern.** The uniqueness of (run_id, seq) must be enforced by the database. If it is enforced in application code, a second worker that never saw the first worker's write will happily append a colliding sequence number. Constraints in the storage layer are the only ones that hold under concurrency.

### 3.2 The determinism boundary

This is the deepest idea in the project and the one most likely to impress a strong interviewer.

Replay only works if replaying produces the same decisions. But agents are saturated with non-determinism: model outputs vary between calls, tool results change over time, the current timestamp is different on every execution, random values are random.

The resolution is to draw a hard line and journal every crossing of it.

```
┌───────────────────────────────────────────────────────────────┐
│  DETERMINISTIC ZONE  —  replayed by RE-EXECUTION              │
│                                                                │
│    • the agent's control flow                                  │
│    • which tool to call given a model response                 │
│    • loop conditions and termination logic                     │
│    • accumulation of state across steps                        │
│                                                                │
│  Must produce identical output given identical input.          │
└───────────────────────────────────────────────────────────────┘
                              │
                              │  every crossing is journaled
                              ▼
┌───────────────────────────────────────────────────────────────┐
│  NON-DETERMINISTIC ZONE  —  replayed by READING THE LOG        │
│                                                                │
│    • LLM completions                                           │
│    • tool and external API calls                               │
│    • the current time                                          │
│    • random values and generated identifiers                   │
│    • any read of external state                                │
│                                                                │
│  Executed once, recorded, never re-executed during replay.     │
└───────────────────────────────────────────────────────────────┘
```

**The rule:** anything non-deterministic is recorded the first time it happens, and on replay is *read back from the log* rather than re-executed.

**The sharp consequence, which you should state unprompted:** the agent's own code must never call the system clock or a random number generator directly. It must request those values from the runtime, which journals them. If it doesn't, replay diverges — the agent takes a different branch than it originally took, and from that point forward the log no longer describes the execution. A generated identifier that differs on replay will produce a different idempotency key, which defeats deduplication entirely.

Explaining this constraint without being asked marks you as someone who has actually implemented replay semantics rather than read about them.

### 3.3 Idempotency — making "did it happen?" answerable

The email problem. The mechanism is a two-phase journal wrapped around every side effect.

```
BEFORE executing:
    append TOOL_INTENT
        tool:             send_email
        args:             {to: ..., subject: ..., body: ...}
        idempotency_key:  hash(run_id, step_index, tool_name,
                               canonical_serialization(args))

EXECUTE the tool

AFTER executing:
    append TOOL_RESULT
        idempotency_key:  <the same key>
        result:           {...}
```

On replay, before invoking any tool, the worker looks up the key:

| Journal state for the key | Meaning | Action |
|---|---|---|
| INTENT present, RESULT present | Completed successfully | Skip execution entirely; return the recorded result |
| INTENT absent | Never attempted | Execute normally |
| INTENT present, RESULT absent | **Uncertain** — crashed during execution | Apply the tool's uncertainty policy |

#### The uncertainty window

There is a genuine interval between "I have recorded that I am about to send this" and "I have recorded that it succeeded." A crash inside that interval leaves the system unable to determine whether the email went out.

**This cannot be eliminated. It can only be handled honestly.** Three policies, declared per tool:

- **Retry-safe.** The tool is naturally idempotent, or the provider accepts an idempotency key. Re-execute, passing your key through so the provider deduplicates on their side. This is how payment APIs work and is the strongest option available.
- **Reconcilable.** You can query whether the effect occurred — "does a message with this identifier exist?" Run the reconciliation query and branch on the answer.
- **Unsafe.** Neither of the above applies. Mark the run `needs_review` and surface it in the dashboard with the specific ambiguous call highlighted. **Do not guess.**

**The sentence to have ready:** *"True exactly-once execution is impossible in a distributed system. Anchor provides at-least-once execution with idempotent effects — effectively-once — plus an explicit, per-tool policy for the uncertainty window."*

That single sentence demonstrates more distributed-systems maturity than any amount of feature description, because it shows you understand the limits of what you built.

#### Why canonical serialization is load-bearing

The idempotency key is derived from the tool's arguments. If the same logical call produces a different hash on replay — because a mapping serialized in a different key order, or a floating-point value formatted differently, or a nested structure was traversed non-deterministically — then deduplication silently fails and the tool executes twice.

Canonical serialization is therefore not a detail. It is the mechanism. Being able to name it as a failure mode you deliberately designed against is a strong signal, and it is the kind of thing that only occurs to someone who has actually built this.

### 3.4 Leases, heartbeats, and fencing tokens

Many identical workers, one shared queue, no central coordinator. How does work get assigned without collisions, and how does a dead worker's work get reassigned?

**Claiming.** A worker atomically selects one available run using a row-locking select that skips rows already locked by other transactions. Every worker gets a different run, with no external coordination and no distributed lock service. The database does the hard part.

**Leasing.** On claim, the run's lease expiry is set to a point in the near future. The worker owns the run until then and no other worker will touch it.

**Heartbeating.** While working, the worker periodically extends the lease. **Extension is the heartbeat** — there is deliberately no separate liveness signal, because two signals can disagree and one cannot.

**Expiry and reclaim.** A dead worker stops extending. The lease expires. Any worker may then claim the run and resume it from the log.

#### The zombie problem

The nasty case is a worker that is not dead but *stalled* — a long garbage-collection pause, a network partition, a suspended virtual machine. Its lease expires, another worker takes over, and then the original wakes up still believing it owns the run and writes to the log. Two writers, one run, corrupted state.

**The fix is a fencing token.** Every run carries a monotonically increasing epoch. Each claim increments it. Every write to that run must carry the epoch the writer believes it holds, and the database rejects any write whose epoch is lower than the run's current epoch.

```
t = 0    Worker A claims run_47                    → receives epoch 5
t = 10   Worker A stalls (GC pause / partition)
t = 45   Lease expires
t = 46   Worker B claims run_47                    → epoch increments to 6
t = 50   Worker B replays the log and resumes
t = 52   Worker A wakes and attempts to append with epoch 5
             → REJECTED: current epoch is 6
             → Worker A observes it has been fenced,
               discards all in-memory state,
               writes nothing further,
               returns to the idle pool
```

No consensus protocol. No distributed lock manager. No external coordination service. A single monotonic counter enforced by a database constraint, and split-brain becomes structurally impossible.

**This is the best interview story the project produces.** It is a real distributed-systems failure mode with a clean, well-known solution, and having implemented it — and hit the bug that motivates it — is rare at any level of experience, let alone undergraduate.

---

## 4. Technology stack and the reasoning behind each choice

| Layer | Choice | Why this, and what was traded away |
|---|---|---|
| Language | Python | The agent ecosystem lives here, and the runtime should be in the same language as the workloads it runs. Gave up: the concurrency ergonomics of Go and the raw throughput of a compiled language — neither is the bottleneck at this scale. |
| Source of truth | PostgreSQL, single instance | The log append, the lease update, and the epoch check must occur in **one atomic transaction**. Splitting them across systems reintroduces precisely the race the design exists to eliminate. Gave up: horizontal write scaling — irrelevant at this volume and reintroducible later via partitioning. |
| Queueing | Postgres row locking with skip-locked semantics | Provides an atomic, contention-free claim in a single statement, in the same transaction as the lease and epoch update. Gave up: the throughput ceiling of a dedicated broker. **Justify this explicitly:** Kafka is a log of *messages*; what you need is a transactional store of *run state*. Adding a broker would add operational surface without solving the problem. |
| Coordination | Redis — **non-authoritative only** | Carries pub/sub fan-out to the dashboard and cheap fleet telemetry. **Never** lease state, never ownership. Two sources of truth for liveness is a way of building split-brain into a system deliberately. Gave up: marginally faster liveness detection. Correctness wins without argument. |
| Workers | Plain processes running a hand-written loop | Writing the loop **is** the project. Using a task framework would hide the exact mechanism being demonstrated. Gave up: batteries-included retry and scheduling, which you are reimplementing on purpose. |
| Agent workload | Any framework, or a hand-rolled loop, running *inside* the durable step boundary | The runtime must be agnostic to the agent framework. The agent is the payload, not the system. |
| API | FastAPI with WebSocket endpoints | Async-native, typed models, automatic schema documentation. |
| Frontend | Next.js with TypeScript and a WebSocket client | The dashboard is a real-time observability surface, not a CRUD screen, and should be built as one. |
| Local development | Docker Compose — API, Postgres, Redis, and three or more workers | Multiple workers locally from day one. A single-worker development environment hides every bug the project exists to solve. |
| Hosting | Render: one web service, one Postgres, one Redis, **three or more always-on background workers** | Three minimum so a worker can be killed during a live demo. **Free tier is disqualifying** — a worker that sleeps is not a fault-tolerant runtime, it is a broken one. |
| Chaos tooling | A kill endpoint on each worker, plus a scripted harness | You cannot reach a terminal on a hosted container mid-demo, so the kill switch must be part of the product. This constraint improves the demo rather than limiting it. |

### 4.1 The four decisions worth being able to defend cold

**Why Postgres rather than Kafka or a dedicated broker.** Because the atomic unit you need is *"claim this run, increment its epoch, extend its lease, and append to its log — all or nothing."* That is one transaction in Postgres and a distributed coordination problem in any split design. Choosing the simpler architecture that makes the invariant trivially enforceable is a senior instinct, and articulating it is worth more than reaching for the fashionable component.

**Why Redis is deliberately excluded from ownership decisions.** If liveness lives in Redis and ownership lives in Postgres, they can disagree, and every disagreement is a potential double execution. One source of truth for ownership; Redis is a delivery mechanism for the UI and nothing more. Being able to say "I deliberately did *not* use Redis for X, and here's why" is a stronger signal than any amount of technology adoption.

**Why step-level checkpointing rather than finer or coarser.** Coarser — per-run — provides no recovery benefit at all. Finer — inside a model call — is impossible, since you cannot checkpoint within a provider's API request. The step boundary is the natural transaction boundary because it is precisely where side effects occur. Articulating *why* the granularity is what it is signals real design thinking rather than an arbitrary choice.

**Why lease expiry is evaluated using the database clock.** Because worker clocks drift. Two workers whose clocks differ by a minute will make contradictory ownership decisions if each evaluates expiry locally. Evaluating expiry server-side eliminates an entire class of bug that is nearly impossible to reproduce and diagnose.

---

## 5. System architecture

```
        ┌────────────────────────────────────────────────────────────┐
        │  CLIENT / DASHBOARD                                         │
        │   submits runs · watches timelines · kills workers          │
        └────────────────────────────────────────────────────────────┘
                    │                                    ▲
                    │  REST                              │  WebSocket
                    ▼                                    │
        ┌────────────────────────────────────────────────────────────┐
        │  API  (FastAPI)                                             │
        │   • run submission, deduplicated on a client request key    │
        │   • admission control — global concurrency cap              │
        │   • run status, timeline, and raw log queries               │
        │   • worker fleet queries and kill commands                  │
        │   • live channel subscription and backfill                  │
        └────────────────────────────────────────────────────────────┘
                    │                                    ▲
                    ▼                                    │
        ┌────────────────────────────────────────────────────────────┐
        │  POSTGRESQL  —  the single source of truth                  │
        │                                                              │
        │   runs           id · status · epoch · lease_expires_at ·    │
        │                  owner_worker_id · attempts · cancel_flag    │
        │   run_events     append-only log · (run_id, seq) UNIQUE      │
        │   tool_journal   idempotency_key UNIQUE · intent · result    │
        │   workers        registry · last_seen · capacity · version   │
        │   chaos_events   injected failures, for evidence             │
        │                                                              │
        │   INVARIANTS ENFORCED HERE, NOT IN APPLICATION CODE:         │
        │     • seq strictly increasing per run, no duplicates         │
        │     • writes rejected when epoch < current epoch             │
        │     • exactly one intent row per idempotency key             │
        │     • lease expiry evaluated against the database clock      │
        └────────────────────────────────────────────────────────────┘
             ▲             ▲             ▲             ▲
             │             │             │             │
        ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
        │ Worker 1│   │ Worker 2│   │ Worker 3│   │ Worker N│
        │         │   │         │   │         │   │         │
        │  claim  │   │  claim  │   │  claim  │   │  claim  │
        │  replay │   │  replay │   │  replay │   │  replay │
        │  step   │   │  step   │   │  step   │   │  step   │
        │  append │   │  append │   │  append │   │  append │
        │  renew  │   │  renew  │   │  renew  │   │  renew  │
        └─────────┘   └─────────┘   └─────────┘   └─────────┘
             │             │             │             │
             └─────────────┴──────┬──────┴─────────────┘
                                  ▼
        ┌────────────────────────────────────────────────────────────┐
        │  REDIS  —  pub/sub fan-out only, NON-AUTHORITATIVE          │
        │   run:{id}:events   →   streamed to dashboard subscribers   │
        │   fleet:telemetry   →   worker heartbeat display            │
        └────────────────────────────────────────────────────────────┘
```

### 5.1 Repository structure

```
anchor/
  core/
    events/        event types, append protocol, sequence handling
    leases/        claim, renew, expiry, fencing token enforcement
    journal/       idempotency keys, canonical serialization,
                   uncertainty-window policies
    replay/        log → in-memory context reconstruction
    determinism/   journaled clock, journaled randomness, id generation

  worker/
    loop.py        the execution loop (the heart of the project)
    admission/     per-worker concurrency limits, backpressure
    retry/         backoff, jitter, attempt caps, dead-lettering
    registry/      worker self-registration and telemetry

  runtime/
    tools/         tool registration and per-tool safety declarations
    agents/        example agent workloads used for demos and tests

  api/             FastAPI routers, WebSocket channels, serializers

  chaos/
    harness.py     orchestrates workers, runs, and injected failures
    invariants.py  the assertions that constitute the proof
    report.py      generates the published metrics

  web/             Next.js operator console

  ops/             migrations, compose files, deployment config
```

The separation of `core/` from `worker/` matters. `core/` contains the protocol — the rules about events, leases, and idempotency. `worker/` contains the loop that follows those rules. Keeping them separate is what makes the protocol independently testable, and independently testable protocol logic is what makes the invariant tests meaningful.

---

## 6. The worker loop — the execution protocol

This is the specification a coding agent should implement. Described as a procedure.

```
LOOP FOREVER:

  ── ADMISSION ────────────────────────────────────────────────────
  If this worker is at its configured concurrency limit,
  sleep briefly and restart the loop.
  (Backpressure lives here, not in the queue.)

  ── CLAIM ────────────────────────────────────────────────────────
  In ONE transaction:

    Select one run where:
        status = 'pending'
      OR (status = 'running' AND lease_expires_at < database_now())
      ORDER BY priority, created_at
      WITH row-level lock, SKIPPING rows locked by other transactions
      LIMIT 1

    If no row is returned:
        sleep with jitter, restart loop.

    Otherwise:
        increment the run's epoch            → my_epoch
        set owner_worker_id = this worker
        set lease_expires_at = database_now() + lease_duration
        set status = 'running'
        append RUN_CLAIMED
            (worker, my_epoch,
             reason: 'initial' | 'reclaimed_after_lease_expiry')

  Commit.

  ── REPLAY ───────────────────────────────────────────────────────
  Read all events for this run in sequence order.
  Rebuild the in-memory context:
      • accumulated messages and agent state
      • the index of the last completed step
      • every journaled tool result, keyed by idempotency key
      • every journaled non-deterministic value
        (recorded timestamps, random values, generated ids)

  Record replay_step_count for observability.
  Emit a REPLAY_COMPLETED marker so the dashboard can distinguish
  replayed steps from freshly executed ones.

  ── EXECUTE ──────────────────────────────────────────────────────
  WHILE the run is not complete:

     Check the cancellation flag.
        If set → finalize as 'cancelled' and exit cleanly.

     If the renewal interval has elapsed, renew the lease.
        If renewal is REJECTED because the epoch has advanced:
            → I have been fenced.
            → Discard all in-memory state.
            → Write NOTHING further.
            → Exit to the idle pool immediately.
            (Do not retry. Do not log through the run. A fenced
             worker that keeps working is the exact split-brain
             the fencing token exists to prevent.)

     Determine the next action.   [deterministic zone]

     If the action requires a non-deterministic value —
     an LLM call, a tool call, the current time, a random value:

        Compute idempotency_key =
            hash(run_id, step_index, action_name,
                 canonical_serialization(args))

        Look up the key in the tool journal:

            RESULT present   → use the stored result.
                               Do NOT execute.
                               Emit a STEP_SKIPPED_ON_REPLAY marker
                               so the dashboard can show it.

            INTENT only      → uncertainty window.
                               Apply this tool's declared policy:
                                 retry-safe   → re-execute with the
                                                key passed through
                                 reconcilable → run the reconciliation
                                                query and branch
                                 unsafe       → mark run 'needs_review',
                                                halt, surface in UI

            nothing present  → proceed:
                                 append TOOL_INTENT   (with my_epoch)
                                 execute with a per-step timeout
                                 append TOOL_RESULT   (with my_epoch)

     Append STEP_COMPLETED (with my_epoch).
     Publish the event to Redis for the dashboard.

     On step failure:
        increment the attempt count for this step
        IF attempts < max_attempts:
            append STEP_FAILED
            wait: exponential backoff with jitter
            retry the step
        ELSE:
            append RUN_FAILED
            set status = 'failed'
            move to the dead-letter view for inspection

  ── FINALIZE ─────────────────────────────────────────────────────
  Append RUN_COMPLETED.
  Set terminal status. Release the lease.
  Publish the final event.
  Return to the top of the loop.
```

### 6.1 Four subtleties that separate a correct implementation from a naive one

**Lease duration must exceed the maximum expected step duration plus the renewal interval, with margin.** If a single model call can take forty seconds, and the lease is thirty seconds with renewals every ten, then a healthy-but-slow worker will be spuriously fenced mid-step — wasting completed work and inflating replay counts. This produces an intermittent bug that is genuinely difficult to diagnose, which is exactly why being able to state the constraint demonstrates real experience.

**Step timeout and lease duration are different quantities with different jobs.** The step timeout bounds how long you will wait for an external call before giving up. The lease bounds how long other workers will wait before assuming you are dead. Conflating them is a common and consequential mistake.

**Lease renewal failure must be terminal for that worker's claim, never retried.** A rejected renewal means the epoch advanced, which means another worker now owns the run. The correct behaviour is immediate, silent withdrawal — not a retry, not an error appended to the run's log, not a warning followed by continued execution.

**The claim query must handle both new runs and expired-lease runs in one statement.** Two separate queries create a window in which a worker can pick up a run that another worker just claimed. One query, one transaction, one atomic decision.

---

## 7. Data model

**`runs`** — one row per agent run. Carries: id, agent type, input payload, client request key (for submission deduplication), status (`pending`, `running`, `completed`, `failed`, `cancelled`, `needs_review`), **epoch** — the fencing token, `lease_expires_at`, `owner_worker_id`, priority, per-run attempt count, cancellation flag, and timestamps.

**`run_events`** — the append-only log. Carries: run id, **sequence number** unique per run and strictly increasing, event type, payload, **the epoch of the writer**, worker id, and timestamp.

The unique constraint on (run_id, seq) is what makes out-of-order or duplicate appends fail loudly rather than corrupt the log silently. It is the single most important constraint in the schema.

Event types:

```
RUN_SUBMITTED        RUN_CLAIMED           REPLAY_COMPLETED
STEP_STARTED         LLM_CALLED            TOOL_INTENT
TOOL_RESULT          NONDET_RECORDED       STEP_COMPLETED
STEP_SKIPPED_ON_REPLAY                     STEP_FAILED
LEASE_RENEWED        WORKER_FENCED         RUN_COMPLETED
RUN_FAILED           RUN_CANCELLED         RUN_NEEDS_REVIEW
```

**`tool_journal`** — the idempotency ledger. Carries: idempotency key (unique), run id, step index, tool name, canonicalized arguments, argument hash, intent timestamp, result payload (nullable), result timestamp (nullable), and the resolution policy applied if the uncertainty window was entered.

**The nullable result column is what makes the three-state check possible.** Intent-without-result is a distinct, meaningful state, and the schema must be able to express it.

**`tool_registry`** — declared tools and their safety properties: name, whether the effect is naturally idempotent, whether the provider accepts an idempotency key, whether a reconciliation query exists, and the default uncertainty policy. **Declaring safety properties per tool rather than assuming a global policy is a design decision worth highlighting** — it is what lets the runtime be correct across tools with genuinely different characteristics.

**`workers`** — fleet registry. Worker id, hostname, process id, start time, last seen, current run count, capacity, and code version. Powers the fleet view and makes it possible to detect a worker that registered but never heartbeated.

**`chaos_events`** — every injected failure: type, target worker, timestamp, and the run ids affected. This turns chaos testing from an anecdote into publishable evidence.

---

## 8. API surface

```
POST   /api/runs                      submit a run (deduped on request key)
GET    /api/runs                      list with status filters
GET    /api/runs/{id}                 status, current step, owning worker
GET    /api/runs/{id}/timeline        step-level view for the UI
GET    /api/runs/{id}/events          raw log, paginated
POST   /api/runs/{id}/cancel          set the cooperative cancel flag
POST   /api/runs/{id}/resolve         resolve a needs_review run

GET    /api/workers                   fleet state
POST   /api/workers/{id}/kill         hard-exit a worker (demo + chaos)

POST   /api/chaos/start               launch a configured chaos run
GET    /api/chaos/{id}/report         invariant results and metrics

GET    /api/metrics                   throughput, recovery, replay overhead
GET    /api/health                    db reachable, fleet size, lag
WS     /ws/runs/{id}                  live event stream for one run
WS     /ws/fleet                      live worker state
```

The kill endpoint is a **first-class product feature**, not a debug affordance. It is how the system demonstrates its central claim, and it should be documented and presented as such.

---

## 9. Failure modes and how the system handles them

This table is the core of the project's interview value. Every row is a question you may be asked.

| Failure | What happens | Mechanism |
|---|---|---|
| Worker killed mid-step | Lease expires; another worker claims, replays, and continues from the last completed step | Lease expiry plus event-log replay |
| Worker stalls but is alive (GC pause, partition, suspended VM) | The stale worker is rejected on its next write, discards state, and withdraws | Monotonic epoch with write gating |
| Crash between tool intent and tool result | Run enters the uncertainty window; the tool's declared policy applies | Two-phase tool journal plus per-tool policy |
| Two workers race to claim the same run | Structurally impossible — a single locking transaction that skips rows locked elsewhere | Row-level locking with skip-locked semantics |
| Duplicate event append | Rejected by the unique constraint on (run_id, seq) | Database constraint, not application logic |
| Step fails transiently (upstream 500, timeout) | Retried with exponential backoff and jitter, up to a per-step cap | Retry at step granularity, never run granularity |
| Step fails permanently (poison input) | Run moves to `failed` and lands in the dead-letter view; it does not retry forever | Attempt cap plus dead-lettering |
| Idempotency key differs across replay | Prevented by canonical serialization; if it ever occurs, the invariant checker catches it | Canonical argument serialization plus invariant assertion |
| Agent code calls the clock directly | Replay diverges — this is why the runtime supplies journaled time and the agent contract forbids direct access | Journaled non-determinism |
| Database unavailable | Workers cannot claim or append; they back off and retry. **Nothing executes without a durable record**, which is correct — the alternative is unrecorded side effects | Fail-closed by design |
| Redis unavailable | Dashboard loses live push and falls back to polling. Execution is entirely unaffected | Redis is non-authoritative |
| Run submitted twice by a client | Deduplicated on the client-supplied request key | Idempotent submission |
| Clock skew between workers | Lease expiry evaluated against the database clock, never a worker's | Server-side time exclusively |
| Slow dashboard client on the WebSocket | Dropped from the live channel past a buffer threshold; can resubscribe and backfill from the log | Backpressure on fan-out |
| Fleet saturated | New runs stay `pending`; admission control prevents overload rather than degrading everything uniformly | Global and per-worker concurrency caps |
| Worker registers then dies immediately | Detected via stale `last_seen` in the registry and surfaced in the fleet view | Registry telemetry |

The "database unavailable" row rewards attention. Failing closed is the correct behaviour and it is a design *choice* rather than a limitation: a runtime whose entire value is durability must never execute a side effect it cannot record. Saying that out loud converts an apparent weakness into evidence of judgment.

---

## 10. The chaos harness — your proof, not your test suite

Most projects claim reliability. This one demonstrates it, continuously, with numbers.

### 10.1 What the harness does

- Launches N workers and submits M runs with a deliberate mix of step counts, tool types, and durations
- Randomly kills workers at random points at a configurable rate
- Injects artificial latency and simulated stalls specifically to trigger the fencing path
- Injects tool failures at a configurable rate to exercise retry and dead-lettering
- Injects crashes *inside the uncertainty window* to exercise every declared policy
- Runs continuously for a sustained period, not a single pass

### 10.2 The five invariants it asserts

These assertions are the product's guarantee expressed as executable checks.

1. **No duplicate side effects.** Every idempotency key appears with at most one recorded result. **This is the headline guarantee.**
2. **Log monotonicity.** Sequence numbers within a run are strictly increasing with no duplicates and no gaps.
3. **Single writer per epoch.** No two events for the same run share an epoch while carrying different worker ids.
4. **Terminal state reachability.** Every submitted run reaches a terminal state within a bounded time. Nothing is stranded.
5. **Replay determinism.** Replaying a completed run's log reproduces an identical final state.

### 10.3 The output

**The harness produces your README's headline number.** In the shape of:

> *"500 randomized worker kills across 2,000 runs and 41,000 steps — zero duplicate tool executions, zero stranded runs, median recovery 1.8 seconds, p99 recovery 4.2 seconds."*

That sentence does more for a technical reviewer than any feature list, because it is a **measured correctness claim under adversarial conditions**. Essentially no student portfolio contains one, and it is immediately recognisable to anyone who has worked on distributed systems.

Run the harness on a schedule and keep the latest results in the README. A number that regenerates is more credible than a number that was true once.

---

## 11. Testing strategy

Distinct from the chaos harness, which is proof rather than test.

**Unit tests — protocol logic in `core/`.** Idempotency key derivation, canonical serialization stability, epoch comparison, lease expiry arithmetic, replay reconstruction from a fixed log. These are pure functions and should be tested exhaustively.

**Property tests — canonical serialization.** Generate structurally equivalent argument objects with different key orderings, nesting traversals, and numeric formatting; assert the hash is identical. This is the test that protects the entire idempotency mechanism.

**Deterministic replay tests.** Take a recorded log, replay it, assert the reconstructed state matches the recorded final state exactly. Run this against logs captured from real chaos runs, including ones that involved fencing.

**Integration tests — the failure matrix.** Each row of the failure table in section 9 should have a corresponding test that induces the failure deliberately and asserts the documented handling. Turning your own failure-mode table into a test suite is unusual and reads extremely well.

**Concurrency tests — claim contention.** Many workers, one available run; assert exactly one claim succeeds. Repeat under load.

---

## 12. Observability

- **Run state distribution** over time — pending, running, failed, needs_review
- **Step throughput** — steps per second, per worker and in aggregate
- **Recovery latency** — worker death to resumption, as a distribution rather than a mean
- **Replay overhead** — mean steps replayed per resumption, and time spent replaying versus executing
- **Fencing events** — how often stale workers are rejected. A rising rate indicates a lease that is too short relative to step duration.
- **Uncertainty window entries**, broken down by resolution policy applied
- **Lease renewal latency**, since renewal latency approaching lease duration is a warning sign
- **Dead-letter volume** and the distribution of failure reasons

The fencing-rate metric is worth calling out. It is a signal about your own configuration, not just about worker health, and noticing that is the kind of operational insight that distinguishes someone who has run a system from someone who has only built one.

---

## 13. Interface design

### 13.1 Design position

Anchor is an **operator console**, and it should feel like one — closer to a flight recorder than to a dashboard. The aesthetic reference is systems tooling: precise, monospaced where alignment carries meaning, high information density, zero decoration.

Copy should name things by what the operator controls and recognizes. A run is claimed, resumed, fenced, or dead-lettered — the vocabulary in the interface must be the same vocabulary in the logs and the documentation, because that consistency is how an operator learns the system.

### 13.2 The signature element

**The live run timeline.** This is what makes Anchor demonstrable rather than merely described, and it is the one place to spend design effort.

- Each step renders as a segment sized by duration and labelled with the action
- Colour encodes state: pending, executing, completed, retried, failed, and **skipped-on-replay**
- Tool calls are visually distinct from model calls
- **The owning worker id appears on every segment.** This is the crucial detail — when a worker dies mid-run, the timeline visibly changes hands. Steps 1 through 5 read `worker-a`; steps 6 through 10 read `worker-c`. The handoff is the entire story and the UI must make it unmissable.
- A fencing event renders as an explicit marker on the track, not as a buried log line
- Steps skipped because their idempotency key already carried a result are rendered distinctly, so **"the tool did not run twice" is visible rather than asserted**

### 13.3 Page inventory

**Runs list.** Live table: id, agent type, status, current step, elapsed time, owning worker, attempt count. Filterable by status, sorted with active runs first, rows updating in place over the WebSocket.

**Run detail.** The timeline as the hero, with the raw event log below it in a monospaced expandable view. Every event shows its sequence number, epoch, and writing worker. Tool intents and results are paired and collapsible. A replay indicator shows how many steps were replayed versus freshly executed on the current attempt.

**Worker fleet.** One card per worker: id, uptime, current runs, steps executed, last heartbeat age, code version — and a **kill control**. Killing a worker from the interface is a first-class feature, because it is how the product demonstrates itself.

**Chaos console.** Configure and launch a chaos run — worker count, kill rate, latency injection, failure injection, duration — then watch the invariant panel live: duplicate executions (must read zero), stranded runs (must read zero), recovery time distribution, replay overhead.

**This page is the project. It is what you show first.**

**Dead letter.** Runs that exhausted retries or entered `needs_review`, each with its full log, the failing step highlighted, and — for uncertainty-window cases — the specific ambiguous tool call with the reconciliation options available and a resolution action.

### 13.4 Motion

Functional only, and almost invisible except where it conveys a state change.

- New events slide into the timeline as they arrive
- A run that loses its worker enters a visibly distinct "orphaned" state before being reclaimed — **do not hide this gap.** The two-second stall followed by a new worker taking over is the single most persuasive moment in the entire demo, and smoothing it over would destroy the thing you built.
- Invariant counters animate only when they change

### 13.5 Empty and failure states

- **No runs yet** → an invitation, not a void. One-click examples: a short run, a long run, and a run containing a deliberately unsafe tool so the reviewer can see the `needs_review` path.
- **Database unreachable** → state plainly that execution is halted deliberately to avoid unrecorded side effects. This turns a failure state into a demonstration of the design philosophy, which is a rare and memorable thing for an error screen to do.

---

## 14. Metrics to publish in the README

- Total runs and total steps executed
- Worker kills injected, and duplicate tool executions observed (target: zero)
- Median and p99 recovery time from worker death to resumption
- Replay overhead: mean steps replayed per resumption, and mean replay latency
- Throughput as a function of worker count, showing the scaling curve
- Lease renewal latency distribution
- Percentage of runs that entered the uncertainty window, and how each was resolved

**Generate the scaling curve deliberately.** "Throughput scales near-linearly from one to eight workers" invites the obvious follow-up — where does it stop scaling? — and the answer is the single Postgres writer. Have the remediation ready too: partition the log by run id, or move to a per-shard writer. Knowing your own bottleneck and its fix is a strong signal.

---

## 15. Build order

| Phase | Deliverable | Why here |
|---|---|---|
| 1 | Submit a run via the API; one worker executes a hardcoded three-step agent; every step appended to the event log | Establishes the log as the spine before any complexity exists |
| 2 | **Replay.** Kill the worker mid-run, restart it, verify it resumes from the correct step with correct context | **This is the moment the project becomes real. Do not proceed until it is clean.** |
| 3 | Multiple workers, skip-locked claiming, leases, heartbeat renewal | Introduces concurrency |
| 4 | Fencing tokens and the epoch write gate. Deliberately construct a zombie-worker scenario and prove the stale worker is rejected | The hardest and most valuable phase |
| 5 | Two-phase tool journal, canonical argument hashing, per-tool uncertainty policies | The "no double email" guarantee |
| 6 | Retry with backoff, dead-lettering, cooperative cancellation, admission control | Production-shaped behaviour |
| 7 | Operator console — runs list, run timeline, worker fleet, kill control | Makes it demonstrable |
| 8 | Chaos harness with invariant assertions; generate the headline numbers | The proof |

**Budget generously for phases 4 and 5.** Concurrency bugs are intermittent, resistant to reproduction, and hard to reason about. That difficulty is precisely why the project is impressive, and precisely why it will take longer than the phase count suggests. Plan for it rather than being surprised by it.

**Do not build the dashboard before phase 4.** A beautiful console over a runtime that hasn't been proven correct is effort spent in the wrong place, and the temptation to do it is strong because the dashboard is more immediately satisfying to build.

---

## 16. Definition of done

The project is finished when all of the following are true:

1. It is deployed with three or more always-on workers, and a reviewer can kill one from the interface and watch recovery happen
2. The README opens with a short screen recording of exactly that, then the chaos numbers, then the architecture
3. The five invariants are implemented as assertions and pass under sustained chaos
4. The failure matrix in section 9 has integration test coverage
5. Failure and empty states are handled visibly and honestly
6. **You can whiteboard the fencing token mechanism — the zombie timeline, why the epoch must be monotonic, and why the check must live in the database — cold, without notes**

Item six is the real bar.

---

## 17. How this reads to a technical reviewer

### 17.1 The resume entry

> **Anchor — Durable Execution Runtime for AI Agents**
> Python · FastAPI · PostgreSQL · Redis · Next.js · Docker
>
> - Built an event-sourced execution engine checkpointing agent runs at step granularity, enabling automatic recovery from worker failure with median resumption in [X] seconds and no re-execution of completed work.
> - Implemented effectively-once tool execution via a two-phase idempotency journal with canonical argument hashing and per-tool uncertainty policies, verified across [N] randomized worker kills with zero duplicate side effects.
> - Designed lease-based work distribution with monotonic fencing tokens and skip-locked claiming, eliminating split-brain execution from stalled workers without any external coordination service.
> - Built a chaos harness enforcing five continuous invariants (no duplicate effects, log monotonicity, single-writer-per-epoch, terminal-state reachability, replay determinism) and an operator console visualizing run handoff between workers in real time.

Every clause names a specific distributed-systems mechanism. A reviewer who knows the field recognizes every term. A reviewer who doesn't recognizes that the vocabulary is unusual for a student.

### 17.2 The interview conversations this earns you

- **"Explain exactly-once semantics."** You can correct the premise — true exactly-once is impossible — and explain what you actually built, why the distinction matters, and how the uncertainty window is handled per tool.
- **"How do you handle a node that appears dead but isn't?"** Fencing tokens, with the zombie timeline drawn out step by step.
- **"Why Postgres instead of Kafka?"** Transactional coupling of claim, epoch, lease, and append in one statement. A genuinely senior answer.
- **"What breaks when you add more workers?"** The single-writer bottleneck, plus how you'd shard the log by run id.
- **"How do you make replay work when LLM outputs are non-deterministic?"** The determinism boundary, and the constraint it places on agent code.
- **"What was your hardest bug?"** Most likely spurious fencing caused by a lease shorter than a step, or an idempotency key that varied across replay due to non-canonical serialization. Both are specific, hard-won, and instantly credible.
- **"How do you know it works?"** The chaos harness and its five invariants. This is the strongest possible answer to that question and most candidates cannot give one.

### 17.3 Weaknesses to preempt rather than hide

- **Single region, single database.** Don't claim otherwise. Frame it accurately: correctness under partial failure within a fleet, not global distribution. Have the sharding answer ready.
- **You did not invent the category.** Name Temporal and Restate unprompted. Positioning your work relative to known prior art reads as maturity; implied novelty reads as naivety and invites a correction you don't want.
- **The agent workloads are simple.** Intentionally so, and say it: the runtime is agnostic to the agent, and a complex agent would obscure the mechanism being demonstrated rather than showcase it.
- **Throughput is modest.** Correct, and irrelevant. The claim is correctness under failure, not scale. Do not let the conversation drift onto an axis where the project isn't trying to compete.

---

## 18. Scope discipline

**Cut list — things that feel valuable here and are not:**

- Authentication, multi-tenancy, teams, or billing. Not the point, and each one dilutes the demo.
- Support for multiple agent frameworks. The runtime is framework-agnostic by design; proving it against two frameworks adds no signal over proving it against one.
- A visual workflow builder. Enormous effort, no relevance to the guarantee being demonstrated.
- Kubernetes. A handful of processes on a managed platform is entirely adequate, and reaching for orchestration here reads as resume-driven architecture — the opposite of the signal you want.
- Distributed tracing integration. Nice, but the run timeline already is your trace.

**Add only if you finish early:**

- **Human-in-the-loop pause and resume.** A run that suspends awaiting approval and resumes days later is a natural extension of durable execution and demos extremely well.
- **Scheduled and recurring runs**, which turn the runtime into something you'd actually deploy.
- **A written design document** in the repository covering the tradeoffs, the alternatives you rejected, and the known limitations. Cheap to produce, extremely rare in student repositories, and it is the artifact a senior reviewer is most likely to actually read.

---

## 19. Glossary

Worth including in the repository README, because the vocabulary is the project.

| Term | Meaning in Anchor |
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
| **Determinism boundary** | The line between logic that is re-executed on replay and values that are read back from the log |
| **Dead letter** | Terminal state for runs that exhausted retries or need human resolution |

---

## 20. Final note

The specification is complete. The protocol is defined, the invariants are stated, and the build order is sequenced by dependency rather than by appeal.

Build to phase 2 first — a worker that dies mid-run and resumes correctly. Everything else in this document is elaboration on that single behaviour, and until it works, nothing else in the system means anything.
