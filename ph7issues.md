# Anchor System Audit & Spec Traceability Report (Phase 7 / Full System)

**Date**: 2026-08-21  
**Scope**: Full Stack (Phase 0 through Phase 7 Scope: `backend/anchor`, `web/`, PostgreSQL DDL, API Contracts, Redis Telemetry)  
**Reference Document**: [`specs/001-anchor-durable-execution-runtime/tasks.md`](specs/001-anchor-durable-execution-runtime/tasks.md)  
**Phase Boundary**: Audited strictly against Phase 0 through Phase 7 deliverables (Phase 8 Chaos Harness and Phase 9 Authoring Surface are scheduled downstream)  
**Status**: Comprehensive Audit & Defect Root-Cause Analysis (No Code Changes Applied)

---

## 1. Executive Summary

Anchor's core durable execution foundation (PostgreSQL transaction isolation, monotonic epoch gate triggers, append-only event logs, and two-phase tool idempotency hashing) is largely built according to the spec. However, **critical integration disconnects exist between the backend API and the operator frontend**, leading to broken worker management, ghost/stale worker accumulation, silent API 404s, and several visual surfaces that currently rely on hardcoded synthetic mock data instead of real engine telemetry.

---

## 2. Phase-by-Phase Traceability Matrix (Phases 0–7 vs Frontend Presence)

| Phase | Spec Tasks | Backend Implementation (`anchor/`) | Frontend Surface (`web/`) | Current Status / Health |
|---|---|---|---|---|
| **Phase 0 — Foundation** | T001–T062 | `ops/migrations/versions/001_foundation.py`, `anchor/core/db/`, `anchor/core/config/`, `anchor/worker/registry/` | `app/(console)/settings/environment/page.tsx`, `useHealth.ts` | **Operational**. DB clocks, trigger constraints, and health endpoint connect correctly. |
| **Phase 1 — Log is the Spine** | T063–T104 | `anchor/core/events/`, `anchor/api/routers/runs.py`, `anchor/runtime/agents/` | `app/(console)/runs/page.tsx`, `app/(console)/runs/[id]/page.tsx`, `app/(console)/logs/page.tsx` | **Operational**. Events append contiguously, log table is queryable. |
| **Phase 2 — Replay (Hard Gate)** | T105–T144 | `anchor/core/replay/`, `anchor/core/determinism/`, `anchor/worker/loop.py` | `components/run/RunDetail.tsx`, `components/run/RunThread.tsx`, `TimelineTrack.tsx` | **Operational**. Reconstructs state from event stream; step skips render with distinct markers. |
| **Phase 3 — Concurrency & Leases** | T145–T190 | `anchor/core/leases/claim.py`, `renew.py`, `anchor/api/routers/workers.py` | `app/(console)/workers/page.tsx`, `app/(console)/workers/deployments/page.tsx`, `useWorkers.ts` | **CRITICAL DEFECTS**: `POST /api/workers/{id}/kill` is missing (returns 404); dead worker incarnations accumulate as stale nodes. |
| **Phase 4 — Fencing Tokens (Hard Gate)** | T191–T228 | `anchor/core/leases/fencing.py`, `anchor/core/events/append.py` (`AN001`) | `components/run/FencingMarker.tsx`, `components/run/RunDetail.tsx` | **Operational**. Stale epoch writes are rejected by PostgreSQL trigger and rendered as fencing collision markers. |
| **Phase 5 — Two-Phase Journal & Policies** | T229–T292 | `anchor/core/journal/`, `anchor/runtime/tools/demo.py`, `resolve` endpoint | `app/(console)/needs-review/page.tsx`, `app/(console)/needs-review/[id]/page.tsx` | **Partially Degraded**: Unresolved `needs_review` runs accumulate indefinitely because demo resets only archive completed runs. |
| **Phase 6 — Production Behaviour** | T293–T378 | `anchor/api/ws/`, `anchor/api/serializers/rollup.py`, `observability.py` | `app/(console)/metrics/page.tsx`, `hooks/useRunStream.ts`, `hooks/useFleetStream.ts` | **DEGRADED**: Rollup job creates sparse buckets locally; metrics charts render empty unless heavy traffic exists. |
| **Phase 7 — Operator Console** | T379–T473 | API endpoints consumed by Next.js / Vite console | Full UI under `web/app/(console)/` and `web/components/` | **CONTAINS MOCK COMPONENTS**: Bottom terminal, Guard Stack cards, 3D Canvas badges, and Health Matrix panels contain hardcoded/simulated data. |
| **Phase 8 — Chaos & Landing** | T474–T551 | *Phase 8 Scope (Deferred)* | *Phase 8 Scope (Deferred)* | **Scope Boundary**: Client API has forward-looking stubs (`api.startChaos`), but endpoints are properly deferred to Phase 8. |
| **Phase 9 — Authoring Surface** | T552–T592 | *Phase 9 Scope (Deferred)* | *Phase 9 Scope (Deferred)* | **Scope Boundary**: Static AST lint CLI (`anchor lint`) is scheduled for Phase 9. |

---

## 3. Deep-Dive Root-Cause Analysis of Critical Issues

### Issue 1: Unable to Kill Workers (`404 Not Found` in `/runs` and `/workers`)
- **Observed Behavior**: Clicking "Kill Owner" in `/runs/[id]` or "kill" / "graceful stop" in `/workers` displays a red error: `Not Found` or `kill request failed`.
- **Root Cause in Code**:
  - `web/lib/api.ts` issues `POST /api/workers/${encodeURIComponent(id)}/kill`.
  - In `anchor/api/routers/workers.py`, the endpoint was **never registered**. Lines 7–14 state:
    ```python
    # The kill endpoints (`POST /api/workers/{worker_id}/kill`) are deferred to
    # phase 8: their documented response carries a `chaos_event_id`...
    ```
  - However, the underlying Redis kill mechanism **is already fully implemented** in `anchor/worker/registry/kill.py` (`publish_kill` and `subscribe_and_wait_for_kill`). Every worker is already listening on Redis channel `anchor:kill:{worker_id}`.
  - Because FastAPI has no route for `/api/workers/{worker_id}/kill`, every kill request returns `HTTP 404 Not Found`.

---

### Issue 2: Permanent "Fleet is below expected complement" & Zombie Worker Flood
- **Observed Behavior**: The fleet grid shows dozens of stale worker nodes and permanently displays a red alert: `"fleet is below its expected complement"`.
- **Root Cause in Code**:
  - **Worker Registration Model**: In `anchor/worker/registry/register.py`, every time a worker process starts or restarts, it inserts a **brand new row** with incremented `incarnation` (e.g. `worker-1#1`, `worker-1#2`, `worker-1#3`).
  - **Query Lacks Deduplication**: Both `GET /api/workers` (`anchor/api/routers/workers.py`) and `WS /ws/fleet` (`anchor/api/ws/fleet.py`) execute:
    ```sql
    SELECT * FROM workers ORDER BY label, incarnation DESC
    ```
    This returns every historical dead incarnation that has ever registered since database creation.
  - **Staleness Calculation**: `serialize_worker` marks any worker with `heartbeat_age > 15s` as `stale = true`. All historical incarnations are permanently stale.
  - **Degraded Status Flag**: In `anchor/api/ws/fleet.py` line 33:
    ```python
    degraded = any(w["stale"] for w in workers)
    ```
    Because old incarnation rows remain in the table forever, `degraded` evaluates to `true` on every single frame, permanently triggering the alert `"fleet is below its expected complement"`.

---

### Issue 3: All Runs Accumulate in `Needs Review` Queue
- **Observed Behavior**: The Needs Review queue keeps growing with runs and never clears.
- **Root Cause in Code**:
  1. **Demo Reset Filter**: `POST /api/runs/demo/reset` (`anchor/api/routers/runs.py` line 481) executes:
     ```sql
     UPDATE runs SET archived_at = now()
     WHERE is_demo = true AND status IN ('completed', 'failed', 'cancelled')
     ```
     By spec design (§21.6), `needs_review` runs are **exempt from bulk demo reset** so operators are forced to resolve them.
  2. **Empty-State Launch Button Bug**: In `web/app/(console)/page.tsx` line 261, the empty state button was hardcoded to:
     ```tsx
     onClick={() => handleQuickLaunch("refund-agent")}
     ```
     `refund-agent` is **not registered** in `anchor/runtime/agents/registry.py` (which only registers `demo_short`, `demo_long`, `demo_minimal`, and `demo_unsafe`). Submitting this triggers validation failure or fallback.
  3. **Unsafe Tool Halting**: When `demo_unsafe` is executed, step 2 calls `send_email` (declared `safety = "unsafe"`). Any process interruption, simulated chaos crash, or unresolved state transition immediately halts the run to `status = 'needs_review'`.

---

### Issue 4: Stale & Inaccurate Worker Stats on Dashboard
- **Observed Behavior**: Workload counters show erratic run counts, and capacity progress bars appear filled even when workers have 0 runs.
- **Root Cause in Code**:
  1. **Historical Rows Included**: The dashboard counts runs across all workers returned by `useWorkers()`, including inactive/stale dead incarnations.
  2. **Hardcoded CSS Clamp**: In `web/app/(console)/page.tsx` line 377:
     ```tsx
     width: `${Math.min(100, Math.max(10, (w.current_run_count / (w.capacity || 1)) * 100))}%`
     ```
     The `Math.max(10, ...)` forces the progress bar to be at least **10% filled** even when `current_run_count == 0`, giving the false appearance of background load.

---

### Issue 5: Telemetry Metrics Don't Work / Charts are Empty
- **Observed Behavior**: Visiting `/metrics` shows empty graphs ("run state distribution", "fencing events over time", "throughput vs worker count").
- **Root Cause in Code**:
  - `GET /api/metrics` (`anchor/api/routers/observability.py`) reads time series strictly from `metrics_rollup`.
  - `metrics_rollup` is populated by the background task `_rollup_forever()` in `anchor/api/app.py`.
  - In local development or fresh deployments with few events, rollup buckets are empty (`rollup_rows == []`).
  - When `rollup_rows` is empty, the API returns `run_state_distribution: []`, `fencing_events_series: []`, and `throughput_by_worker_count: null`.
  - The frontend chart component has no fallback for sparse data, resulting in empty boxes.

---

## 4. Comprehensive Inventory of ALL Mock Components & Synthetic Data (Phase 7 Scope)

The following components and files in the frontend codebase currently generate or display **synthetic, hardcoded, or simulated mock data**:

### 1. `web/components/shell/TerminalConsole.tsx` (100% Mock Data)
- **What it does**: Runs an internal `setInterval` every 4.5 seconds to append randomly selected fake telemetry strings (`DEFAULT_LOGS` and `sampleEvents` like `"AST step executed: step_23 recorded in durable state"`).
- **Impact**: Generates illusionary logs completely disconnected from actual WebSocket engine events or database transactions.

### 2. `web/components/shell/RightInspectorPanel.tsx` — Guard Stack Tab (100% Mock Data)
- **What it does**: Hardcodes 4 guard cards (`GUARDS` constant):
  - *OOM Prevention*: `"Heap Memory: 412MB / 2048MB"`, `"85% auto-fence"`
  - *Infinite Loop Breaker*: `"Step Limit: 100 steps/seg"`, `"50 max cycle"`
  - *Auto Healer*: `"Self Healed: 3 recoveries"`, `"0 side effects"`
  - *Deadlock & Fence Guard*: `"Token Epoch: seq 4092 verified"`, `"0 split-brain"`
- **Impact**: Displays static mock metrics with fake green blinking lights.

### 3. `web/components/shell/RightInspectorPanel.tsx` — Health Matrix Tab (Partial Mock Data)
- **What it does**: Hardcodes fake SLA and performance figures:
  - `"Cluster Uptime: 99.998%"` (hardcoded static string)
  - `"Duplicate Effects: 0 (VERIFIED)"` (hardcoded static string)
  - `"Active Leases: 4 / 4 Held"` (hardcoded static string)
  - `"Throughput: 142.8 steps/s"` (hardcoded static string)
- **Impact**: Misrepresents live cluster health with hardcoded perfection numbers.

### 4. `web/components/canvas/GoldenThreadsCanvas.tsx` — 3D Agent Steps (100% Mock Data)
- **What it does**: Hardcodes an array of 4 floating 3D checkpoint badges (`AGENT_STEPS` constant):
  - `STEP 1: LEASE ACQUIRED` (`worker-1 held`)
  - `STEP 2: AST EXECUTION` (`step 14 durable`)
  - `STEP 3: FENCE VERIFIED` (`seq 4092 assigned`)
  - `STEP 4: CHECKPOINT SECURED` (`0 duplicate effects`)
- **Impact**: Renders hardcoded static step text floating in the background 3D canvas regardless of whether runs are active or idle.

### 5. `web/components/shell/GuardStackSidebar.tsx` & `RuntimeHealthPanel.tsx` (Orphaned Mock Files)
- **What they are**: Earlier-generation shell panels that were superseded by `RightInspectorPanel.tsx` but remain in the codebase containing duplicated hardcoded mock constants (`GUARDS` array and static SLA metrics).

### 6. `web/components/run/mocks/` (Static Mock Runs Directory)
- **Files**:
  - `reference.ts`: 5-step refund-agent mock run
  - `fortySteps.ts`: 40-step mock run
  - `manyHandoffs.ts`: Mock run with 4 worker handoffs
  - `needsReview.ts`: Mock run in `needs_review` state
  - `orphaned.ts`: Mock run in orphaned state
  - `zeroHandoffs.ts`: Clean single-worker mock run
- **Where used**: Used by `web/app/(dev)/preview/page.tsx` and unit tests.

### 7. `web/app/(console)/page.tsx` — Telemetry Header Fallbacks & CSS Hacks
- **What it does**:
  - Hardcodes fallback values in the top telemetry bar (`metrics?.lease_duration_ms ?? 4000`, `health.global_concurrency_cap ?? 50`).
  - Progress bar has `Math.max(10, ...)` CSS width clamp forcing idle workers to appear loaded.

---

## 5. Additional System Deficiencies, Unhandled Edge Cases & UI Inconsistencies (Phase 0–7)

### Defect 8: Ghost Deployments on `/workers/deployments`
- **Location**: `web/app/(console)/workers/deployments/page.tsx`
- **Issue**: The Deployments page groups all worker entries by `w.code_version`. Because `useWorkers()` returns all dead historical incarnations, builds that were decommissioned hours or days ago remain rendered under "ACTIVE BUILDS".
- **Impact**: Operators cannot tell which code versions are genuinely running vs historical ghosts.

### Defect 9: Inconsistent Styling and Legacy Token Usage in `needs-review/[id]/page.tsx`
- **Location**: `web/app/(console)/needs-review/[id]/page.tsx`
- **Issue**: While the rest of the console was modernized to glassmorphism (`bg-black/40`, `border-white/[0.08]`, `backdrop-blur-2xl`), the individual Needs Review detail page still uses legacy color tokens (`text-ink-muted`, `bg-surface-panel`, `border-gridline`, `bg-surface-page`).
- **Impact**: Visual jarring and broken contrast when inspecting review items.

### Defect 10: Non-Demo Run Cancellation Lockdown
- **Location**: `anchor/api/routers/runs.py` (Line 406)
- **Issue**: In `cancel_run()`, the backend enforces:
  ```python
  if app.state.deployment_mode == "demonstration" and not run_row["is_demo"]:
      raise HTTPException(403, detail="only demo runs may be cancelled in demonstration mode")
  ```
  If an operator submits a custom run via `/tools/test-run` with `is_demo = false` while in demonstration mode, clicking "Cancel" in the UI errors out with an unhandled 403 response without informative explanation.

### Defect 11: Fixed Limit without Keyset Pagination in Logs Viewer
- **Location**: `web/app/(console)/logs/page.tsx`
- **Issue**: The logs page hardcodes `limit: 100`. There is no cursor pagination button ("Load Previous / Next Events") to traverse beyond the latest 100 log entries, cutting off audit trails for long-running workflows.

### Defect 12: Missing Empty-State Feedback in `Chart.tsx`
- **Location**: `web/components/primitives/Chart.tsx`
- **Issue**: When a time series has 0 data points (`points: []`), `Chart.tsx` draws an empty SVG `<polyline points="" />` without an empty state notice, and renders an empty table body in table view.

### Defect 13: Missing Optimistic UI Revalidation upon Run Resolution
- **Location**: `web/app/(console)/needs-review/[id]/page.tsx` & `runs/[id]/page.tsx`
- **Issue**: When `resolveRun` is triggered, the run transitions to `pending` on the server, but the client does not optimistically update the timeline state or trigger a WebSocket re-sync, requiring a full page refresh to confirm.

### Defect 14: WebSocket Slow Consumer Recovery Handling
- **Location**: `web/hooks/useRunStream.ts` & `web/hooks/useFleetStream.ts`
- **Issue**: When the backend closes a client queue with `SLOW_CONSUMER_CLOSE_CODE` (`4001`), the frontend hooks treat it as a generic network drop and immediately attempt reconnect without resetting dropped frames.

---

## 6. Comprehensive Remediation Roadmap (Phase 0–7 Integrity)

1. **Register `POST /api/workers/{worker_id}/kill`**:
   - Mount the route in `anchor/api/routers/workers.py`.
   - Publish directly to Redis `anchor:kill:{worker_id}` via `publish_kill`.
   - Support both `graceful: false` (`os._exit(1)`) and `graceful: true`.

2. **Deduplicate Fleet Queries by Slot Label**:
   - Change `GET /api/workers` and `/ws/fleet` queries to:
     ```sql
     SELECT DISTINCT ON (label) * FROM workers ORDER BY label, incarnation DESC
     ```
   - Calculate `degraded` solely by comparing count of live, healthy slots against the configured complement.

3. **Eliminate All Mock Data from the Console**:
   - **Terminal Console**: Connect to live backend telemetry events or active run event stream.
   - **Guard Stack**: Read real live counters from PostgreSQL (active leases, current fencing incidents, unhandled tool errors).
   - **Health Matrix**: Dynamically compute cluster uptime, active leases, and throughput from live database tables (`runs`, `run_events`).
   - **3D Canvas**: Remove hardcoded `AGENT_STEPS` badges from `GoldenThreadsCanvas.tsx`.
   - **Empty State**: Fix the quick launch button to dispatch `"demo_short"`.
   - **Capacity Bar**: Remove `Math.max(10, ...)` clamp.

4. **Provide Fallback Live Aggregation for Metrics**:
   - When `metrics_rollup` has fewer than 2 buckets, aggregate live counts directly from `run_events` on `GET /api/metrics` so charts render cleanly from step 1.

5. **Harmonize `needs-review/[id]/page.tsx` & `Chart.tsx` Styling**:
   - Upgrade all legacy token classes (`text-ink-muted`, `bg-surface-panel`) to the console's glassmorphic dark-theme design standard.

---

## 7. Deep-Dive: Where Phase 1–6 Engine Deliverables are Rendered on the Phase 7 Frontend

This section details exactly where and how every single engine capability, invariant, and data structure implemented across Phases 1 through 6 surfaces in the Phase 7 Operator Console:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PHASE 7 OPERATOR CONSOLE MAPPING                                     │
├──────────────────────────┬──────────────────────────────────────────┬──────────────────────────────────┤
│ Backend Phase & Feature  │ Frontend Surface & Component             │ Exact Visual Representation      │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 1: 17 Event Types  │ • web/components/run/RawEventLog.tsx     │ Expandable JSON tree per event   │
│ & Append-Only Log        │ • web/app/(console)/logs/page.tsx        │ with seq, type badge, timestamp  │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 1: Run Submission  │ • web/app/(console)/page.tsx             │ 1-Click Launch buttons and       │
│ & Client Request Dedupe  │ • web/app/(console)/tools/test-run       │ dynamic agent dispatch forms     │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 2: State Fold      │ • web/components/run/RunDetail.tsx       │ Reconstructed step counts,       │
│ & Step-Skip on Replay    │ • web/components/run/TimelineTrack.tsx   │ duration, and dashed skip blocks │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 2: Determinism     │ • web/components/run/RunThread.tsx       │ Reticle rings (#34d399) marking  │
│ & Recorded Nondet Values │ • web/components/run/ThreadMarkers.tsx   │ skipped steps along the spline   │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 3: Worker Claims   │ • web/app/(console)/workers/page.tsx     │ Worker grid with capacity bars,  │
│ & Heartbeat Renewal      │ • web/components/run/WorkerBar.tsx       │ uptime, and lease progress fills │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 4: Fencing Token   │ • web/components/run/FencingMarker.tsx   │ Red collision flags on timeline  │
│ Rejections (AN001)       │ • web/app/(console)/metrics/page.tsx     │ and fencing spike metric charts  │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 5: Two-Phase       │ • web/app/(console)/needs-review         │ Interactive uncertainty console  │
│ Journal & 3 Policies     │ • web/app/(console)/needs-review/[id]    │ with operator resolution buttons │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 5: Zero-Duplicate  │ • web/app/(console)/page.tsx (Hero KPI)  │ "0 Duplicate Effects (Verified)" │
│ Side-Effect Guarantee    │ • web/app/(console)/tools/page.tsx       │ tile & tool safety classification│
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 6: Live WebSockets │ • web/hooks/useRunStream.ts              │ 60fps flowing execution ribbons  │
│ & Rolling Metrics        │ • web/app/(console)/metrics/page.tsx     │ and live cluster status pills    │
├──────────────────────────┼──────────────────────────────────────────┼──────────────────────────────────┤
│ Phase 6: Live Config     │ • web/app/(console)/settings/environment │ 15-parameter live edit matrix    │
│ & Demo Reset Controls    │ • web/app/(console)/page.tsx (Header)    │ and one-click demo reset toast   │
└──────────────────────────┴──────────────────────────────────────────┴──────────────────────────────────┘
```

### Detailed Breakdown by Engine Feature

#### 1. Phase 1: Event Log & Contiguous Sequence (`run_events`)
- **`RawEventLog.tsx` (`/runs/[id]`)**: Directly consumes `GET /api/runs/{id}/events`. Every single row in `run_events` is displayed with its contiguous `seq` integer, discriminated event type badge (`STEP_STARTED`, `TOOL_INTENT`, `TOOL_RESULT`, `LLM_CALLED`, `STEP_COMPLETED`, `RUN_COMPLETED`), epoch, emitting worker ID, and an expandable interactive JSON payload viewer with clipboard copy.
- **`LogsPage.tsx` (`/logs`)**: Surfaces the global event log across all runs via `GET /api/events`. Allows operators to filter by all 17 event types and worker ID.
- **`RunsPage.tsx` (`/runs`)**: Consumes `GET /api/runs` with server-side keyset pagination (`after_id`) and status filtering.

#### 2. Phase 2: Replay Reconstructor & Step Skip (`reconstruct.py`)
- **`RunDetail.tsx` (`/runs/[id]`)**: Renders the folded execution state from `reconstruct.py` (accumulated messages, total duration, last completed step index, and total handoffs).
- **`TimelineTrack.tsx`**: Steps marked with `status === "skipped_on_replay"` render with dashed borders (`borderLeft: "1px dashed rgba(165, 180, 252, 0.5)"`) and 45% opacity, visually indicating that no real execution time was consumed.
- **`ThreadMarkers.tsx` & `RunThread.tsx`**: Renders replayed steps as **Emerald Mint Reticle Rings** (`data-shape="ring"`, `#34d399`) mathematically anchored along the animated ribbon.

#### 3. Phase 3: Leases, Ownership & Concurrency (`anchor.core.leases`)
- **`FleetPage.tsx` (`/workers`)**: Maps `GET /api/workers` directly to cards displaying worker identity (`label#incarnation`), uptime, current run count vs capacity, heartbeat age in milliseconds, and code version.
- **`Dashboard Fleet Grid` (`/`)**: Displays color-coded worker nodes (`var(--worker-1)`, `var(--worker-2)`, `var(--worker-3)`) showing real-time load distribution.
- **`WorkerBar.tsx`**: Renders deep indigo / electric blue progress bars representing the active worker's execution segment across handoffs.

#### 4. Phase 4: Fencing Tokens & Zombie Detection (`AN001` / `WORKER_FENCED`)
- **`FencingMarker.tsx`**: When a stale worker attempts a write and is rejected by the database trigger, the resulting `WORKER_FENCED` event is rendered as an alert flag directly on the timeline track at the exact fractional point in time (`xPercent`). Clicking or hovering displays `fenced_worker_id`, `stale_epoch`, `current_epoch`, and whether it was detected by `renewer` or `append`.
- **`ThreadMarkers.tsx`**: Handoff points between workers render as luminous **Sun-Gold Beacon Nodes** (`var(--strand-gold)` with white core and `#glow-gold`).
- **`MetricsPage.tsx` (`/metrics`)**: The `"fencing events over time"` chart plots the fencing frequency series over selected time windows.

#### 5. Phase 5: Two-Phase Journal & Uncertainty Policies (`tool_journal`)
- **`NeedsReviewPage.tsx` (`/needs-review`)**: Directly queries `GET /api/runs?status=needs_review`. Lists all runs halted at the uncertainty window following a worker crash during non-idempotent tool calls.
- **`NeedsReviewDetailPage.tsx` (`/needs-review/[id]`)**: Displays the ambiguous tool call, declared policy (`unsafe`), step index, and cryptographic `idempotency_key`. Provides interactive resolution buttons (`mark executed`, `mark not executed`, `retry`) that issue `POST /api/runs/{id}/resolve`.
- **`ToolRegistryPage.tsx` (`/tools`)**: Consumes `GET /api/tools` to display all registered tools, their declared safety category (`retry_safe`, `reconcilable`, `unsafe`), reconciler presence, and execution gate status.
- **`Dashboard Hero KPI` (`/`)**: Displays `duplicate side effects: 0 (verified live)` backed by PostgreSQL queries against `demo_effects` and `STEP_SKIPPED_ON_REPLAY`.

#### 6. Phase 6: WebSockets, Metrics Rollup & Live Admin Config
- **`useRunStream.ts` (`WS /ws/runs/{id}`)**: Drives the 60fps wave motion on `RunThread.tsx` and dynamically appends steps in real-time as workers write to the log.
- **`useFleetStream.ts` (`WS /ws/fleet`)**: Pushes full fleet state updates on worker heartbeat ticks and lease acquisitions without page reloads.
- **`EnvironmentPage.tsx` (`/settings/environment`)**: Consumes `GET /api/config` and `PATCH /api/config` to allow live tuning of all 15 runtime timing parameters.
- **`TestRunPage.tsx` (`/tools/test-run`)**: Dispatches custom workflows via `POST /api/runs` using agent descriptors loaded dynamically from `GET /api/agents`.

---
*Report fully updated and committed to `auditph7.md`.*
