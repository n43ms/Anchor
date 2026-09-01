# ⚓ Anchor

**The PostgreSQL-Authoritative Durable Execution Engine for AI Agent Workflows.**

*Eliminate lost state and duplicate API calls when executing multi-step LLM agent pipelines. Anchor guarantees atomic two-phase tool journaling, monotonic epoch fencing, and sub-second crash recovery.*

---

### 🌐 Quick Links & Resources
- 🌐 **Official Website**: [https://anchor-runtime.xyz](https://anchor-runtime.xyz)
- 📹 **Live Video Demos**: [https://anchor-runtime.xyz/demo](https://anchor-runtime.xyz/demo)
- 📚 **Technical Documentation**: [https://anchor-runtime.xyz/docs](https://anchor-runtime.xyz/docs)
- 📦 **PyPI Package**: [`pip install anchor-runtime`](https://pypi.org/project/anchor-runtime/)
- 👤 **Author & Creator**: **Aditya Nema** ([LinkedIn](https://linkedin.com/in/adityaxnema) • [GitHub](https://github.com/n43ms/Anchor))

---

[![Apache 2.0 License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PyPI version](https://img.shields.io/badge/pypi-v1.6.0-emerald.svg)](https://pypi.org/project/anchor-runtime/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-amber.svg)](pyproject.toml)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://anchor-runtime.xyz)
[![Crash Recovery](https://img.shields.io/badge/crash_recovery-sub--second-success.svg)](https://anchor-runtime.xyz/demo)

---

## 🚀 Quickstart (Under 60 Seconds)

No API keys, no cloud subscriptions, and no complex cluster setups required to get started.

### 1. Install the Python SDK
```bash
pip install anchor-runtime
```

### 2. Boot Local Cluster & UI (1-Click Launch)
```bash
# 🌟 Recommended (Scaffolds workspace, boots PostgreSQL 16, API daemon, and opens Operator Console):
anchor dev
```
> *On Windows if PATH is not configured*: `python -m anchor.cli dev`  
> *Alternative manual boot*: `anchor init` followed by `docker compose up -d`.

### 3. Write & Run Your Agent (`app.py`)

Create `app.py`:

```python
import anchor, json

# 1. Custom Tool 0: Fetch Customer Data (Retry-Safe)
@anchor.tool(safety="retry_safe", naturally_idempotent=True)
def fetch_customer(customer_id: str) -> dict:
    return {"id": customer_id, "email": "aditya@anchor.dev", "tier": "VIP"}

# 2. Custom Tool 1: Dispatch Email Notification (Unsafe Side-Effect)
@anchor.tool(safety="unsafe")
def send_welcome_email(email: str, tier: str) -> dict:
    return {"status": "sent", "to": email, "tier": tier}

# 3. Multi-Tool Durable Agent Workflow
@anchor.agent(name="onboarding_agent")
def decide_next_step(ctx: anchor.StepContext):
    customer = yield anchor.ToolCall("fetch_customer", {"customer_id": ctx.input["customer_id"]})
    email_res = yield anchor.ToolCall("send_welcome_email", {"email": customer["email"], "tier": customer["tier"]})
    yield anchor.Done({"status": "completed", "customer": customer, "email": email_res})

# 4. Trigger & Submit to Engine
if __name__ == "__main__":
    result = anchor.run("onboarding_agent", input={"customer_id": "cust_99"})
    print(json.dumps(result, indent=2))
```

Run `python app.py`. `anchor.run()` serializes the workflow AST and submits it to PostgreSQL. Cluster workers claim the run, execute steps, and log atomic two-phase tool journals. Inspect live execution at `http://localhost:3000` or [https://anchor-runtime.xyz](https://anchor-runtime.xyz)!

---

## 📹 Video Demonstrations & Empirical Benchmarks

Watch live recordings of Anchor handling hard process terminations, unsafe tool pauses, and adversarial fault injections:

- 📺 **[01. End-to-End Multi-Step LLM Workflow](https://anchor-runtime.xyz/demo)** — Parallel market intelligence lookup, Gemini 2.5 Flash LLM synthesis, and email delivery.
- ⚡ **[02. SIGKILL Process Interrupt & Auto-Reclaim](https://anchor-runtime.xyz/demo)** — Hard process termination mid-run with sub-second lease reclamation by secondary worker.
- 🛡️ **[03. Unsafe Tool Pause & NeedsReview Queue](https://anchor-runtime.xyz/demo)** — `@anchor.tool(safety="unsafe")` protection protocol halting runs for operator resolution (`mark_executed` / `mark_not_executed`).
- 💥 **[04. Live Adversarial Fault Injection Harness](https://anchor-runtime.xyz/demo)** — Real-time random SIGKILL terminations across parallel worker replicas.
- 📊 **[05. Invariant Verification Log Proof](https://anchor-runtime.xyz/demo)** — Benchmark logs proving 5/5 SQL invariants held under load.

👉 **[Watch All Video Demos at anchor-runtime.xyz/demo](https://anchor-runtime.xyz/demo)**

---

## 💡 Why Choose Anchor?

Current AI agent frameworks (LangGraph, CrewAI) rely on **in-memory buffers or naive Redis checkpoints** — causing process crashes to re-execute non-idempotent tool calls, double-charge payment APIs, and corrupt database state. 

Meanwhile, legacy enterprise orchestrators (Temporal, AWS Step Functions) require hosting **massive external clusters ($5,000+/mo cloud tax)** built for microservices, not non-deterministic Python LLM loops. 

Anchor fills this void as a lightweight, PostgreSQL-authoritative engine embedding **atomic two-phase tool journaling** (`INTENT` / `RESULT`) and **monotonic epoch fencing** (`AN001`) to guarantee **zero duplicate side-effects** and **sub-second recovery** natively in SQL.

### 📊 Competitive Architecture Comparison Matrix

| Feature | Anchor Runtime | LangGraph / CrewAI | Temporal / Step Functions |
| :--- | :--- | :--- | :--- |
| **State Authority** | **PostgreSQL 16 Engine** (`FOR UPDATE SKIP LOCKED`) | Volatile Memory / Redis Checkpoints | Dedicated Cassandra / MySQL Cluster |
| **Infrastructure Tax** | **$0/mo** (Runs in existing DB) | $0/mo (Unsafe) | **$5,000+/mo** (Massive External Cluster) |
| **Two-Phase Side-Effect Guard** | **Atomic INTENT / RESULT Journal** | ❌ Duplicate API Calls | ⚠️ Activity Heartbeats |
| **Monotonic Epoch Fencing** | **Database Constraint (`AN001`)** | ❌ Split-Brain Risk | ❌ Application-Level |
| **SIGKILL Recovery Time** | **P50 < 3.1s** | ❌ Process Crash Data Loss | ⚠️ 10s+ Timeout Window |
| **Developer API** | **Native Python Generators** | Complex Graph State Handoffs | Multi-File SDK Boilerplate |

---

## 💰 Financial ROI & Execution Safety

When AI agents execute multi-step tasks — searching database records, calling third-party APIs, or processing payments — server crashes normally result in lost progress and double-billing. Anchor acts as an immutable flight recorder: every step is saved before it runs, so if a server dies, another takes over instantly with zero wasted credits.

* **Financial Savings Analysis**: On 1,000,000 multi-step LLM requests per month with a 2% node crash rate, unmanaged retries cost over **$12,400/mo** in duplicate prompt tokens. Anchor's step-level result cache reduces wasted token charges to **$0**.
* **Idempotent Side-Effect Guarding**: If a worker process is terminated by Kubernetes SIGKILL while calling a payment endpoint or database mutation, Anchor checks the `TOOL_INTENT` sequence ID on recovery to prevent duplicate charges or corrupt row insertions.

---

## 🏗️ System Architecture & Formal SQL Invariants

Anchor enforces mathematical correctness through five formal SQL invariants verified continuously by an automated chaos harness:

```
                                    ┌───────────────────────┐
                                    │    Client SDK / API   │
                                    │  (POST /api/runs)     │
                                    └───────────┬───────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │   FastAPI Daemon      │
                                    │   (Stateless Router)  │
                                    └───────────┬───────────┘
                                                │
                                                ▼
  ┌───────────────────────────────────────────────────────────────────────────────────┐
  │                           PostgreSQL 16 Engine Core                               │
  │  ┌───────────────────────┐   ┌───────────────────────┐   ┌─────────────────────┐  │
  │  │  SELECT FOR UPDATE    │   │ Two-Phase Tool        │   │ AN001 Epoch Fencing │  │
  │  │  SKIP LOCKED Queue    │   │ INTENT/RESULT Journal │   │ Monotonic Triggers  │  │
  │  └───────────────────────┘   └───────────────────────┘   └─────────────────────┘  │
  └─────────────────────────────────────▲─────────────────────────────────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           │                            │                            │
  ┌────────┴────────┐          ┌────────┴────────┐          ┌────────┴────────┐
  │ Worker Replica  │          │ Worker Replica  │          │ Worker Replica  │
  │  (Process A)    │          │  (Process B)    │          │  (Process C)    │
  └─────────────────┘          └─────────────────┘          └─────────────────┘
```

### Core Engine Invariants:
1. **`I1` (Idempotency)**: `COUNT(duplicate_side_effects) == 0`. Zero non-idempotent tool calls executed twice.
2. **`I2` (Log Monotonicity)**: Append-only event sequence integrity backed by database triggers.
3. **`I3` (Single Writer)**: `AN001` monotonic epoch-fenced single-active-writer guarantee blocking zombie worker writes.
4. **`I4` (Terminal Reachability)**: All runs reach deterministic terminal states (`completed`, `failed`, `needs_review`).
5. **`I5` (Replay Determinism)**: Step replays reconstruct full generator state from journal logs in `<5ms`.

---

## 🛠️ Repository Structure

```
Anchor/
├── anchor/                      # Python Core SDK & Engine Daemon
│   ├── api/                     # FastAPI Router & Endpoint Definitions
│   ├── core/                    # PostgreSQL Protocol Logic, Fencing & Replay
│   ├── chaos/                   # Automated Chaos Harness & SQL Invariant Asserter
│   └── worker/                  # Worker Claim Loop & Process Lifecycle
├── demo-site/                   # Standalone Interactive Site & Video Demos (React/Vite)
├── web/                         # Production Next.js 14 Operator Console UI
├── ops/
│   ├── compose/                 # Production Docker Compose Stack & Dockerfiles
│   └── migrations/              # Alembic DDL Migrations (001_foundation to 006_chaos)
├── GTM_LAUNCH_PLAYBOOK.md       # Go-To-Market & Monetization Master Playbook
└── pyproject.toml               # Python Package Spec (anchor-runtime)
```

---

## 📄 License & Commercial Rights

Anchor is open-source software licensed under the **[Apache License 2.0](LICENSE)**. You are free to use, modify, distribute, and embed Anchor in commercial products without copyleft restrictions.

- 👤 **Author & Creator**: Aditya Nema  
- 🌐 **Official Website**: [https://anchor-runtime.xyz](https://anchor-runtime.xyz)  
- 📹 **Video Demos**: [https://anchor-runtime.xyz/demo](https://anchor-runtime.xyz/demo)  
- 📚 **Documentation**: [https://anchor-runtime.xyz/docs](https://anchor-runtime.xyz/docs)  
- 🔗 **LinkedIn**: [linkedin.com/in/adityaxnema](https://linkedin.com/in/adityaxnema)  
- ⭐ **GitHub Repository**: [github.com/n43ms/Anchor](https://github.com/n43ms/Anchor)
