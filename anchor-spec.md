# Anchor — Technical Specification & Build Audit

**Document type:** Standalone product and engineering specification, written for spec-driven development.
**Version:** 1.2 — adds Addendum D (developer adoption path, authoring surface, recorded cuts) and Addendum E (canonical page inventory, deployment-mode capability matrix, outbound surface).
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
| Frontend | React with Vite, TypeScript, and a WebSocket client | The dashboard is a real-time observability surface, not a CRUD screen, and should be built as one. |
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

  web/             React + Vite operator console

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

GET    /api/agents                    registered agents and their contracts
GET    /api/tools                     tool registry with safety categories
GET    /api/runs/{id}/effects         demo_effects rows for this run (§21.5)

                                      — authoring surface, §27 —
POST   /api/authoring/validate        static-check a draft against the
                                      agent contract; ALWAYS available
POST   /api/authoring/generate        LLM draft from a description;
                                      ALWAYS available, returns text only
POST   /api/authoring/register        load a draft into the live registry;
                                      LOCAL DEPLOYMENT MODE ONLY (§27.3)
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

### 13.3 Navigation and page inventory

Anchor follows the navigational pattern of Render and Vercel: **a persistent left sidebar with grouped sections**, rather than a flat handful of top-level pages.

The reason is positioning rather than function. A product with five pages reads as a single-screen demo; a product with a grouped sidebar reads as an operator console with real surface area. The runtime underneath is identical either way — but the perceived scope is not, and perceived scope is what a reviewer forms an opinion about in the first ten seconds.

#### The sidebar

Present on every page. Three zones, top to bottom.

**Zone 1 — workspace switcher, pinned at the top.** A project or workspace selector. **This slot exists even though there is only one project**, because it is what makes the product read as built for multiple projects rather than as a one-off. It need do nothing beyond naming the current workspace and showing that the concept exists. It does not reintroduce the accounts and multi-tenancy that §18 cuts — it is a navigational affordance, not a tenancy boundary.

**Zone 2 — seven grouped sections**, detailed below.

**Zone 3 — a Docs link, pinned at the bottom** and separated from the groups by a divider. Links out to the written design document of §18 — the artifact a senior reviewer is most likely to actually read, which is reason enough to give it permanent placement rather than burying it in a footer.

| Group | Pages |
|---|---|
| Overview | Dashboard |
| Runs | All runs · Needs review · Scheduled |
| Workers | Fleet · Deployments |
| Chaos | Console · History |
| Tools | Registry · Test run |
| Observability | Metrics · Logs |
| Settings | Environment · API keys · Webhooks |

#### Overview

**Dashboard.** Fleet health at a glance: active run count, a live sparkline of step throughput, and any recent duplicate-side-effect alerts, which read zero. Per §22.5 the throughput sparkline belongs inside a stat tile rather than as its own chart, and the duplicate count is the one figure permitted to be large here.

This is the console's landing page. **It is not the same page as the public landing surface of §21.3** — since §21.7 establishes there is no login, the two coexist: the persuasion layer at the root path for a cold visitor, and this dashboard as the console's own entry point once they cross into the instrument layer. Do not merge them; they have different jobs and different readers.

#### Runs

**All runs.** The primary list view. Live table: id, agent type, status, current step, elapsed time, owning worker, attempt count. Filterable by status — pending, running, completed, failed, needs_review — sorted with active runs first, rows updating in place over the WebSocket. **Each row carries the compact thread strand of §24.3** as a visual summary, so a reader can see at a glance which runs changed hands. Per §24.8 the compact strand does not identify *which* workers touched a run, so the owning-worker column stays.

**Needs review.** Dead-lettered and ambiguous runs — those that exhausted retries, and those that entered the uncertainty window of §3.3 and could not be resolved automatically — surfaced as **their own page rather than only as a filter on the main list.** Each entry carries its full log, the failing step highlighted, and for uncertainty-window cases the specific ambiguous tool call with the available reconciliation options and a resolution action.

**Scheduled.** Recurring or delayed runs. Forward-looking: **build this page only if the recurring-run feature of §18 gets built.** Until then the group has two pages and the sidebar shows two.

#### Workers

**Fleet.** One card per worker: id, uptime, current runs, steps executed, last heartbeat age, code version — and a **kill control**. Killing a worker from the interface is a first-class feature, because it is how the product demonstrates itself. Unchanged from the previous inventory; only its location in the navigation has moved.

**Deployments.** Which code version each worker is currently running, presented as a deploy-history-style list. Lets an operator see "three workers on v12, one still on v11" at a glance. **Populated entirely from the `version` column already defined on the `workers` table in §7** — no new schema, no new instrumentation, no new writes. It also answers a question the fleet view cannot: whether an in-flight run is being resumed by a worker running different code than the one that started it, which is a genuinely interesting durability question to be able to ask.

#### Chaos

**Console.** The chaos configuration and live-launch page: worker count, kill rate, latency injection, failure injection, duration — then the invariant panel live, showing duplicate executions (must read zero), stranded runs (must read zero), recovery time distribution, and replay overhead. Content unchanged; only relocated under this group.

**This page is the project. It is what you show first.**

**History.** Every past chaos run with its final invariant report preserved permanently — duplicate executions, stranded runs, recovery time distribution — rather than visible only while the run is live.

**Why this page matters more than its size suggests.** It converts the chaos harness from a one-time demonstration into an **accumulating, inspectable body of evidence.** A reviewer can scroll back through weeks of runs and see that the invariants held every time, which is a materially stronger claim than one successful demo. Section 10.3 already argues that a number which regenerates is more credible than a number that was true once; this page is that argument given a surface. It carries a second, quieter signal too: a system that preserves every past result is one that could not have quietly discarded a bad one.

#### Tools

**Registry.** Every tool in the `tool_registry` table of §7: name, declared safety category — retry-safe, reconcilable, or unsafe — and last-used timestamp. This page makes the per-tool policy decision of §3.3 visible rather than buried in configuration, and that decision is among the design choices most worth highlighting.

**Test run.** Submit a one-off synthetic task through a simple form, without writing code. Useful for manual verification during development, and for demos where a specific step count or tool mix is wanted rather than whatever the preset produces.

**Authoring.** The editor and draft generator of §27. On the public instance this page is author-and-validate only — it teaches the agent contract and proves the validator works, but cannot execute. On a local instance it additionally registers and runs. The page states which mode it is in, in the header, at all times.

#### Observability

**Metrics.** The §12 metrics visualized rather than merely tracked: throughput, recovery latency, replay overhead, and fencing rate over time. Chart forms, color assignment, and the no-dual-axis rule per §22.5.

**Logs.** A searchable view across the raw event log for **all** runs, filterable by event type, worker, epoch, and time range. Distinct from the per-run event log on the run-detail page, which stays scoped to one run.

#### Settings

**Environment.** Lease duration, per-step retry limits, and worker concurrency caps, **editable live without a redeploy.**

This is a deliberate design choice and worth stating as one. Section 6.1 establishes that lease duration must exceed the maximum expected step duration plus the renewal interval, and that getting it wrong produces spurious fencing — an intermittent bug that is genuinely hard to diagnose. An operator who can retune the lease while watching the fencing-rate metric of §12 closes that loop in seconds. Requiring a redeploy to change it would make this console documentation rather than tooling, which is the distinction the whole page inventory is trying to land.

**API keys.** For programmatic run submission. Keys authenticate a caller against the API; they are not user accounts and do not reintroduce the auth cut in §18 and §21.7.

**Webhooks.** Notify an external URL on run completion or failure. Cheap and genuinely useful: it reuses the `RUN_COMPLETED` and `RUN_FAILED` event types already defined in §7, so the implementation is a subscriber on the existing log rather than new machinery.

#### Why this structure

Four of these choices are doing more work than they appear to.

**Separating Needs review from the main run list** mirrors how deploy tools isolate failures instead of burying them behind a filter. A failure reachable only by selecting a dropdown value is a failure that goes unnoticed, and for this product the ambiguous-run case is the one most worth noticing — it is where the system admits what it does not know, which is the most credible thing it does.

**Deployments under Workers costs nothing extra**, since worker version is already tracked in §7, and it gives a real answer to "which code is actually running right now" — a question every operator eventually asks and most consoles cannot answer.

**Chaos History converts the harness's output from a demo into an asset.** The proof stops being an event that happened and becomes a record that accumulates.

**Live-editable Environment settings is what makes the console read as operational tooling** rather than a static demo. It is also the page that most directly reflects §6.1's hard-won constraint about lease duration, which means it doubles as evidence that the constraint was understood.

#### Page count is not build priority

**This expanded inventory does not change the build order of §15.** The chaos console and the run-detail view remain the priority builds. Every page added here — Deployments, Chaos History, Tools Registry, Test run, Metrics, Logs, Environment, API keys, Webhooks — is a UI shell over data that already exists, and all of it can be built last, after the runtime and its proof are working, exactly as phase 7 already implies. **Do not read a longer sidebar as a longer critical path**, and do not build any of it before phase 4.

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
| 9 | *(stretch)* The authoring surface of §27 — contract editor, validator, draft generator | Strictly additive. It improves the developer story; it proves nothing the runtime does not already prove. Build it only if phases 1–8 are done. |

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
> Python · FastAPI · PostgreSQL · Redis · React (Vite) · Docker
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
- **A consumer-facing storefront** wrapping a single flagship agent. Considered and cut in §28.2. It reframes an infrastructure project as a product project and softens exactly the vocabulary that makes the runtime legible to a technical reviewer.
- **A no-code agent builder for non-developers.** Considered and cut in §28.2. It puts the project in competition with mature workflow-automation products on their strongest axis while abandoning its own.
- **Branching / fork-from-checkpoint.** Considered and cut in §28.3 on prior-art grounds. It is a native feature of at least one widely-used agent framework and a shipped commercial product; implementing it buys no differentiation and adds replay-coherence risk.
- **Executing visitor-authored code on the public instance.** Cut on security grounds in §27.3. This is remote code execution, and the mitigation is deployment-mode gating, not sandboxing.

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

---
---

# Addendum A — The self-explanatory surface and the visual system

**Addendum version:** 1.1
**Status:** Additive. Nothing in sections 0–20 is retracted. Where this addendum refines an earlier statement, it says so explicitly and gives the reason.
**Scope note:** Sections 21–23 specify the surface a reviewer meets in the first ten seconds, and the visual system that carries it. Section 13 remains authoritative for the dense operational views; this addendum governs the explanatory layer above them and the design tokens beneath them both.

---

## 21. The landing surface — the project must explain itself

### 21.1 The problem this section solves

Sections 0–20 describe a system that is correct. They do not describe a system that is *legible to someone who has never heard of it*. Those are different problems, and the second one is what determines whether the first one is ever noticed.

The reviewer arriving at the deployed URL has no context. They have not read this document. They will not read a wall of prose. They have somewhere between ten and ninety seconds of patience, and in that window they must arrive at three conclusions, in order:

1. **"I understand what this does."**
2. **"I just watched it do the hard thing."**
3. **"The hard thing is measured, not claimed."**

If the landing surface delivers those three, every remaining page is a reward for interest already earned. If it doesn't, the chaos console and the invariant assertions are never reached, and the engineering in them counts for nothing.

**The governing rule for this section:** the landing surface must require **zero prior knowledge and zero reading** to produce conclusion 2. Explanation is a fallback for the curious, not the primary channel. The primary channel is a thing happening on screen.

### 21.2 Reconciling this with section 13

Section 13.1 sets the design position as "closer to a flight recorder than to a dashboard," with "zero decoration." Section 13.4 requires motion to be "functional only, and almost invisible." Taken literally and applied to the landing surface, those instructions produce something correct and unreadable.

**The resolution is two layers with different jobs, not a compromise between them.**

```
┌─────────────────────────────────────────────────────────────────┐
│  THE PERSUASION LAYER          — landing / overview / demo       │
│                                                                   │
│    Job: comprehension in ten seconds, for a cold reader.         │
│    Permitted: large type, a hero figure, an animated             │
│      explainer, generous whitespace, deliberate motion,          │
│      a guided call to action.                                    │
│    Still forbidden: gradient washes, glassmorphism, decorative   │
│      illustration, marketing copy, anything that moves           │
│      without carrying information.                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │  one click, no friction
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  THE INSTRUMENT LAYER          — runs, timeline, fleet, chaos,   │
│                                  dead letter                     │
│                                                                   │
│    Job: operational density for a reader who is now invested.    │
│    Section 13 governs here, unchanged: monospaced where          │
│      alignment carries meaning, high information density,        │
│      motion only where it conveys a state change.                │
└─────────────────────────────────────────────────────────────────┘
```

**"Flashy" is defined here as high production value, never as decoration.** The distinction is load-bearing and worth stating precisely, because it is the difference between a console that reads as professional tooling and one that reads as a student project with a template bolted on:

| Reads as FAANG-grade | Reads as a template |
|---|---|
| Live data moving on screen | Gradient hero background |
| A number counting up because a run completed | A number counting up on page load for effect |
| One hero figure, enormous, in the same typeface as everything else | Three competing display fonts |
| Motion that marks a state transition | Motion on scroll, on hover, on everything |
| Whitespace and alignment doing the work | Borders, shadows, and glass panels doing the work |
| A dense table that is genuinely readable | A dense table with a decorative header |

The most persuasive thing this project can put on a screen is **its own live state**. That is free, it is unfakeable, and no amount of visual styling competes with it.

### 21.3 The landing page, top to bottom

One scrolling page. Every band earns its place by advancing one of the three conclusions.

```
╔═══════════════════════════════════════════════════════════════════╗
║  BAND 1 — THE CLAIM                                    (no scroll) ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║   Anchor keeps AI agents running when the machine                  ║
║   executing them dies.                                             ║
║                                                                    ║
║   Agent runs are stored as an append-only log in Postgres,         ║
║   not in a process's memory. Kill a worker mid-run and             ║
║   another resumes from the exact step it stopped on —              ║
║   without re-sending the email it already sent.                    ║
║                                                                    ║
║   ┌──────────────────────────────┐  ┌───────────────────────────┐  ║
║   │  ▶  Run the example agent    │  │  Read the design doc  →   │  ║
║   └──────────────────────────────┘  └───────────────────────────┘  ║
║                                                                    ║
║   ● 3 workers online   ·   1,284 runs   ·   0 duplicate effects    ║
║     └── live, from /api/health and /api/metrics ──┘                ║
╚═══════════════════════════════════════════════════════════════════╝
```

Two sentences. The first states the outcome in language requiring no distributed-systems vocabulary. The second names the mechanism and lands on the concrete consequence — *the email it already sent* — because that image does more work than the word "idempotency" ever will.

**The live status strip is the most important element in this band.** Three real numbers, polled from the existing `/api/health` and `/api/metrics` endpoints, proving before any interaction that this is a running system rather than a repository with a screenshot. If the fleet is degraded it says so — a strip that can report bad news is the reason to believe it when it reports good news.

```
╔═══════════════════════════════════════════════════════════════════╗
║  BAND 2 — THE MECHANISM, ANIMATED                                  ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║        worker-a                              worker-c              ║
║       ┌────────┐                            ┌────────┐             ║
║       │  ▓▓▓   │  ✕ killed at step 6        │        │            ║
║       └────┬───┘                            └───▲────┘             ║
║            │ appends each step                  │ reads the log    ║
║            ▼                                    │ resumes at 6     ║
║       ┌────────────────────────────────────────────────┐           ║
║       │  ▓▓ ▓▓ ▓▓ ▓▓ ▓▓ ░░ ░░ ░░ ░░ ░░   run_47 log   │            ║
║       │   1  2  3  4  5  6  7  8  9 10                 │           ║
║       └────────────────────────────────────────────────┘           ║
║                     Postgres — the source of truth                 ║
║                                                                    ║
║   A three-beat loop, ~6s, pausing on the handoff.                  ║
╚═══════════════════════════════════════════════════════════════════╝
```

A single looping animation, three beats: worker-a executing and appending; worker-a dying with the log intact; worker-c reading the log and continuing from step 6. It holds for roughly a second on the handoff, because the handoff is the entire idea.

Constraints: **SVG or CSS, hand-built, no animation library, no video file.** It must be under a few kilobytes, must not autoplay audio, must respect `prefers-reduced-motion` by falling back to the third beat as a static frame with the transition labelled, and must be captionable so that it is comprehensible with the animation disabled. This is an explanatory diagram that happens to move — the movement carries the causal sequence, which is exactly the case where motion is information rather than decoration.

```
╔═══════════════════════════════════════════════════════════════════╗
║  BAND 3 — THE GUIDED DEMO                                          ║
╠═══════════════════════════════════════════════════════════════════╣
║   The four-step walkthrough of §21.4, rendered inline.             ║
║   This band is the product. Everything above it is preamble.       ║
╚═══════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════╗
║  BAND 4 — THE EVIDENCE                                             ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║              0                                                     ║
║              duplicate tool executions                             ║
║              across 517 injected worker kills                      ║
║                                                                    ║
║   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐     ║
║   │ Runs       │ │ Steps      │ │ Median     │ │ Stranded   │     ║
║   │ 2,041      │ │ 41,388     │ │ recovery   │ │ runs       │     ║
║   │ ▁▂▃▅▇▆▇    │ │ ▂▃▄▆▇▇▇    │ │ 1.8s       │ │ 0          │     ║
║   └────────────┘ └────────────┘ └────────────┘ └────────────┘     ║
║                                                                    ║
║   Last chaos run: 4h ago, 30 min sustained   ·   Full report →     ║
╚═══════════════════════════════════════════════════════════════════╝
```

The hero figure is the zero. It is the only hero figure in the entire product (§22.5), and it is the sentence from §10.3 rendered as a number instead of a claim. **It must be generated by the chaos harness and timestamped**, because a number with a "last run: 4 hours ago" beside it is evidence, and the same number hardcoded is a decoration that a reviewer will assume is hardcoded.

```
╔═══════════════════════════════════════════════════════════════════╗
║  BAND 5 — THE ARCHITECTURE, AND THE HONEST PART                    ║
╠═══════════════════════════════════════════════════════════════════╣
║   The §5 diagram, rendered rather than ASCII, with the four        ║
║   invariants called out where they are enforced.                   ║
║                                                                    ║
║   Then, in plain type and not hidden:                              ║
║     · This is durable execution in the Temporal lineage,           ║
║       scoped to agent runs.                                        ║
║     · True exactly-once is impossible. This is at-least-once       ║
║       with idempotent effects, plus a declared policy per tool     ║
║       for the uncertainty window.                                  ║
║     · Single region, single Postgres writer. Here is where         ║
║       it stops scaling, and here is how it would shard.            ║
╚═══════════════════════════════════════════════════════════════════╝
```

Band 5 puts §1.5 and §17.3 on the page rather than saving them for an interview. A landing page that names its own prior art and states its own ceiling is doing something almost no portfolio project does, and it converts the two most likely objections into evidence of judgment before they are ever raised.

### 21.4 The guided demo — the interaction that has to land

This is the load-bearing sequence. It must work on a first visit, with no configuration, no account, and no reading. Four steps, each one click.

```
STEP 1  ─  "Run the example agent"
           One click submits a real run of the demo agent (§21.5).
           No form. No options. No modal.
           → The timeline appears inline, already populating.

STEP 2  ─  Steps land in real time over the WebSocket
           Each segment labelled with its action and its worker id.
           Every segment reads worker-a. This uniformity is
           deliberate: it is the baseline the next step breaks.

STEP 3  ─  A single highlighted control appears mid-run:
           ┌──────────────────────────────────────────────┐
           │  ✕  Kill worker-a                            │
           │     It is executing step 6 of this run.       │
           │     Watch what happens.                       │
           └──────────────────────────────────────────────┘
           This calls the real POST /api/workers/{id}/kill.
           It is not a simulation, and the UI should say so.

STEP 4  ─  The payoff, and it must NOT be smoothed over:
             · the timeline stalls, visibly, and is labelled
               "orphaned — lease expiring"
             · a countdown shows the lease expiry, so the pause
               reads as a designed interval rather than a bug
             · a new segment appears reading worker-c
             · steps 1–5 are marked "replayed from log — not
               re-executed"
             · a line of copy states the conclusion outright:
               "Steps 1–5 were read back from the log. The tool
                calls in them did not run a second time."
```

Four notes on why this is specified this tightly:

**The countdown during the stall converts the worst moment into the best one.** Section 13.4 correctly insists the two-second gap must not be hidden. But an unexplained pause reads as a broken page to someone who does not yet know what they are watching. A countdown labelled "lease expires in 1.4s" tells the reviewer the pause is the mechanism working. The gap stays fully visible — it is *narrated*, not smoothed.

**Step 4 must state its own conclusion in words.** The visual distinction between replayed and freshly-executed segments (§22.4) is the proof, but a reviewer seeing this interface for the first time has not yet learned the encoding. One sentence of copy makes the proof self-interpreting. This is the single highest-value sentence in the product.

**The kill must be real.** A simulated kill is worthless, and a reviewer will suspect simulation by default. Label the button with the endpoint it calls and let them find the same worker gone from the fleet page.

**Nothing in this sequence may require the reviewer to navigate.** The demo runs inline on the landing page. The dedicated run-detail, fleet, and chaos pages of §13.3 exist unchanged for the reviewer who now wants depth — but the first proof must not cost a page load.

### 21.5 The demo agent — deliberately small, deliberately honest

The workload exists to make the runtime legible. Section 17.3 already commits to saying this out loud: a complex agent would obscure the mechanism rather than showcase it.

| Property | Specification | Reason |
|---|---|---|
| Steps | 8–10 | Enough for a mid-run kill to have visible history behind it and visible work ahead of it |
| Total duration | 25–40 seconds | Long enough to kill a worker in the middle; short enough to watch the whole thing without losing interest |
| Step duration | 2–5s, deliberately varied | Uniform steps make the timeline look synthetic; varied ones make duration-sized segments meaningful |
| Model calls | Stubbed by default, with fixed latency and canned responses | The runtime's claim is about durability, not model quality. A stub removes API keys, cost, rate limits, and non-determinism from the demo path — and the determinism boundary of §3.2 means the runtime cannot tell the difference. **State this on the page.** |
| Tool calls | Fake but named after real consequential actions — `web_search`, `fetch_page`, `send_email` | `send_email` is what makes the double-execution risk intuitive without a word of explanation |
| Tool mix | At least one `retry-safe`, one `reconcilable`, and one `unsafe` | So all three uncertainty policies of §3.3 are reachable from the UI |
| Side effect | Writes to a `demo_effects` table, one row per execution | **This is the proof surface.** The row count is the ground truth for "it ran once." Show it. |

**The `demo_effects` table is not an implementation detail — it is the strongest evidence in the product.** A counter reading `send_email executed: 1 time` beside a timeline showing the run was interrupted and resumed is a claim a reviewer can verify without trusting the log. Surface it in step 4 of the guided demo.

Three one-click presets on the empty state, per §13.5, now specified:

| Preset | Shows |
|---|---|
| **Short run** — 8 steps, ~30s | The happy path and the guided kill |
| **Long run** — 40 steps, several minutes | Replay overhead at a scale where it is measurable, and a run that survives multiple kills |
| **Unsafe-tool run** — crashes inside the uncertainty window | The `needs_review` path and the dead-letter resolution UI. **The one that proves the system knows what it does not know** — and the one most likely to genuinely impress, because handling ambiguity honestly is rarer than handling failure. |

### 21.6 Self-sufficiency and shared-instance discipline

Section 0 establishes that the system generates its own workload. Making the deployment survive public, unauthenticated use requires four things that are worth specifying, because each one is a small engineering decision that reads well:

**Workers must respawn automatically.** The kill endpoint hard-exits the process; the platform restarts it. A reviewer who kills all three workers must find three workers again within seconds. **A demo that a visitor can permanently break is not a fault-tolerant runtime.** Render's own process supervision does this — the point is that killing workers is safe *because* the fleet is self-healing, which is the same property the product claims.

**Submission is capped and cheap.** A global concurrency cap already exists in §5 admission control. Add a rate limit on submission by IP and a hard cap on demo runs per hour. Stubbed model calls mean an abusive visitor costs compute, not money.

**Nothing destructive is exposed.** Kill a worker: yes, it is the product. Cancel a run, resolve a `needs_review`: yes, scoped to demo runs. Drop data, mutate another visitor's run, or alter chaos history: never. The kill endpoint should also be rate-limited — not for safety, but so the fleet view stays readable.

**A reset affordance exists.** "Clear demo runs" prunes completed demo runs so the runs list stays legible. It must never touch chaos-harness history, because that history is the published evidence.

### 21.7 Explicitly out of scope: accounts and per-user state

**Anchor has no authentication, no accounts, no login, and no per-user data.** Section 18 already cuts these; this section restates it because the landing surface is exactly where the temptation to add them appears.

The reasoning, stated once so it does not have to be relitigated:

- The product is a **demonstration instance**, not a multi-tenant service. Its user is one reviewer at a time.
- Auth adds real work — sessions, isolation, an account UI, a password reset path — and contributes nothing to either of the two guarantees the project exists to prove.
- It actively harms the demo. A login wall between a reviewer and the guided demo of §21.4 will lose a meaningful fraction of reviewers outright, and every one lost is a total loss.
- The engineering hours it would consume are the same hours phases 4 and 5 need, and §15 already warns those will overrun.

If per-visitor continuity is ever wanted, the cheap version is `localStorage` holding the ids of runs this browser submitted, so the runs list can offer a "runs you started" filter. **No server-side identity, no database column, no auth.** This is a nice-to-have well below the §18 add-only-if-finished-early line.

---

## 22. The visual system

Design tokens and mark specifications, so that the interface reads as one system rather than as a sequence of independently styled pages. **The palette below was validated with a colorblind-safety and contrast validator before being written down; the measured numbers are quoted inline, and three of them changed the design.** Where a value is a deliberate exception to a general rule, the exception and its mitigation are stated together.

### 22.1 Surfaces, ink, and mode

**Dark-first**, because the reference class is systems tooling and because the timeline's colored segments carry more separation against a dark surface. A light mode is optional; if built, it is a **selected** set of values validated against the light surface, never an automatic inversion.

| Role | Dark (primary) | Light (if built) |
|---|---|---|
| Page plane | `#0d0d0d` | `#f9f9f7` |
| Panel / chart surface | `#1a1a19` | `#fcfcfb` |
| Primary ink | `#ffffff` | `#0b0b0b` |
| Secondary ink | `#c3c2b7` | `#52514e` |
| Muted — axis, labels, pending | `#898781` | `#898781` |
| Gridline — hairline, solid, never dashed | `#2c2c2a` | `#e1e0d9` |
| Baseline / axis | `#383835` | `#c3c2b7` |
| Hairline ring | `rgba(255,255,255,0.10)` | `rgba(11,11,11,0.10)` |

Every contrast and colorblind-separation figure in this section was measured against the `#1a1a19` panel surface. **If the surface changes, the palette must be re-validated** — these numbers are only meaningful against the surface the interface actually renders on.

### 22.2 Typography

Two families, no more. A third reads as decoration and is the fastest way to make a console look amateur.

| Use | Family | Notes |
|---|---|---|
| UI — labels, prose, headings, stat values, the hero figure | `system-ui, -apple-system, "Segoe UI", sans-serif` | Including the hero figure. A display or serif face on the big number reads as off-brand decoration. |
| Data — run ids, worker ids, epochs, sequence numbers, event payloads, the raw log | A monospace stack | Per §13.1: monospaced **where alignment carries meaning**. An id is compared character by character; a label is not. |

- **Proportional figures for large standalone numbers** — the hero figure and stat-tile values. `tabular-nums` gives every digit the width of a zero, which makes a number like `121` look loose at 48px.
- **`tabular-nums` only in columns that must align vertically** — table rows, axis ticks, the elapsed-time column of the runs list.
- **Never color text with a data color.** Marks carry hue; labels, values, legends, and axis text wear ink tokens. Identity comes from a colored dot or swatch *beside* the text. The one exception is a label set inside a filled segment, where white or ink is chosen by the fill's luminance so it always clears contrast.

### 22.3 The two color channels

The timeline encodes two independent things at once, and conflating them is the mistake to avoid. **Separate them by visual property, not by hue alone.**

```
CHANNEL 1 — WHO   (worker identity)   →  carried by HUE
CHANNEL 2 — WHAT  (step state)        →  carried by FILL WEIGHT + ICON + LABEL
```

**Channel 1 — worker identity.** Three hues, in fixed order, never cycled:

| Worker slot | Hue | Dark |
|---|---|---|
| 1 | blue | `#3987e5` |
| 2 | orange | `#d95926` |
| 3 | aqua | `#199e70` |

**Three slots is not an arbitrary choice — it is the validated ceiling and it happens to match the deployment.** Validated as a set against `#1a1a19` under an all-pairs comparison: worst colorblind separation ΔE 9.4 (deuteranopia), worst normal-vision separation ΔE 20.9, all three ≥ 3:1 contrast against the surface. **All checks pass.** A fourth hue does not clear the all-pairs floors, which is exactly why §4 specifies three always-on workers.

For chaos runs with more than three workers: **do not extend the hue set.** Worker ids are already direct-labelled on every segment (§13.2), so identity never depends on color. Past three workers, color by *emphasis* instead — the run's current owner in slot 1, all prior owners in muted gray — which also happens to make the handoff read more clearly than eight competing hues would.

**Channel 2 — step and run state.** Status colors, fixed, never themed, never reused as a series color:

| State | Color | Icon | Fill treatment |
|---|---|---|---|
| pending / queued | muted `#898781` | — | hollow, hairline only |
| executing | accent `#3987e5` | — | solid + slow pulse |
| completed | good `#0ca30c` | check | solid |
| **replayed from log** | worker hue @ ~10% | log glyph | **ghosted wash + hairline** |
| retried | warning `#fab219` | circular arrow | solid, repeated segment |
| failed / fenced | critical `#d03b3b` | ✕ / shield | solid |
| needs review | warning `#fab219` | question | solid, hatched edge |
| orphaned | **no fill** | — | **gap + pulsing hairline** |

Four decisions in that table came out of validation rather than taste:

**Status must always be icon + label + color, never a colored dot alone.** Measured: completed-green `#0ca30c` against failed-red `#d03b3b` is **colorblind separation ΔE 4.1 (deuteranopia)** — far below the ≥ 8 target, despite an ΔE of 33.9 for normal vision. This is the classic red/green trap, and it means **the two most important states in the product are indistinguishable by hue for a substantial fraction of readers.** The mitigation is not a different green: it is that hue is never the only channel. Every status in the runs list, the timeline, and the fleet view ships with its icon and its text label. This costs nothing and is non-negotiable.

**`serious` was removed from the state vocabulary.** The status ramp offers a fourth role between warning and critical, but measured against warning `#fab219` it is **normal-vision ΔE 13.6, below the 15 floor** — a pair that full-color readers cannot reliably tell apart. Three status levels plus muted plus the accent covers every state in §7 without asking the reader to distinguish two oranges. Removing a color that does not survive measurement is the correct response to a failed check.

**`needs_review` and `retried` share the warning hue deliberately.** They never appear in the same encoding channel — `retried` is a *step* state inside the timeline track, `needs_review` is a *run* state in the runs list and dead-letter view — and their icons differ. Both mean "a human should look at this," so the shared hue is semantically honest rather than a collision.

**`orphaned` is the absence of fill, not a color.** The most persuasive moment in the product (§13.4) is a gap where work should be happening. Filling it with a color would be a lie about what is occurring: nothing is executing. A gap with a pulsing hairline and the lease countdown of §21.4 states the truth, and the truth is more dramatic than any color.

### 22.4 The replayed-step encoding — the product's central claim, rendered

Section 13.2 requires that "the tool did not run twice" be **visible rather than asserted.** This is the mark specification that carries it.

```
      ┌──────┬──────┬──────┬──────┬──────┐░░░░░░┌──────┬──────┐
      │ ▓▓▓▓ │ ▓▓▓▓ │ ▓▓▓▓ │ ▓▓▓▓ │ ▓▓▓▓ │ gap  │ ████ │ ████ │
      └──────┴──────┴──────┴──────┴──────┘░░░░░░└──────┴──────┘
        1      2      3      4      5     orphan   6      7
      └────────── worker-a ─────────────┘        └── worker-c ──┘
      └───── ghosted: read from log ─────┘       └── solid: ────┘
             replayed, NOT re-executed              executed now
```

**Solid fill means "this executed." Ghosted fill means "this was read back from the log."** The distinction is carried by fill weight and opacity, not by hue — which means it survives grayscale, survives every form of color blindness, survives a screen recording compressed by a video codec, and survives being viewed on a bad projector in an interview room. Given that this single distinction is the visual expression of the project's headline guarantee, it must not depend on the most fragile channel available.

Rules for the track:

- **A 2px gap in the surface color separates adjacent segments** — the same width throughout. Never a border stroke around a segment; a stroke adds ink that isn't data.
- Segment width is proportional to step duration, with a floor so a 200ms step stays clickable.
- **Tool calls and model calls are shape-distinct**, not just hue-distinct — tool segments carry a notched leading edge, model segments do not.
- **A fencing event is a full-height marker on the track**, labelled, with the stale and current epoch both shown. Per §13.2 it is never a buried log line.
- The worker id rides every segment as a direct label. When segments are too narrow for it, the label moves to a continuous rail beneath the track that spans each ownership range — **never clipped with `overflow: hidden`**, which crops characters and is worse than no label.
- Hovering any segment gives a tooltip with the step index, action, duration, epoch, worker, and — for tool calls — the idempotency key and whether it was executed or replayed.

### 22.5 Figures and the metrics views

The metrics of §12 and §14 need forms. The form follows the data's job, and for several of these the right answer is not a chart.

| Data | Form | Color job |
|---|---|---|
| Duplicate tool executions | **Hero figure**, ≥48px — exactly one per view, on the chaos console and landing band 4 | status good |
| Runs, steps, kills, stranded runs, recovery median | **KPI row of stat tiles** — label, value, optional 12-point sparkline | de-emphasis gray + accent on current period |
| Run state distribution over time | **Stacked area**, states as series | the §22.3 status colors — semantic, not decorative |
| Recovery latency distribution | **Histogram** | sequential blue, one hue |
| Lease renewal latency distribution | **Histogram** | sequential blue, one hue |
| Throughput vs worker count | **Line, single series**, plus a dashed muted reference line for ideal-linear | one hue + gray — the emphasis form |
| Fencing events over time | **Sparkline** inside a stat tile | accent |
| Uncertainty-window resolutions by policy | **Horizontal stacked bar** — three policies only | three categorical slots |
| Dead-letter failure reasons | **Table**, not a chart | — |

Applying the general rules to these specifically:

- **The zero is the hero figure, and there is exactly one hero figure per view.** Competing 48px numbers cancel each other out. On the chaos console, the zero wins; everything else is a stat tile.
- **Never a dual-axis chart.** Recovery latency and throughput are different scales and get separate charts. This is the most common charting mistake and the easiest to avoid by rule.
- **The throughput chart is the emphasis form on purpose.** One measured line against a dashed ideal-linear reference makes the divergence point self-evident, which is precisely the §14 conversation about the single Postgres writer being the ceiling. The chart asks the interview question for you.
- **Sequential ramps on dark must not go darker than the mid-dark step**, or the low bins recede into the surface and read as empty rather than as small.
- **Stacked segments get the same 2px surface gap** as timeline segments.
- **A legend is present for every chart with two or more series**, and single-series charts get none — the title already names what is plotted, and a one-swatch legend restates it.
- **Every chart has a table view**, reachable, with the same numbers. This is the accessibility floor and it is also genuinely useful.
- **Label selectively.** A number on every point is chaos and goes unread. Label the endpoint, the extreme, or the one series the story is about; the axis and the tooltip carry the rest.
- Gridlines are hairline, solid, one step off the surface, and recessive. Never dashed.

### 22.6 Motion

Section 13.4 stands: functional only. What that means concretely, given that the persuasion layer is permitted more than the instrument layer:

| Motion | Permitted where | Duration |
|---|---|---|
| New event sliding into the timeline | Everywhere | 150–200ms |
| Executing-segment pulse | Everywhere | ~2s loop, low amplitude |
| Orphaned-gap pulse + lease countdown | Everywhere — **never suppressed** | 1s loop |
| Invariant counter tick | Only on an actual change | 300ms |
| Worker handoff — new owner's first segment | Everywhere | 250ms, the one place a slightly emphatic ease is earned |
| Mechanism explainer loop | Landing band 2 only | ~6s loop, pausing on the handoff |
| Anything on scroll | **Nowhere** | — |
| Anything on page load for effect | **Nowhere** | — |

**`prefers-reduced-motion` must be honored throughout**, and honoring it must not remove information: the explainer falls back to a static third-beat frame with the transition labelled, the pulse becomes a static state color, and the orphaned gap keeps its countdown as plain changing text. A reviewer with reduced motion enabled must still be able to reach conclusion 2 of §21.1.

### 22.7 Before calling the interface done

- Every status is icon + label + color. **No bare colored dots anywhere.** This is the red/green measurement of §22.3 and it is the one that breaks silently.
- The palette was re-validated against the surfaces actually shipped, not the ones specified here, if they differ.
- Replayed and executed segments are distinguishable **with the display in grayscale.** Check it.
- Every chart has a table view and — for two or more series — a legend.
- No chart has two y-axes.
- `prefers-reduced-motion` loses no information.
- The landing page reaches conclusion 2 of §21.1 **with no scrolling on a laptop viewport** and with prose unread.
- The guided demo of §21.4 works on a first visit in a private window, with three workers freshly respawned.
- **Render it and look at it.** Validation covers color, not layout — open every view and check for label collisions, overflow, and a timeline that still reads at 40 steps.

---

## 23. What this addendum changes about the build order

Section 15 sequences the console at phase 7 and warns, correctly, against building it before phase 4. **That warning stands and this addendum does not relax it.** A landing page over an unproven runtime is worse than no landing page, because it invites scrutiny the system cannot yet survive.

The revision is only to what phase 7 contains, and to one small item that moves earlier:

| Phase | Addition |
|---|---|
| 5 | **The `demo_effects` table** and the demo agent of §21.5. It costs almost nothing and it is the ground truth the tool journal is tested against — useful during phase 5 development, not just in the UI. |
| 7 | The design tokens of §22 first, then the instrument layer of §13.3 — runs list, timeline, fleet, dead letter. The timeline's replayed-step encoding (§22.4) is the priority within phase 7. |
| 8 | The chaos console, and **only then** the landing surface of §21 — because bands 1 and 4 quote live metrics and harness output that do not exist until phase 8. |

Building the landing page last is not a deprioritization. It is a dependency: **the landing page's entire job is to present numbers the chaos harness produces**, and it cannot be honestly built before those numbers exist. A landing page written first would necessarily contain placeholder figures, and placeholder figures have a way of shipping.

**One addition to §16, definition of done:** a reviewer who has never heard of this project reaches the deployed URL, and within sixty seconds — without reading the README, without an account, and without navigating away from the landing page — has watched a worker die mid-run and another resume it, and has seen the evidence that nothing ran twice.

Item six of §16 remains the real bar. This is the bar for whether anyone gets far enough to ask you about it.

---
---

# Addendum B — The run-detail component

**Addendum version:** 1.2
**Status:** Additive. Specifies a required component. **Contains two deliberate departures from §22, both flagged in §24.7 with the measurements behind them, plus one open question in §24.8 that must be answered before phase 7 begins.**
**Scope note:** This is the primary screen for a single run. It supersedes the §13.2 description of the run-detail page — not by contradicting it, but by specifying it concretely. Every §13.2 requirement (worker id on every segment, fencing markers on the track, replayed steps rendered distinctly) must still be satisfied by what is built here.

---

## 24. `RunDetail` and `RunThread`

### 24.0 Design intent

Anchor runs agent tasks as a sequence of steps executed by worker processes. When a worker dies mid-run, another resumes from where it stopped without re-executing completed steps. **This component exists to make that handoff visually obvious and provable**, because it is the core value proposition of the product.

**Build what is described here.** Do not substitute a generic timeline library, a Gantt chart, or a kanban-style layout. The specific form is the point — a generic timeline component renders this data as a project schedule, which communicates nothing about ownership handoff.

### 24.1 Data shape

Delivered by a WebSocket subscription keyed on run id. **The component accepts this as props** — it does not open the connection itself (§24.6).

```
Run
  id                      string
  agent_type              string
  status                  "pending" | "running" | "completed"
                          | "failed" | "needs_review"
  started_at              timestamp
  step_count              int

  segments[]              one per worker that has touched this run,
                          in chronological order
    worker_id             string
    started_at            timestamp
    ended_at              timestamp | null      ← null ⇒ current owner
    steps[]
      name                string
      status              "done" | "active" | "pending"
      started_at          timestamp
      completed_at        timestamp | null
    log[]                 the monospace lines rendered under this
                          worker's bar
      timestamp           string
      text                string
      level               "info" | "success" | "warning"

  summary
    duplicate_side_effects  int      ← renders 0; the headline number
    handoff_count           int
    recovery_seconds        float    ← meaningful only when
                                       handoff_count > 0
```

`ended_at === null` identifies the current owner. That single field drives the kill button's target, the active-step styling, and which strand segment is still growing — so it must be trusted rather than re-derived.

### 24.2 The primary view — stacked worker bars

One horizontal progress bar per worker segment, stacked vertically in chronological order.

```
┌───────────────────────────────────────────────────────────────────────┐
│  run_47 · refund-agent                                    ┌─────────┐ │
│  started 41s ago · 5 steps                                │ running │ │
│                                                           └─────────┘ │
│                                                                        │
│  worker-a  ████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│            read ticket    check order    decide                        │
│            14:02:11  run_claimed worker-a epoch=5                      │
│            14:02:13  tool_intent fetch_order key=r47:s2:c1e            │
│            14:02:14  tool_result fetch_order ok                        │
│                                                                        │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤ worker-a lease expired ├─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│                                                                        │
│  worker-c  ██████████████████████████████████████████░░░░░░░░░░░░░░░  │
│            issue refund…    notify customer                            │
│            14:02:17  run_claimed worker-c epoch=6 reclaimed            │
│            14:02:17  replayed 3 steps from log                        │
│            14:02:18  tool_intent send_refund key=r47:s4:9a1           │
│                                                                        │
│  ─────────────────────────────────────────────────────────────────────│
│  0 duplicate side effects · 1 handoff · 3.1s recovery   ┌────────────┐│
│                                                         │ kill       ││
│                                                         │ worker-c   ││
│                                                         └────────────┘│
└───────────────────────────────────────────────────────────────────────┘
```

**Card header.** Run id and agent type as the title. `"started {n}s ago · {step_count} steps"` as the subtitle beneath it. A status pill on the right: `running` in warning colors, `completed` in success colors, `needs_review` and `failed` in danger colors.

**Worker id column.** Fixed width, to the left of each bar, monospace, bold, small, **in that worker's §22.3 identity hue**. Fixed width so the bars align to a common left edge — bars that start at different x positions cannot be compared by eye.

**The bar.** A rounded horizontal track. The filled portion represents completed plus active progress for that worker's portion of the run; the unfilled portion is a neutral surface color. **The fill is that worker's §22.3 identity hue** — blue, orange, then aqua in claim order — not a single accent shared across segments. Two stacked bars in different hues is the fastest possible read of "this run changed hands."

**Step labels.** Below each bar, the segment's step names as a row of labels, spaced to align with roughly where each step falls along the bar. The active step's label is **bold in primary ink** with a trailing ellipsis — `issue refund…`.

*(The original brief colored the active label amber. Per §22.2 text never wears a data color — a mid-lightness hue is unreliable as small text on either surface. Bold plus the ellipsis carries "active" unambiguously, and the colored bar directly above supplies the identity.)*

**The log.** Below the step labels, the segment's raw log lines in monospace, 11px, reading exactly as a terminal log would: muted ink for `info`, success color for `success`, warning color for `warning`. This is the §13.2 requirement that the raw event log sit beneath the timeline, satisfied per segment rather than as one block — which is better, because it attributes every line to the worker that wrote it.

**The handoff divider.** Between two worker segments: a horizontal dashed divider with a centered pill reading `{worker_id} lease expired` in danger colors — dark red background, red text. **This is the money moment of §13.4 rendered as a component.** It must never be collapsed, hidden behind a toggle, or animated away.

**The footer.** A thin divider, then a status line on the left in muted small text — `"{duplicate_side_effects} duplicate side effects · {handoff_count} handoff(s) · {recovery_seconds}s recovery"` — and a `kill {current_worker_id}` button on the right in danger styling: dark red background, red text, no border, small padding.

Three constraints on the footer that come from elsewhere in this document:

- **The duplicate count leads the line** because it is the product's guarantee (§10.2, invariant 1). It reads `0`, and a reader who understands the system knows that is the whole claim.
- **`recovery_seconds` is suppressed entirely when `handoff_count === 0`**, rather than shown as `0.0s`. A zero recovery time on a run that never lost a worker is not a measurement, and printing it invites the reader to distrust the numbers that are real.
- **The kill button targets the current owner** — the segment with `ended_at === null` — and is disabled with a reason when the run is in a terminal state. Per §8 it is a first-class product feature and should be styled as a deliberate action, not hidden in a menu.

### 24.3 The thread view — `RunThread`

Below the bars, inside the same card, separated by a thin divider and a small muted label reading `thread view`.

**This is a thin animated strand, not the bars again.** If it reads as a second progress bar it has failed; the bars answer *how far*, the strand answers *what happened, in what order, and where ownership changed*.

**Geometry.** Inline SVG, viewBox approximately `0 0 620 70`. One continuous wavy path drawn left to right using smooth bezier curves — never straight line segments. Stroke width 2–2.5px, noticeably thinner than the bars above.

**Color — one gold, not a shade per worker.** The strand is a **single gold** along its whole length (§24.7). Segment boundaries are marked by the enlarged `handoff` marker and its label, **not** by a change of shade.

This is a correction to the original brief, and §24.7 gives the measurement that forces it. The short version: worker identity is already carried by the bars in §22.3's hues, and a second gold shade collides with worker-2's orange badly enough to be indistinguishable. **The two views therefore answer different questions** — the bars answer *who owned what*, the strand answers *what happened, in what order*. Encoding identity twice, in two color languages, one of which is weaker, would make the card harder to read rather than richer.

**Event markers.** A small filled circle on the strand at each key event:

| Event | Color role | Shape | Why the shape matters |
|---|---|---|---|
| ordinary step completion | muted neutral | circle | the background case; must not compete |
| **a real side effect executed** | rust / critical | **square** | the event the product is about |
| reconciled safely / confirmed no duplicate | green / good | **ring (hollow)** | the proof, and it must not depend on hue |

**Shape is not decoration here — it is required, and §24.7 gives the measurement that forces it.**

At the handoff point specifically, the marker is slightly larger and carries a small text label above it reading `handoff`.

**Marker labels.** Small text, 11–12px, muted, near each circle, briefly identifying the event — `read`, `check`, `sent once`, `done`. Positioned above or below the strand in clear space, **never overlapping the strand**. A label that will not fit is dropped rather than clipped or overlapped; the tooltip and the log lines above carry it.

`sent once` is worth calling out as the single best two words in the interface. It states the guarantee in the reader's own language, right next to the marker proving it.

**The flow animation.** An SVG `stroke-dasharray` / `stroke-dashoffset` technique so the strand appears to gently and continuously flow along its own path, like a subtle current moving through it. A CSS `@keyframes` animation on `stroke-dashoffset`, looping smoothly, 2.5–3.5s per cycle, eased linearly so it reads as continuous flow rather than a pulse. **Keep it subtle** — visible on close inspection, not distracting at a glance.

This is the one exception to §22.6's ban on ambient motion, and it earns the exception on a specific ground: the strand represents *execution in progress*, so continuous motion on an in-progress run is stating a fact. **The flow must therefore stop when the run reaches a terminal state.** A completed run's strand is static. A strand that keeps flowing after the run finished is decoration, and it also lies.

**Reduced motion.** With `prefers-reduced-motion` set, freeze the dashoffset. The static strand keeps its colors, its markers, and its labels — no information is lost, per §22.6.

**Live extension.** When a new step event arrives over the WebSocket on an in-progress run, the strand's path **extends in real time** — grow the path length, reveal more of it — rather than snapping to the new state. This is the §22.6 "new event sliding in" rule applied to a path instead of a rectangle.

**Reusability.** `RunThread` is an independently reusable sub-component:

```
<RunThread segments={...} compact={boolean} />
```

`compact` renders the strand alone — no bars, no logs, no labels beyond the handoff marker — at a smaller scale, so it drops into a single row of the §13.3 runs list without duplicating logic. **Structure it this way from the start.** The runs list showing a strand per row means a reviewer sees at a glance which runs changed hands, which is a genuinely strong list view and costs nothing once the component is factored correctly.

### 24.4 Styling constraints

- **Dark, dense, monospace-leaning.** A developer and operator console. Reference tone: closer to a flight recorder or a terminal than a SaaS dashboard. This is §13.1, unchanged.
- **Tailwind utilities for layout.** The specific gold, red, and green values go in CSS custom properties or a small inline style block, so they render consistently regardless of theme.
- **Both light and dark mode**, with the strand and bar colors legible and distinguishable in each. Per §22.1 the light values are *selected and validated*, never an inversion — §24.7 gives them.
- **No decorative gradients, shadows, or glow effects anywhere**, with the single intentional exception of the strand's flow animation.
- **All text sentence case.** No title case. No exclamation marks. Applies to labels, pills, buttons, and log lines alike.
- **Monospace where alignment carries meaning** (§22.2): run ids, worker ids, epochs, keys, timestamps, and every log line. Not the prose subtitle, not the step labels.

### 24.5 Deliverable

- A single React and TypeScript component, or a small set — `RunDetail` plus `RunThread` — built against the §24.1 data shape.
- **Mock data matching the refund-agent example**: 5 steps, 2 workers, 1 handoff, 0 duplicate side effects, 3.1s recovery. It must render meaningfully with no live backend.
- **Live updates arrive as props**, via a passed-in hook or callback. Connection logic is not hardcoded inside the component, so it is testable in isolation.
- A preview: Storybook-style if the project has a preview setup, otherwise a simple page route rendering it with the mock data.

**Mock states worth building beyond the happy path**, because they are where the component will actually break: a run with zero handoffs (the footer suppression of §24.2), a run with three or more handoffs (the color rule of §24.7), a `needs_review` run (§21.5's third preset), a run with 40 steps (label collision), and a currently-orphaned run — no segment has `ended_at === null` yet — which is the state the component will be in during the most important two seconds of the demo. **That last one is easy to forget and it is the one a reviewer will see.**

### 24.6 Interface contract

```
RunDetail
  run          Run                       ← §24.1, fully controlled
  onKill       (workerId) => void        ← parent calls the API
  now?         timestamp                 ← injectable, for stable
                                           snapshots of "41s ago"

RunThread
  segments     Segment[]
  compact?     boolean = false
  animate?     boolean = true            ← parent may force-freeze
```

**No data fetching, no WebSocket, no API calls inside either component.** Kill is raised to the parent as a callback; the parent owns the `POST /api/workers/{id}/kill` call and its error handling. Injecting `now` matters more than it looks — relative timestamps make snapshot tests flap, and this component will be snapshot-tested.

### 24.7 Measured palette corrections

**The colors in the original brief were validated against the §22.1 surfaces before being written here. Three failed, and the failures are not cosmetic — each one degrades the specific thing the component exists to prove.** Corrected values below; use these.

**1. A gold shade per worker does not survive contact with the bar hues.** The brief's two golds were too close to each other to begin with — `#F6C453` against `#D68F1F` measures **normal-vision ΔE 14.3, below the 15 floor.** Widening the pair to `#F6C453` / `#B87309` fixes that in isolation (ΔE 23.2). But under the §24.8 decision the bars carry §22.3's hues, so all five colors appear in one card, and measured as a set:

| Pair | Measured | Verdict |
|---|---|---|
| strand gold 2 `#B87309` ↔ worker-2 orange `#d95926` | **CVD ΔE 1.2 (deutan), normal-vision ΔE 8.4** | the same color |

A reader could not tell whether a gold path segment meant "worker 2" or "strand segment 2" — the two channels would actively lie about each other. **The fix is one gold, with segment boundaries marked structurally rather than by hue:**

| Mode | Strand gold | Measured against the three bar hues, all-pairs |
|---|---|---|
| dark | `#F6C453` | worst CVD ΔE 9.4, worst normal-vision ΔE 20.9, all ≥ 3:1 — **passes** |
| light | `#7A6300` | worst CVD ΔE 9.2, worst normal-vision ΔE 21.4 — **passes** |

Selected per mode, not inverted: a gold light enough to read on `#1a1a19` is far too light for `#fcfcfb`, and a gold dark enough for the light surface collides with light-mode orange `#eb6834` unless it is pushed toward olive. `#7A6300` is that push.

`#F6C453` sits above the categorical lightness band (L 0.844). That is a **documented exception of the same class as status-yellow in §22.3**: it is a single signature accent rather than a member of a categorical set, it clears contrast on its surface, and nothing else on screen competes with it for the same meaning. Do not add a second gold to "balance" it.

**2. Two of the three event-marker colors were nearly identical.** The brief's amber-brown `#8A5A12` against rust `#B5471F` measures **CVD ΔE 1.7 (protanopia) and normal-vision ΔE 9.1** — effectively the same color. These encode "an ordinary step finished" versus "a real side effect executed," which are the two most consequential marker types in the product. Additionally `#3C6B4A` reads as gray (chroma 0.074) and both it and `#8A5A12` sat below 3:1 against the dark surface.

| Marker | Corrected | Shape |
|---|---|---|
| ordinary step | **muted `#898781`** (was `#8A5A12`) | circle |
| side effect executed | **`#d03b3b`** (was `#B5471F`) | square |
| reconciled safely | **`#0ca30c`** (was `#3C6B4A`) | ring |

Measured as a set on dark, all-pairs: normal-vision ΔE 18.9 worst pair, **all three now ≥ 3:1 contrast.** Demoting the ordinary-step marker to a neutral is also the semantically correct move — ordinary steps are the background case and should recede so the rust squares and green rings stand out.

**The red-versus-green pair remains at CVD ΔE 4.1 and cannot be fixed with color.** This is the same measurement recorded in §22.3, and it is why **shape coding is mandatory, not optional**: circle, square, and ring are distinguishable under every form of color blindness, in grayscale, and in a compressed screen recording. Combined with the brief's own text labels, the encoding is then carried by three independent channels. Do not ship the markers as three colored circles.

**3. The gold bar fill was illegible on a light surface, and is now moot.** `#EF9F27` measures **2.12:1 against `#fcfcfb`** — below 3:1, so it was never viable in light mode. Under §24.8 the bars no longer use gold at all; each takes its worker's §22.3 identity hue, which is already validated in both modes:

| Worker slot | Dark | Light |
|---|---|---|
| 1 | `#3987e5` | `#2a78d6` |
| 2 | `#d95926` | `#eb6834` |
| 3 | `#199e70` | `#1baf7a` |

The unfilled portion of the track is a neutral surface step in both modes — never a lighter tint of the worker's hue, which would read as a magnitude ramp and imply the empty portion carried a value.

**One inherited caveat:** light-mode aqua `#1baf7a` measures 2.74:1, just under 3:1. This is pre-existing in the §22.1 palette and carries the documented relief rule — the worker id label beside the bar and the step labels beneath it are the required visible text, and both are already specified in §24.2. No change needed, but do not remove those labels believing them decorative.

**Also carried over from §22.7, and easy to lose in this component specifically:** the status pill is not a bare colored pill. It carries its text label, and the `needs_review` and `failed` states carry an icon, because `completed`-green and `failed`-red are the ΔE 4.1 pair.

### 24.8 Resolved — gold is scoped to the strand

**Decision: gold belongs to `RunThread` alone. Section 22.3 stands unchanged** — blue, orange, and aqua carry worker identity in the bars, the fleet view, the runs list, and the charts. Gold is the strand's signature and appears nowhere else in the product.

The decision is settled; the rest of this section records what it implies, because two of the implications are not obvious and one of them corrects the original brief.

**The two views are assigned different questions, and neither answers the other's.**

```
   THE BARS          →   WHO owned WHAT
                         §22.3 identity hues, one per worker
                         read vertically: two hues stacked = a handoff

   THE STRAND        →   WHAT happened, in WHAT ORDER
                         one gold, always
                         read horizontally: markers = events,
                         enlarged marker = the handoff point
```

This separation is what makes two color languages in one card legible rather than inconsistent. **The failure mode to avoid is the strand also encoding identity** — that is what the original brief specified with a shade per worker, and §24.7 records the measurement that kills it: strand-gold-2 and worker-2 orange are the same color to a colorblind reader (CVD ΔE 1.2) and near-identical to everyone else (ΔE 8.4). Two channels asserting the same fact in different languages, one of them unreliable, is worse than one channel asserting it well.

**What changed in this document as a result:**

| Section | Change |
|---|---|
| §24.2 | Bar fill and worker id label take the worker's §22.3 hue, not amber. Active step label is bold primary ink, not amber (§22.2: text never wears a data color). |
| §24.3 | One gold for the whole strand; segment boundaries marked by the enlarged `handoff` marker, not a shade change. |
| §24.7 | Correction 1 rewritten around the strand-versus-bar collision. Correction 3 moot — bars no longer use gold. |
| §22 | **Unchanged.** No token rework required. |

**What this costs, stated plainly:** the strand no longer shows ownership on its own, so the `compact` variant in a runs list row (§24.3) cannot communicate *which* workers touched a run — only that a handoff occurred, via the enlarged marker. That is the right trade for a list row, where "did this run change hands?" is the question a reader actually has and the worker ids are one click away. But it means **the compact strand is not a substitute for the runs-list owning-worker column of §13.3.** Keep that column.

**What this buys:** §22 needs no rework, the stronger identity channel stays where identity is read most often, and gold remains distinctive precisely because it is used for exactly one thing. A single mark used once is what a reviewer remembers; an accent applied everywhere is wallpaper.

### 24.9 Build constraint

**Ask before making structural changes to the file layout beyond adding this component and its preview page.** New top-level directories, changes to the §5.1 repository structure, routing reorganizations, and added dependencies are all discussed first. Adding the component, its sub-component, its mock data, and one preview route needs no further approval.

---
---

# Addendum C — Protocol decisions

**Addendum version:** 1.3
**Status:** Resolves all four decisions left open before phase 1. **§25.5 supersedes the first subtlety in §6.1 and replaces the recovery figure in §10.3** — both changes are recorded there explicitly, with the arithmetic that forced them.
**Basis:** Decided against the engineering standard (`CLAUDE.md`), not by preference. Each decision below names the rule that determines it. Where the standard does not determine the answer, that is stated rather than papered over.

---

## 25. Resolved protocol decisions

### 25.0 How these were decided

Three of the four open decisions turned out not to be judgment calls at all — the engineering standard's invariants and architecture rules determine them, and the work was tracing the implication rather than choosing. That is worth recording, because a decision derived from a stated rule is defensible under questioning in a way that a preference is not.

| Decision | Determined by | Status |
|---|---|---|
| Sequence allocation | I2, I3, and "failing loudly beats failing silently" | Resolved, §25.1 |
| Epoch write-gate | I3, §4.2 "constraints over conventions", §5.4 anti-pattern 1 | Resolved, §25.2 |
| Determinism API | I6, §4.1 module boundary | Resolved, §25.3 |
| Configuration values | **Not determined by the standard.** Confirmed per §3.2, then derived from §4.4's assertion | Resolved, §25.5 |

### 25.1 Sequence number allocation

**Decision: a `last_seq` counter column on `runs`, incremented in the same transaction as the append. `UNIQUE (run_id, seq)` is retained as the backstop, not the allocator.**

The reasoning turns on a consequence of I3 that is easy to miss. **I3 guarantees exactly one worker may write to a run at a time.** Therefore, under correct operation, there is never contention for a sequence number within a run. Contention is not a normal condition to be handled — it is evidence that fencing has failed.

That reframes the choice. The allocator's job is to make collision *impossible* when the system is behaving, and the constraint's job is to make collision *loud* when it is not.

| Candidate | Verdict |
|---|---|
| `SELECT MAX(seq)+1`, insert, catch the unique violation, retry | **Rejected.** It makes collision a routine, silently-retried condition — which converts a fencing bug into invisible retry noise. That inverts "failing loudly beats failing silently" and would mask a violation of the system's most important invariant. |
| A Postgres `SEQUENCE` per run | **Rejected.** Sequences are non-transactional: a rolled-back append consumes a number and leaves a gap. Invariant 2 of §10.2 asserts no gaps, so this breaks a published guarantee. |
| **`runs.last_seq`, incremented in the append transaction** | **Adopted.** The append transaction already holds the `runs` row (§25.4), so the counter costs no additional lock. A rollback un-increments it, so there are no gaps. Collision becomes structurally impossible rather than caught-and-retried. |

**Crash behaviour.** The counter increment, the epoch check, and the event insert are one transaction. If the process vanishes at any point, all three roll back together: the counter is not advanced, no event is written, no gap is created. There is no interleaving that produces a partially-applied append.

**Schema note:** this adds one column to `runs` in §7. Per §3.2 of the standard, schema changes are normally raised before being made — it is recorded here as part of a spec revision rather than applied to a live database, but flag it if you would rather `last_seq` live elsewhere.

**Required test** (§5.3, concurrency): append under N concurrent workers against one run with only one legitimate epoch holder, then assert the sequence is contiguous from 1 with no duplicates and no gaps.

### 25.2 Epoch write-gate enforcement

**Decision: a `BEFORE INSERT` trigger on `run_events` that compares `NEW.epoch` to the run's current epoch and raises. Not a conditional `UPDATE … WHERE epoch = $1` with a rowcount check in the worker.**

Three rules in the standard converge on this and none of them permit the alternative:

- **I3** states that *the database* rejects any write whose epoch is below the run's current epoch.
- **§4.2** — "constraints over conventions. If a property must hold, express it as a database constraint. Application-level checks do not survive concurrency."
- **§5.4**, first listed anti-pattern — "application-level enforcement of a property a constraint could enforce."

A conditional `UPDATE` with a rowcount check is application-level enforcement. It is correct only for as long as every write path remembers to perform it, and §4.1 is explicit about where that ends: a safety property enforced outside `core/` "will eventually be bypassed by a code path that doesn't go through it." A trigger holds for every writer without exception — including a future code path, a migration script, and a `psql` session at three in the morning.

**Why not a `CHECK` constraint:** a `CHECK` cannot reference another table's row, and the current epoch lives on `runs`. The trigger is the least-powerful mechanism that can actually express the property.

**Error surface.** The trigger raises a dedicated `SQLSTATE`, which `core/leases/` maps to a typed `LeaseFencedError` (§5.2). On catching it the worker discards all in-memory state, writes nothing further — including no error event through that run's log — and returns to the idle pool. **It does not retry**, per I3 and §5.4's "retrying a fenced write."

**Crash behaviour.** The check and the insert are the same statement, so there is no window between validation and write. If the process dies before commit, nothing is written and the run is reclaimed on lease expiry as normal.

**Required tests** (§5.3, failure injection): construct a zombie worker holding a stale epoch and assert its append is rejected by the database with the specific error, that no partial write landed, and that the worker performs no subsequent write. This is the §9 failure-matrix row for a stalled-but-alive worker.

### 25.3 The agent contract — the determinism API

**Decision: agent code receives a `StepContext` and may reach the outside world only through it.** I6 forbids agent code from calling the clock or a random source directly; this is the surface that replaces those calls.

| Call | Journaled as | On replay |
|---|---|---|
| `ctx.now()` | `NONDET_RECORDED` | returns the recorded timestamp |
| `ctx.random()` | `NONDET_RECORDED` | returns the recorded value |
| `ctx.new_id()` | `NONDET_RECORDED` | returns the recorded identifier |
| `ctx.call_model(...)` | `LLM_CALLED` | returns the recorded completion, no provider call |
| `ctx.call_tool(name, args)` | `TOOL_INTENT` → `TOOL_RESULT` | returns the recorded result, or applies the tool's uncertainty policy |

`ctx.new_id()` is named separately from `ctx.random()` deliberately, per §5.1's precision rule: §3.2 of the spec identifies a generated identifier differing across replay as the specific failure that defeats deduplication, so the call that produces one should be individually visible in the log and individually greppable in agent code.

**This is a contract, not a sandbox — and the standard's "explicit beats clever" says to leave it that way.** Sandboxing Python's `datetime` and `random` from agent code would be substantial machinery guarding against a mistake that a much cheaper mechanism catches:

**Required test** (§5.3): a test that imports every module under `runtime/agents/` and fails if any of them references `datetime`, `time`, `random`, or `uuid` directly. It is three lines, it runs in milliseconds, and it catches the I6 violation at commit time instead of as a replay divergence that the chaos harness reports days later as an unrelated-looking invariant failure.

**Crash behaviour.** Each `ctx` call is journaled before its value is returned to agent code, so a crash between the external call and the journal write lands in the uncertainty window and is resolved by I8's declared policy — identically to any other side effect. **`ctx.now()` and `ctx.random()` are the exception worth naming:** they have no external effect, so a crash before journaling is safely re-derivable on the next attempt, because nothing in the world observed the discarded value.

### 25.4 Why §25.1 and §25.2 compose — the `runs` row is the serialization point

The two decisions above are independent in motivation and share one mechanism, which is worth stating explicitly because it is the load-bearing detail in both.

**Every append transaction takes the run's row in `runs` and holds it to commit.** That single lock does three jobs at once:

```
  BEGIN
    lock the runs row                     ← the serialization point
      · read current epoch                → §25.2's check reads a stable value,
                                            not one a concurrent claim can move
      · increment last_seq                → §25.1's allocation is uncontended
      · renew lease if due                → I5, evaluated on the database clock
    insert into run_events                → trigger validates against the
                                            epoch just read under the lock
  COMMIT
```

Because a claim (I4) also locks that same row to increment the epoch, a claim and an append can never interleave. The epoch the trigger validates against cannot change between being read and being enforced. **One lock, and I2, I3, I4, and I5 all hold across it** — which is the §4.2 instinct of putting the atomic unit in one transaction, applied to the append path rather than only the claim path.

This is also the answer to "what serializes the log?" in an interview, and it is a better answer than naming the unique constraint, because the constraint detects a problem the lock prevents.

### 25.5 Configuration — background renewal, two profiles

**This is the one decision the standard does not determine, and §3.2 explicitly requires it be confirmed rather than assumed.** Deriving the values surfaced a conflict inside the existing spec, recorded below because the resolution only makes sense against it.

**The constraint, from §4.4 of the standard:**

```
lease_duration > max_step_timeout + renewal_interval + margin
```

with the worker refusing to start and naming the violated relationship if configuration breaks it.

**The contradiction.** That constraint exists because §6 renews the lease *between* steps — the worker loop checks "if the renewal interval has elapsed, renew" inside the step loop, so no renewal happens during a long step. The consequence is unavoidable arithmetic:

```
  recovery time from a hard kill  ≈  lease_duration − (time since last renewal)
                                  ≈  lease_duration − renewal_interval/2

  and since   lease_duration > max_step_timeout + renewal_interval + margin

  therefore   recovery time  >  max_step_timeout
```

**Recovery can never be faster than the longest permitted step.** But §10.3 publishes "median recovery 1.8 seconds" as the headline number, and §21.4 promises the reviewer a roughly two-second stall. With a step timeout anywhere near a real model call — §1.1 shows a 22-second step — recovery is tens of seconds, not 1.8. **The headline number and the lease architecture as specified cannot both be true.**

This matters beyond the demo: §17.3 commits to preempting weaknesses rather than hiding them, and a reviewer who does this arithmetic while looking at the README will find it. Better to have decided it deliberately.

**Three ways out, with the honest cost of each:**

| Option | Mechanism | Cost |
|---|---|---|
| **A — Renew from a background task** | A concurrent renewer extends the lease on its own timer regardless of step progress. The constraint becomes `lease > renewal_interval + margin`, independent of step duration, so a short lease and long steps coexist. | Adds concurrency inside the worker. A hung step no longer expires its own lease, so `step_timeout` becomes the only thing bounding a stuck run — it must be enforced rigorously. Still does not reach 1.8s: that needs `lease ≈ 3s`, which risks spurious fencing on a 1s GC pause, the bug §6.1 warns is hardest to diagnose. |
| **B — Accept slower recovery and republish the number** | Keep renewal between steps. Set the lease honestly and report the recovery time it actually produces — single-digit to low tens of seconds. | The headline number gets less impressive. It also gets *true*, and a defensible 8s beats an indefensible 1.8s under questioning. |
| **C — Two profiles, reported separately** | A demo and chaos profile with short steps (§21.5 stubs model calls at 2–5s) and a correspondingly short lease; a production profile sized for real model calls. Publish recovery per profile and state the lease each was measured under. | Two configurations to keep honest. But it is the only option that gives a fast live demo *and* a configuration that could run a real agent — and stating "recovery is bounded by lease duration, here is the tradeoff, here are both points on it" is a stronger interview answer than either number alone. |

**Decision: C, with A as the mechanism underneath it.** A background renewer decouples the lease from step duration, which is what makes two sensible profiles possible at all; C is then the reporting discipline that keeps the published number honest.

#### The revised constraint

Renewal moves out of the step loop into a **concurrent task that extends the lease on its own timer**, regardless of step progress. The §4.4 relationship therefore loses its dependence on step duration:

```
  was:   lease_duration > max_step_timeout + renewal_interval + margin
  now:   lease_duration > renewal_interval + margin
```

**This supersedes the first of the four subtleties in §6.1**, which required lease duration to exceed maximum step duration plus renewal interval. That was correct for renewal-between-steps and is no longer the binding constraint. The warning attached to it stands and in fact sharpens: a lease too short relative to *renewal latency* still spuriously fences a healthy worker, and §12's fencing-rate metric is still the detector — read it as "too short relative to renewal latency" rather than to step duration.

**It does not introduce a second liveness signal.** Section 3.4 insists extension *is* the heartbeat and that there is deliberately no separate signal, because two signals can disagree. A background renewer is still lease extension; only its timer changed, not its meaning.

Concrete rule adopted: **`lease_duration = 4 × renewal_interval`**, tolerating three consecutively missed renewals before ownership is lost. One relationship, asserted at startup, holding identically in both profiles.

#### The two profiles

| Setting | Demo / chaos | Production | Constraint that produced it |
|---|---|---|---|
| `renewal_interval` | 1s | 5s | short enough that expiry is prompt after a kill |
| `lease_duration` | 4s | 20s | `= 4 × renewal_interval`; tolerates 3 missed renewals |
| `margin` | 3s | 15s | `= lease_duration − renewal_interval`; the assertion's slack |
| `step_timeout` | 10s | 60s | bounds a hung step only — **no longer tied to the lease** |
| `max_attempts_per_step` | 3 | 3 | §6 attempt cap before dead-lettering |
| `backoff_base` | 1s | 1s | |
| `backoff_factor` | 2 | 2 | |
| `backoff_jitter` | ±25% | ±25% | prevents retry convoys forming across workers |
| `backoff_cap` | 30s | 30s | |
| `per_worker_concurrency` | 10 | 10 | §6 admission control, per worker |
| `global_concurrency_cap` | 100 | 100 | §5 admission control, fleet-wide |
| `reclaim_poll_interval` | 0.5s + jitter | 2s + jitter | the tail on observed recovery |

**Derived recovery**, since this is the number that gets published:

```
  recovery ≈ lease_duration − renewal_interval/2 + reclaim_poll_interval/2

  demo:         4 − 0.5 + 0.25  ≈  3.75s
  production:  20 − 2.5 + 1.0   ≈  18.5s
```

**Section 10.3's "median recovery 1.8 seconds" is not achievable at any safe lease and is replaced.** The honest headline is the demo-profile figure with its lease stated — approximately 3.5 to 4 seconds at a 4-second lease. **Section 14 must report the profile alongside the number**, because a recovery time without the lease it was measured under is not a measurement. Reporting both profiles is the stronger move regardless: it shows recovery is a tuned tradeoff that was understood, rather than a number that happened.

Section 21.4's "roughly two-second stall" becomes roughly four. The lease countdown specified there consequently does more work than anticipated — four seconds of unexplained pause reads as a broken page, whereas four seconds of visible countdown reads as the mechanism working.

#### What the background renewer costs, and how each cost is contained

**`step_timeout` becomes the only bound on a hung step.** Previously a hung step eventually lost its own lease. Now the renewer keeps extending it, so the step timeout is no longer a convenience — it is the sole mechanism preventing a stuck run from being held indefinitely. Per §4.3 it must wrap every external call without exception. **When a step exceeds its timeout the renewer stops**, so that if the failure path itself cannot proceed, the lease lapses and the run is reclaimed rather than held by a worker that is no longer making progress.

**The renewer becomes the fencing detector**, which makes it the most safety-critical concurrency in the worker. When a renewal is rejected because the epoch advanced (§25.2), the renewer cancels the run's task, and that task must write nothing after cancellation. Per I3 the worker then discards state, writes nothing further, and returns to the idle pool. The material change is that discovery now happens on a *different task* than the one doing the work — so the cancellation path is real code with a real race, and it needs a test rather than an argument.

**A blocked event loop is still fenced correctly**, which is worth confirming rather than assuming. If the process stalls on a GC pause, a CPU-bound section, or a suspended VM, the renewer task cannot run either — so the lease expires and the run is reclaimed. **The zombie-worker path of §3.4 is preserved, not bypassed:** the renewer is incapable of signalling liveness that outlives a stalled process, which is precisely why it is safe to move renewal off the step loop.

**Accepted risk, stated plainly.** At a 1-second renewal and a 4-second lease, a three-second stall spuriously fences a healthy worker. That is a genuine exposure on the demo profile and it is the price being paid for a demonstrable recovery time. The production profile has the same proportional tolerance with far more absolute headroom. Watch §12's fencing rate; a rising rate on the demo profile means the lease is too tight for the environment, not that workers are unhealthy.

#### Startup assertion

Per §4.4, in one config module, checked before the worker accepts any work:

```
  assert lease_duration >= 4 × renewal_interval
  assert margin == lease_duration − renewal_interval
  assert step_timeout > 0
```

On violation the worker **refuses to start** and names the violated relationship together with the offending values.

**This interacts with §13.3's Environment page, which makes these editable live.** The assertion must therefore run on every applied change and **reject the change**, not the worker — a running fleet must not be configurable into a state where every worker spuriously fences itself. An operator who sets the lease equal to the renewal interval gets a rejected edit explaining the relationship, not an outage.

**Required tests** (§5.3, failure injection and concurrency):

- renewal continues across a step longer than the lease duration; the run is **not** fenced
- a step exceeding `step_timeout` fails, the renewer stops, and the lease lapses
- a renewal rejected on epoch advance cancels the run's task, and **no write follows the cancellation**
- a simulated blocked event loop results in lease expiry and reclaim, not in continued renewal
- the startup assertion rejects `lease_duration == renewal_interval`, both at boot and when applied through the Environment page

**One further note, independent of the choice above.** The kill endpoint of §8 is a *cooperative* shutdown, so it could release the lease explicitly on the way out and make reclaim near-instant — but that is not how a crash behaves, and presenting it as one would violate §6.1 of the standard, which forbids the interface from misrepresenting system state. If it is implemented, the demo should offer both paths and label them: a graceful kill that releases the lease, and a hard kill that waits for expiry. **Showing a reviewer both, and explaining why they differ, is worth more than hiding the slower one** — it demonstrates that the recovery path is understood rather than merely observed.

---
---

# Addendum D — Developer adoption, the authoring surface, and recorded cuts

**Addendum version:** 1.0
**Status:** Additive. Fills one real gap in the base document (§26), specifies one stretch subsystem (§27), and records four decisions so they are not relitigated (§28).
**Relationship to §21.7:** This addendum introduces no authentication, no accounts, and no per-user state. §21.7 stands unmodified. Where §27 needs to restrict a capability, it binds that capability to **deployment mode**, not to identity — see §27.3 for why that is the stronger choice and not merely the cheaper one.

---

## 26. The developer adoption path

### 26.1 The gap this section closes

Section 2.1 states that Anchor's user is a developer running agents. Sections 21.4 through 21.6 then specify, in detail, the experience of a **reviewer** who lands on the deployed instance and watches a demo. Section 13.3 specifies the experience of an **operator** watching runs execute.

Nothing in the base document specifies the experience of the person §2.1 names: **a developer who wants to run their own agent on Anchor.** That path exists — the agent contract of §25.3 and the tool registry of §7 are exactly the surfaces it uses — but it has never been written down as a path, which means it has never been designed as one.

This matters for two reasons. It is the difference between a project that demonstrates a capability and a tool that has one. And it is the section a technical reviewer reads to answer the question *"could I actually use this?"* — a question the guided demo of §21.4 deliberately does not answer, because the demo is about the guarantee, not the interface to it.

### 26.2 The distribution model, stated plainly

**Anchor is self-hosted. It is not a service.** A developer runs their own instance; there is no multi-tenant hosted offering, no signup, and no API key issued by anyone.

State this in the README's first paragraph. It is the same model as most open infrastructure, it is the correct scope for this project, and being explicit about it prevents the reasonable-but-wrong assumption that the deployed demo instance is something a developer would point production traffic at.

The deployed instance at the public URL is a **demonstration instance** (§21.6). It exists to be watched. It is not the product's distribution channel; the repository is.

### 26.3 The quickstart — eight steps, and the README leads with it

The README's structure per §16 is: screen recording, chaos numbers, architecture. **This quickstart goes immediately after the architecture diagram**, because a reviewer who is convinced by the numbers will next want to know what using it costs them.

```
1  clone and start
       git clone <repo> && cd anchor && docker compose up
   Brings up Postgres, Redis, the API, and three workers.
   Console at localhost:3000. No configuration required.

2  write the agent
       runtime/agents/my_agent.py
   One function, the §25.3 contract:
       decide_next_step(ctx) -> ToolCall | ModelCall | Done
   It receives the reconstructed run state and returns ONE action.

3  write any tools it needs
       runtime/tools/my_tool.py
   A plain function. Anchor does not care what is inside it.

4  declare each tool's safety category
       register_tool(name=..., fn=..., safety=...)
   retry_safe | reconcilable | unsafe  (§3.3)
   For reconcilable tools, also supply reconcile_fn.
   THIS IS THE ONLY ANCHOR-SPECIFIC CONCEPT TO LEARN.

5  register the agent
       agent_registry.register("my_agent", my_agent.decide_next_step)

6  rebuild
       docker compose up --build
   Agent and tools now live inside every worker.

7  submit a run
       POST /api/runs  { "agent_type": "my_agent", "input": {...} }
   Or use the Test run form in the console.

8  watch it, then break it
       Open the run. Kill a worker from the fleet page.
       Watch it resume. Check that the tool ran once.
```

**Steps 2 through 5 are the entire integration surface.** Everything else is `docker compose`. A developer who follows this path writes zero durability code and receives crash-resilience, resumability, a complete audit trail, and effectively-once side effects.

### 26.4 The one constraint that must be taught, not discovered

Every other part of the contract is mechanical. This one is conceptual, and if it is not stated in the first paragraph of the authoring documentation, developers will get it wrong and their agents will replay incorrectly.

> **The agent function returns one action and then returns control. It does not loop, and it does not hold state in variables across steps.** All state is read from `ctx`, which the runtime reconstructs from the log on every attempt.

The reason, stated for the developer rather than for the runtime author: an agent that loops internally is opaque to the runtime, and a crash inside that loop has nothing to resume from. Yielding control at each step is what converts a fragile in-memory process into a resumable one.

**Concretely, in the professor-outreach shape** — the loop is expressed as a function of journaled history, not as a `for` statement:

```
def decide_next_step(ctx):
    if not ctx.has_result("search_professors"):
        return ToolCall("search_professors", {...})

    professors = ctx.result_of("search_professors")
    done = ctx.completed_tool_args("send_email")     # from the log
    remaining = [p for p in professors if p.email not in done]

    if not remaining:
        return Done({"contacted": len(done)})

    p = remaining[0]
    if not ctx.has_result("fetch_page", {"url": p.url}):
        return ToolCall("fetch_page", {"url": p.url})
    ...
```

The loop's progress lives in the journal, so "which professors have already been emailed" survives any number of crashes, on any worker, without the agent tracking it. **This example belongs in the README verbatim** — it is the clearest possible demonstration that the constraint buys something rather than merely costing something.

### 26.5 Framework adapters

Section 18 cuts support for multiple agent frameworks, and that cut stands. But the contract's shape should make an adapter obviously possible, because a reviewer familiar with LangGraph will ask.

**The answer to have ready:** a graph-based framework is driven one node per `decide_next_step` invocation rather than by calling its own end-to-end execution method, with the framework's state object rehydrated from `ctx` on each call. That is an adapter of perhaps fifty lines, and it is not in scope to write. **Say the shape, do not build it.** Claiming framework-agnosticism and demonstrating it once is stronger than demonstrating it twice and having spent the time.

---

## 27. The authoring surface *(phase 9, stretch)*

### 27.1 What it is and what it is for

A page in the console — **Tools → Authoring** — containing a code editor preloaded with the agent contract, the three demo agents as worked examples, live validation against the contract, and an optional LLM-backed draft generator.

**Its purpose is pedagogical before it is functional.** A reviewer who has watched the guided demo and now wants to know what authoring costs can read the contract and see the validator reject a deliberately wrong draft, without cloning anything. For a developer running locally, it removes a context switch during the most annoying part of integration.

**It proves nothing the runtime does not already prove.** It is in phase 9 for that reason, and it must not be built before phase 8 is complete.

### 27.2 The validator is the interesting part, not the editor

An editor is a dependency someone else wrote. The validator is a small piece of original engineering that makes the contract enforceable rather than merely documented, and it reuses machinery the project already needs.

Static checks, run on every keystroke pause and on every submission:

| Check | Rejects | Why it matters |
|---|---|---|
| **Determinism imports** | Any reference to `datetime`, `time`, `random`, or `uuid` | This is I6. **It is the same check as the required test in §25.3** — the test that runs at commit time here runs interactively, against a draft, before the code has ever executed. |
| **Return shape** | Anything not a `ToolCall`, `ModelCall`, or `Done` | An agent that returns an unrecognised action stalls the worker loop |
| **Module-level mutable state** | Globals mutated across invocations | Violates §26.4. State held outside `ctx` does not survive a handoff and is the most likely authoring mistake. |
| **Unregistered tool names** | `ToolCall` naming a tool absent from the registry | Fails fast in the editor rather than at step 3 of a live run |
| **Missing safety declaration** | A registered tool with no declared category | Forces the §3.3 decision to be made deliberately |
| **Unbounded self-recursion** | A step that can only return itself | Catches the trivial infinite-run case; the attempt cap of §6 catches the rest |

**The validator's error messages are product surface, not developer output.** Per the standard, they state what is wrong and what to do: *"line 14 calls `datetime.now()`. Agent code must use `ctx.now()` so the value is journaled and replay returns the same timestamp — see the determinism boundary."* An error that teaches the invariant is worth more than the feature that produced it.

### 27.3 Execution is bound to deployment mode, not to identity

**The problem, stated without softening: accepting arbitrary Python from a public endpoint and executing it on the host is remote code execution.** Not a theoretical concern. The code that reads the process environment and exfiltrates the database URL is three lines, the endpoint would be found by automated scanning, and the host in question also runs the Postgres instance holding the chaos-harness history that §21.6 identifies as the project's published evidence.

**The rejected mitigation: sandboxing.** Doing this properly means a container-per-execution boundary, a microVM, or a WASM runtime, plus egress control and resource limits. That is a substantial subsystem, it is entirely orthogonal to durable execution, and building it would consume the hours §15 already warns phases 4 and 5 will overrun.

**The rejected mitigation: authentication.** Gating execution behind a login would work, and it is what most projects would do. It is rejected because §21.7 cuts accounts for good reasons that have not changed, and because introducing an auth system to guard one stretch feature inverts the cost-benefit completely.

**The decision: the capability is compiled out of the public deployment.**

| Deployment | `/authoring/validate` | `/authoring/generate` | `/authoring/register` |
|---|---|---|---|
| Local (`docker compose`) | enabled | enabled | **enabled** |
| Public demonstration instance | enabled | enabled | **not mounted** |

The register route is mounted only when `ANCHOR_AUTHORING_EXECUTE=true`, which is set exclusively in the local compose file. **Absent configuration, it is disabled** — fail-closed, consistent with I7, and the same posture the runtime takes toward the database.

Three properties make this stronger than an auth check rather than merely cheaper:

- **There is no code path to attack.** An unmounted route cannot be reached by a credential-stuffing attempt, a session bug, or a misconfigured middleware ordering. The public instance does not contain the capability.
- **It matches the actual trust boundary.** A developer running locally is executing their own code on their own machine — the normal case, requiring no permission from anyone. The restriction is not about *who* is asking; it is about *whose machine* is at risk. Binding it to identity would model the situation incorrectly.
- **It is one line to explain in an interview**, and the explanation demonstrates that the RCE was recognised rather than missed.

**The page states its mode in the header at all times.** On the public instance: *"Author-and-validate mode. This instance does not execute submitted code. Run locally to register and execute."* Silently disabling the button would read as a bug.

### 27.4 The draft generator, and why it does not violate the governing rule

The governing rule appears in §0 and throughout: **deterministic core, LLM explanation layer — the model never produces output the system presents as fact.**

A code generator appears to contradict it and does not. The rule governs **runtime**: a value the system computes, displays, and acts upon without a human in the loop. Generation here is **authoring-time**: it produces a draft that a human reads, edits, and explicitly registers before a single step of it ever executes. The distinction is the same one that makes an editor's code completion compatible with a codebase's invariants.

**State this distinction in the spec and in the README**, because a reviewer who has absorbed the governing rule will notice the generator and should find the reconciliation already written down rather than have to raise it.

Four requirements, all of which follow from the distinction rather than being bolted on:

**It is seeded with the contract.** The system prompt carries the §25.3 contract table, the §26.4 constraint, the registered tool list with safety categories, and the three demo agents as worked examples. An ungrounded generator emits plausible Python that does not fit the runtime, which is strictly worse than no generator — the developer now has to find the mismatch rather than write correct code from a template.

**Its output is always routed through the validator before display.** The draft arrives in the editor with validation already run and any violations already marked. The generator does not get to produce something the validator would reject and have that pass without comment.

**It never registers, and never executes.** Output lands in the editor. Registration is always a separate, explicit human action — and on the public instance, per §27.3, is not available at all.

**It degrades honestly.** No API key configured, or the provider is unreachable: the page works, the editor works, the validator works, and the generate control is disabled with a plain statement of why. The generator is a convenience on top of the authoring surface, never a dependency of it.

### 27.5 What this section deliberately does not become

**It is not a no-code builder.** There is no visual step composer, no dropdown-driven agent construction, and no attempt to make agent authoring accessible to non-programmers. §18 cuts that, §28.2 records why, and the editor is the boundary — it lowers the friction of writing the contract, it does not remove the requirement to write code.

**It is not a hosted authoring environment.** No saved drafts, no per-user workspaces, no draft persistence across sessions beyond the browser. §21.7 stands: no accounts, no server-side per-user state. A draft lives in the editor and in the developer's clipboard.

---

## 28. Recorded decisions — prior art and cuts

These four are written down so they are not reopened. Each was considered seriously, and each was cut for a stated reason.

### 28.1 Prior art, and the positioning that follows from it

Durable execution is a solved and actively contested category. Temporal is the mature reference implementation; Restate, Inngest, Trigger.dev, and DBOS occupy adjacent positions, several of them marketing specifically to agent workloads. Event sourcing, leases, fencing tokens, and idempotency keys are textbook distributed-systems patterns with decades of literature.

**Anchor is not novel, and the specification does not claim it is.** §17.3 already commits to naming Temporal and Restate unprompted; this section states the underlying position so that commitment has something to rest on.

> **Anchor is a durable execution engine in the Temporal lineage, specialized for agent workloads and built to be demonstrated rather than deployed at scale.**

Say that sentence first, in the README and in conversation. A reviewer who knows the field will think of Temporal within ten seconds regardless; getting there first converts a potential gap in your awareness into evidence of it. **The claim the project makes is measured correctness under adversarial failure, which is a claim about rigour and not about invention** — and that claim is unaffected by the category's maturity.

### 28.2 Cut: the consumer storefront and the no-code builder

Both were considered as ways to give Anchor a user-facing entry point comparable to a consumer product.

**The storefront** — a polished single-purpose page wrapping one flagship agent, hiding all runtime vocabulary — was cut because the guided demo of §21.4 already solves the underlying problem. A reviewer lands, clicks once, and watches a real run recover from a real kill, in sixty seconds, with no jargon required to understand what happened. A second consumer-framed surface would duplicate that work while softening the operator vocabulary that makes the runtime legible to the audience that matters.

**The no-code builder** — visual composition of agents from a tool palette — was cut on positioning grounds. It moves the project into competition with mature workflow-automation products on their strongest axis, integration breadth, while abandoning its own, which is correctness under failure. The authoring surface of §27 is the deliberate middle position: it lowers the cost of writing an agent without pretending the requirement to write one away.

### 28.3 Cut: branching and fork-from-checkpoint

Forking a run at step N, altering an input, and re-executing forward on the journaled prefix is a natural extension of an event-sourced runtime, and it would render beautifully in the thread visualization of §24.3.

**It is cut on prior-art grounds.** Checkpoint-based time travel with forking is a native, documented feature of at least one widely-used agent framework, and at least one commercial debugging product ships the cached-prefix version specifically. Implementing it buys no differentiation.

It also carries real cost that is easy to underestimate: a fork produces two run histories sharing a prefix, which complicates the §10.2 invariants — particularly log monotonicity and single-writer-per-epoch, both of which currently assume one linear history per run. **Adding branching means revisiting the invariants that constitute the project's proof.** That is the wrong trade for a feature whose value is exploratory rather than load-bearing.

### 28.4 Cut: the research-flavoured extensions

Four ideas were raised as potential sources of genuine novelty, evaluated, and cut:

| Idea | Why it is interesting | Why it is cut |
|---|---|---|
| **Divergence-aware replay** — deciding per step whether to replay a journaled decision or re-derive it when the world has moved on | The most genuinely open problem here. Literal replay of a stale search result, or of a decision made from a transient failure, is a real weakness of the current model. | No known-good answer. Getting it wrong produces a runtime whose replay semantics are unclear, which is worse than one whose semantics are simple and stated. |
| **Cost-aware recovery** — optimizing replay-versus-re-derive against token cost | Agent replay is not free the way deterministic workflow replay is; nobody models the economics. | Requires the divergence work above as a prerequisite. |
| **Generic reconciliation protocol** — a declarative way to express "check whether this effect landed" across arbitrary tools | Would generalize §3.3's per-tool policies into something reusable. Real and unsolved. | Genuinely interesting and genuinely out of scope. Worth a paragraph in the design document as future work. |
| **Semantic compensation** — generating compensating actions with a model when a run fails partway | Sagas require hand-written compensations; generating them is unexplored. | Directly contradicts the governing rule at runtime, unlike §27.4's authoring-time generation. Also alarming. |

**Recorded here rather than pursued.** Each is a legitimate paragraph in a "future work" section, and a reviewer who asks "what would you do next" gets a better answer for having thought about them than for having half-built one.

---

## 29. What this addendum changes about the build order and the definition of done

### 29.1 Build order

Section 15 gains phase 9 and nothing else. **Phases 1 through 8 are unchanged, and the §23 warning against building the console before phase 4 stands.**

| Phase | Change |
|---|---|
| 5 | No change, but note: the demo agents registered here are the same ones §27.4 uses as few-shot examples. Write them well enough to serve as documentation. |
| 8 | Unchanged. **The definition of the project is complete at the end of phase 8.** |
| 9 | *(stretch)* Authoring surface. Order within the phase: validator first, editor second, generator last. The validator is the part with engineering content; the editor is a dependency; the generator is a convenience. If phase 9 is only half-built, the half worth having is the validator. |

**Phase 9 is genuinely optional and should be treated as such.** If it is not built, nothing in §26 becomes untrue — the quickstart path works entirely from the command line, which is how developers integrate infrastructure anyway.

### 29.2 Definition of done

Section 16 gains one item, and §23 already added one. Both are about whether anyone gets far enough to evaluate the runtime.

**New item:** the README's quickstart (§26.3) has been followed end to end, from a clean clone on a machine that has never run the project, by someone who is not you. Every step works as written, or the step is corrected. A quickstart that has only ever been executed by its author is a quickstart that does not work.

This is cheap to satisfy and it is the single most common failure in developer-facing repositories.

### 29.3 What this addendum does not change

- **No authentication, no accounts, no per-user state.** §21.7 stands. §27.3 achieves its restriction through deployment mode specifically to avoid reopening this.
- **No change to the eight invariants**, the worker loop, the data model, or the chaos harness.
- **No change to the claim.** The project's headline remains the measured chaos-harness result. Everything in this addendum is about the surfaces around that claim, not the claim itself.

---
---

# Addendum E — Canonical page inventory, deployment-mode capabilities, and the outbound surface

**Addendum version:** 1.0
**Status:** Consolidating and additive. §30 restates the console's pages as one canonical table, superseding no prior text but replacing the need to reconstruct the list from §13.3, §21, and §27. §31 is new and normative: it is the single authoritative statement of what each deployment mode permits. §32 is new and specifies the page's outbound links.
**Why §31 exists as its own section.** The public/local capability split is currently derivable from §21.6, §21.7, and §27.3, but it is never stated in one place. A security boundary that must be reconstructed from three sections is a security boundary that will eventually be implemented wrong. **When any part of this document appears to conflict with §31, §31 governs.**

---

## 30. The canonical page inventory

Every page in the console, in sidebar order. This table is the build checklist for phase 7 and the completeness check for §16.

| Group | Page | Contents | Phase |
|---|---|---|---|
| **Overview** | Dashboard | Active runs, live worker count, steps/sec, duplicate-effect counter (reads zero), throughput sparkline | 7 |
| **Runs** | All runs | Every run, newest first; per-row `RunThread` in compact mode (§24.3); status, current step, owning worker; filterable; rows update in place over the WebSocket | 7 |
| | Run detail | The `RunDetail` component of Addendum B — stacked worker bars, per-segment logs, handoff dividers, thread view, replayed-step encoding (§22.4), raw event log, kill control, effect counters | 7 |
| | Needs review | Runs halted in the uncertainty window (§3.3). Each shows the specific ambiguous call, the tool's declared policy, and the resolution actions. **Its own page, not a filter** — per §13.3, failures must not be reachable only by narrowing a list. | 7 |
| | Scheduled | Recurring and delayed runs. **Only if the §18 add-if-early item is built.** Absent otherwise; do not ship an empty page. | — |
| **Workers** | Fleet | Card per worker: id, uptime, current run count, last heartbeat age, code version, kill control | 7 |
| | Deployments | Code version per worker, as a history. Populated from the `workers.version` column already in §7. Answers "which build is actually running." | 7 |
| **Chaos** | Console | Configure worker count, kill rate, latency injection, failure injection, duration. Launch. Live invariant panel: duplicate executions, stranded runs, recovery distribution, replay overhead. **Per §23, built at phase 8, before the landing surface.** | 8 |
| | History | Every past chaos run with its final invariant report, retained permanently. §21.6 forbids the reset affordance from touching this table. | 8 |
| **Tools** | Registry | Every row of `tool_registry` (§7): name, declared safety category, reconciliation function presence, last used | 7 |
| | Test run | Submit a one-off run through a form. **Pre-registered agents only in every deployment mode** — this page selects, it does not author. | 7 |
| | Authoring | The editor, validator, and draft generator of §27. Header states the deployment mode at all times. | 9 |
| **Observability** | Metrics | §12 metrics as charts over time: throughput, recovery latency, replay overhead, fencing rate. Chart rules per §22.5. | 7 |
| | Logs | Search across `run_events` for all runs. Distinct from the per-run log on the run-detail page. | 7 |
| **Settings** | Environment | Lease duration, renewal interval, step timeout, retry caps, concurrency caps. Live-editable, subject to the §25.5 startup assertion re-running on every applied change and rejecting the change rather than the fleet. | 7 |
| | API keys | Present only where programmatic submission is gated. **On the public demonstration instance there is no gate, therefore no keys, therefore no page.** See §31. | — |
| | Webhooks | Run-completion and failure notification targets. §18 add-if-early. | — |

**Three pages in this table are conditional and must not ship as empty shells:** Scheduled, API keys, and Webhooks. An empty settings page reads as an unfinished product; an absent one reads as a scoped one.

---

## 31. Deployment-mode capabilities — normative

Anchor runs in exactly two modes. Mode is determined at process start by configuration, never by a request, a session, or a user.

| Mode | How it is entered | Trust model |
|---|---|---|
| **Demonstration** | Default. `ANCHOR_AUTHORING_EXECUTE` unset or false. | Anonymous public visitors. The host is yours; the code is yours. |
| **Local** | `docker compose up` sets `ANCHOR_AUTHORING_EXECUTE=true`. | The operator is running their own code on their own machine. |

**Fail-closed, per I7:** absent configuration is demonstration mode. A deployment that fails to set anything is the safe one.

### 31.1 The capability matrix

| Capability | Demonstration (public) | Local | Rationale |
|---|---|---|---|
| Landing page and guided demo (§21.4) | Yes | Yes | The entire point of the public instance |
| Watch any run's timeline live | Yes | Yes | Read-only |
| Runs list, thread previews, run detail | Yes | Yes | Read-only |
| Raw event log, per run and global | Yes | Yes | Read-only. The log contains no secrets; demo tool args are synthetic. |
| Submit a **pre-registered** agent | Yes, IP rate-limited and hourly-capped (§21.6) | Yes, uncapped | Bounded compute, stubbed model calls, no financial exposure |
| Kill a worker | **Yes** | Yes | This is the product. Workers self-heal (§21.6); a visitor cannot permanently degrade the fleet. Rate-limited only so the fleet view stays readable. |
| Launch a chaos run | Yes, bounded duration and worker count | Yes, unbounded | Same reasoning as submission. Cap the parameters, not the capability. |
| View chaos history | Yes | Yes | This is the published evidence; it is meant to be read |
| Tool registry, metrics, logs | Yes | Yes | Read-only |
| Cancel a run | Yes, **scoped to demo runs** | Yes, all runs | §21.6 |
| Resolve a `needs_review` run | Yes, **scoped to demo runs** | Yes, all runs | The resolution UI is worth demonstrating; scoping prevents interference |
| Clear demo runs | Yes | Yes | Never touches chaos history (§21.6) |
| **Authoring: edit and validate** | **Yes** | Yes | Static analysis only. Nothing executes. This is what makes the contract legible to a reviewer without a clone. |
| **Authoring: generate a draft** | **Yes** | Yes | Returns text into the editor. Never registers, never runs (§27.4). |
| **Authoring: register an agent** | **No — route not mounted** | Yes | §27.3. This is the RCE boundary. |
| **Execute visitor-authored code** | **No — no code path exists** | Yes | §27.3 |
| Edit Environment settings | **No** | Yes | Lease misconfiguration can render the fleet non-functional (§25.5). Not a security boundary — an availability one. |
| Delete or alter chaos history | **No** | **No** | Immutable in both modes. It is evidence. |
| Mutate another visitor's run | **No** | n/a | No cross-run write paths exist at all |

### 31.2 The four properties this matrix must preserve

**Nothing in demonstration mode can execute code the visitor supplied.** Not sandboxed, not filtered, not permission-checked — the route is not mounted. An unmounted route survives a middleware ordering bug, a session-handling error, and a credential-stuffing attempt, because there is nothing behind it.

**Everything a visitor *can* do is either read-only or designed to be abused.** Killing workers is not a vulnerability here; it is the demonstration. The self-healing property that makes it safe is the same property the product claims, which is why exposing it strengthens rather than weakens the instance.

**No capability is gated by identity.** §21.7 stands: no accounts, no auth, no sessions, no per-user state. Every restriction in §31.1 is a function of deployment mode alone. This is why there is no API keys page on the public instance — there is nothing to key.

**The two availability-only restrictions are labelled as such.** Environment editing and unbounded chaos parameters are withheld from the public instance to keep the demonstration functional, not because they are dangerous. Conflating availability restrictions with security boundaries makes both harder to reason about.

### 31.3 Required tests

Per §5.3, the boundary is asserted, not assumed:

- With `ANCHOR_AUTHORING_EXECUTE` unset, `POST /api/authoring/register` returns 404, **not 401 or 403** — the route does not exist, and the response should not imply that a credential would help
- With it unset, no import path in the API package reaches the registry-mutation code
- `/api/authoring/validate` and `/api/authoring/generate` succeed in both modes
- Submission and kill endpoints enforce their rate limits under concurrent load
- The reset affordance leaves `chaos_events` and chaos reports untouched

---

## 32. The outbound surface — links, attribution, and footer

The landing page of §21.3 is a demonstration, but it is also a public artifact that a reviewer arrives at from a resume link. It needs the ordinary furniture of a developer-tool page. That furniture is small, and specifying it prevents both omission and bloat.

### 32.1 Header

Persistent, quiet, three items:

- **Wordmark** — returns to the landing page
- **GitHub** — the repository. **This is the single most important outbound link on the site**, because the quickstart of §26.3 lives there and it is what converts a curious reviewer into one who understands the integration cost.
- **Console** — enters the instrument layer of §30 for anyone who wants depth past the guided demo

### 32.2 The live evidence badge

A small element in the header or immediately beneath the headline, reading the current headline result — for example `0 duplicates / 500 kills`.

**It must be read live from the most recent chaos report, never hardcoded.** Its value is that a technical visitor sees a measured claim before reading a single sentence of description; that value is entirely destroyed if the number is stale or invented. If no chaos run has completed, the badge is absent rather than showing a placeholder.

### 32.3 Attribution strip

One line beneath the demo, not a biography section:

- Author name, linked to a portfolio or professional profile
- Optionally a resume link
- Optionally a single cross-link to another project

**One line.** A project page that spends more vertical space on its author than on its evidence inverts the thing it is trying to demonstrate.

### 32.4 Footer

Small, quiet, at the bottom:

- Repository link, repeated — header links are missed more often than assumed
- License
- **The self-hosting statement, verbatim from §26.2:** this is a demonstration instance, not a hosted service
- A link to the design document in the repository, if the §18 add-if-early item was written. Per §18 it is the artifact a senior reviewer is most likely to actually read, which makes it worth one line of footer.

### 32.5 Explicitly excluded

Each of these is a default that a project page accumulates without anyone deciding to add it:

| Excluded | Why |
|---|---|
| Newsletter signup, social share buttons, notification prompts | The page has one job (§21.4) and every additional call to action competes with it |
| Analytics-driven modals or cookie banners beyond legal minimum | A modal between a reviewer and the demo costs reviewers, and every one lost is a total loss (§21.7's reasoning) |
| Pricing, plans, or a "get started free" CTA | Directly contradicts §26.2. Implying a hosted offering that does not exist is the one dishonest thing this page could do. |
| A features grid | The demo is the feature list, demonstrated rather than claimed |
| Testimonials or logos | There are no users. Manufacturing social proof for a demonstration instance is worse than having none. |

---

## 33. What Addendum E does not change

- **No change to the eight invariants, the worker loop, the data model, the protocol decisions of Addendum C, or the chaos harness.**
- **No authentication.** §31 achieves every restriction through deployment mode specifically so that §21.7 stands unmodified.
- **No change to build order** beyond the phase column in §30, which restates §15 and §23 rather than revising them. The landing surface and its outbound links remain last, after phase 8, because §23's dependency argument is unchanged: the evidence badge cannot be honestly built before the evidence exists.
- **No change to the claim.** Everything here is surface around the measured chaos-harness result.

---
---

# Addendum F — Agent authoring boilerplate *(post-launch, do not build now)*

**Addendum version:** 0.1 — placeholder
**Status:** Deferred. Nothing in this addendum is scheduled into the build order of §15 or §29. It is recorded here so the idea isn't lost, not so it gets built early. **Do not implement any part of this until the end product from phases 1–8 is working and demoed.**

## 34. The gap, stated for later

A developer writing `decide_next_step` can make a correctness mistake Anchor cannot catch — forgetting to filter already-completed items from a loop, forgetting a terminal `Done(...)` branch, holding state in a variable instead of reading it from `ctx`. The §27 validator catches mechanical contract violations (wrong return type, direct clock access, unregistered tools). It does not and cannot catch wrong business logic — no static analysis can verify intent it was never told.

## 35. What to build, once there's time

**A `_template.py` scaffold** in `runtime/agents/`, with the four-step shape (check first action → branch on result → check terminal condition → return next action) and TODO markers, so a new agent starts from a correct skeleton rather than a blank file.

**The three §21.5 demo agents, explicitly repurposed as reference implementations** — not just chaos-testing fixtures. The "long run" agent in particular should be the canonical worked example of the already-done filter pattern, and the README should point developers at it directly.

**A four-item pre-registration checklist**, cheap to write, catching exactly the mistakes surfaced by building this project:
```
[ ] Every branch reads state from ctx, never a variable held across calls
[ ] Every loop filters using ctx.completed_tool_args(...), not a counter
[ ] There is a reachable Done(...) branch once the loop's work is exhausted
[ ] Every ctx.call_tool(...) checks ctx.has_result(...) first
```

## 36. Why this is correctly sequenced last

None of this makes the runtime more correct — it makes *writing agents for* the runtime less error-prone, which is a different axis entirely. Per §15 and §29, the chaos harness and its measured invariants are the project's actual claim. This addendum is polish on the developer experience around that claim, and it should only be spent time on after the claim itself exists and is proven.
