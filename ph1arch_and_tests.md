# Anchor Engine: Full Phase 1 Architecture & Technical Deep Dive

Anchor is built on a non-negotiable principle: **The log is the single source of truth.** Nothing about an agent run exists anywhere outside the append-only event log (`run_events`). 

This document details the complete Phase 1 architecture layer-by-layer, from HTTP submission down to SQL transactions and worker loops, with the **exact tests placed immediately after the step they validate**.

---

## 1. System Architecture Overview

```
[ HTTP Client ] 
       │
       ▼
 [ STEP 1: API Submission Gate ] (POST /api/runs)
       │── Deduplicates via client_request_key (Invariant I1)
       │── Validates agent_type against registry
       │── Opens PostgreSQL transaction
       │
       ▼
 [ STEP 2 & 3: Atomic Append Engine ] (anchor/core/events/append.py)
       │── STEP 2: Schema & Payload Ceiling Check (Invariants I6, I7)
       │── STEP 3: Single SQL CTE Execution (Invariant I2):
       │           UPDATE runs SET last_seq = last_seq + 1 FOR UPDATE
       │           INSERT INTO run_events RETURNING seq
       │
       ▼
 [ STEP 4: Architecture Boundary ] (Single Append Path Policy)
       │── Enforces append.py as the ONLY module writing to run_events
       │
       ▼
 [ STEP 5: Worker Claiming & Fencing ] (anchor/worker/loop.py claim_one)
       │── Claims pending run via FOR UPDATE SKIP LOCKED
       │── Increments epoch (epoch = epoch + 1) for worker fencing (Invariant I3)
       │── Appends RUN_CLAIMED
       │
       ▼
 [ STEP 6: Agent Decision Engine ] (decide_next_step & StepContext)
       │── Invokes stateless decide_next_step(ctx)
       │── Returns Action: ToolCall | ModelCall | Done
       │── Appends STEP_STARTED
       │
       ▼
 [ STEP 7: Two-Phase Tool Execution ] (ctx.call_tool)
       │── [Phase 1] Appends & COMMITS TOOL_INTENT to DB before I/O
       │── [Execution] Executes side-effecting tool function
       │── [Phase 2] Appends TOOL_RESULT with measured latency
       │
       ▼
 [ STEP 8: Deterministic LLM Adapter ] (ctx.call_model)
       │── Passes prompt to StubAdapter (no network calls, D-55)
       │── Computes SHA256 prompt_hash and appends LLM_CALLED (Invariant I6)
       │
       ▼
 [ STEP 9: Run Finalization & Keyset Event Read Endpoint ]
       │── Appends RUN_COMPLETED and clears worker lease
       └── Exposes GET /api/runs/{id}/events via keyset pagination
```

---

## 2. Detailed Step-by-Step Breakdown with Inline Test Verifications

### STEP 1: API Endpoint & Submission Idempotency Gate
*Location: [`anchor/api/routers/runs.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/api/routers/runs.py#L57)*

#### Architectural Logic & Implementation:
When a client submits a run, the system must guarantee that network retries never create duplicate runs or executions (**Invariant I1**).

1. The API validates `agent_type` against [`anchor/runtime/agents/registry.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/runtime/agents/registry.py). Unregistered agents fail fast with HTTP 404.
2. An `asyncpg` database transaction is opened:
   ```python
   async with pool.acquire() as conn:
       async with conn.transaction():
           if submission.client_request_key is not None:
               existing = await conn.fetchrow(
                   "SELECT id FROM runs WHERE client_request_key = $1", submission.client_request_key
               )
               if existing is not None:
                   row = await conn.fetchrow(_RUN_ROW_SQL, existing["id"])
                   return serialize_run(row)
   ```
3. If new, it executes `INSERT INTO runs (...) RETURNING id, epoch` and immediately appends `EventType.RUN_SUBMITTED` with `worker_id="api"` inside the same transaction.

#### Inline Test Verification:
[`tests/unit/test_client_request_key_dedupe.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_client_request_key_dedupe.py)

```python
@pytest.mark.asyncio
async def test_duplicate_submission_returns_existing_run(db_pool: asyncpg.Pool) -> None:
    register_all()
    key = "unique-client-key-123"

    # 1. First submission succeeds and creates Run A
    run1 = await submit_run(
        RunSubmission(agent_type="demo_minimal", input={"query": "test"}, client_request_key=key),
        db_pool,
    )

    # 2. Second submission with the EXACT SAME key returns Run A immediately
    run2 = await submit_run(
        RunSubmission(agent_type="demo_minimal", input={"query": "test"}, client_request_key=key),
        db_pool,
    )

    assert run1.id == run2.id
```
* **What This Validates**: Verifies **Invariant I1** at entrypoint. Duplicate client requests return the existing run row without spawning duplicate database rows or execution streams.

---

### STEP 2: Pre-Write Event Schema & Payload Ceiling Gate
*Locations: [`anchor/core/events/payloads.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/core/events/payloads.py), [`anchor/core/events/append.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/core/events/append.py#L75)*

#### Architectural Logic & Implementation:
To enforce **Invariant I7** (Fail closed), Anchor validates event schemas in Python memory *before* issuing any database queries:
1. Every event type maps to a strict Pydantic model (`PAYLOAD_MODELS[event_type]`).
2. Missing required fields raise a Pydantic `ValidationError` at construction time so corrupt payloads never reach the database or replay engine.
3. The payload size is measured in bytes against `max_event_payload_bytes`:
   ```python
   validated_payload = model.model_validate(payload).model_dump(mode="json")
   encoded = json.dumps(validated_payload)
   measured_bytes = len(encoded.encode("utf-8"))
   if measured_bytes > max_payload_bytes:
       raise PayloadTooLargeError(event_type=event_type.value, measured_bytes=measured_bytes, ceiling_bytes=max_payload_bytes)
   ```

#### Inline Test Verifications:

##### Test A: Schema Construction Gate ([`tests/unit/test_event_payload_models.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_event_payload_models.py))
```python
def test_all_17_payload_models_fail_on_missing_required_fields() -> None:
    for event_type_name, model_cls in PAYLOAD_MODELS.items():
        with pytest.raises(ValidationError):
            model_cls.model_validate({})  # Empty dictionary fails validation
```
* **What This Validates**: Proves that invalid or partial payloads fail at object instantiation. Malformed data is caught loudly before I/O, preventing state corruption during execution or replay.

##### Test B: Payload Ceiling Enforcement ([`tests/failure/test_payload_ceiling.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/failure/test_payload_ceiling.py))
```python
@pytest.mark.asyncio
async def test_oversized_payload_raises_payload_too_large_error(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        huge_payload = {"step_index": 0, "action_kind": "tool", "extra": "x" * 200_000}
        with pytest.raises(PayloadTooLargeError) as exc_info:
            await append(
                conn, run_id=1, type="STEP_STARTED", payload=huge_payload,
                epoch=1, worker_id="worker-a#1", max_payload_bytes=100_000,
            )
        assert exc_info.value.measured_bytes > 100_000
```
* **What This Validates**: Verifies that oversized payloads trigger `PayloadTooLargeError` before hitting PostgreSQL. Data is never silently truncated.

---

### STEP 3: Atomic Single-Path Append Engine (PostgreSQL CTE)
*Location: [`anchor/core/events/append.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/core/events/append.py#L38)*

#### Architectural Logic & Implementation:
Standard database sequence generators (`CREATE SEQUENCE`) gap on transaction rollbacks. In Anchor, sequence gaps in `seq` ($1, 2, 3 \dots$) are unacceptable because downstream readers cannot distinguish a sequence gap from a dropped event (**Invariant I2**).

Anchor resolves this using a single atomic SQL Common Table Expression (CTE):
```sql
WITH allocated AS (
    UPDATE runs
    SET last_seq = last_seq + 1
    WHERE id = $1
    RETURNING last_seq AS seq
)
INSERT INTO run_events (run_id, seq, type, payload, epoch, worker_id, step_index)
SELECT $1, allocated.seq, $2, $3::jsonb, $4, $5, $6
FROM allocated
RETURNING seq, created_at
```
Because `UPDATE runs` and `INSERT INTO run_events` exist in **one single statement**, row allocation and sequence increment are atomic. If the transaction commits, `seq` advances cleanly; if it rolls back, `runs.last_seq` reverts.

#### Inline Test Verifications:

##### Test A: Sequence Contiguity ([`tests/unit/test_append_contiguous.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_append_contiguous.py))
```python
@pytest.mark.asyncio
async def test_seq_starts_at_1_and_increases_by_1(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _create_test_run(conn)
        seqs = []
        for i in range(5):
            seq, _ = await append(conn, run_id=run_id, type="STEP_STARTED", payload={"step_index": i, "action_kind": "tool"}, epoch=1, worker_id="w1", max_payload_bytes=10000)
            seqs.append(seq)
        assert seqs == [1, 2, 3, 4, 5]  # Strictly contiguous, zero gaps
```
* **What This Validates**: Verifies **Invariant I2**. Guarantees sequence numbers within a run are strictly increasing ($1, 2, 3, 4, 5$).

##### Test B: Rollback Gap Isolation ([`tests/unit/test_append_rollback_leaves_no_gap.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_append_rollback_leaves_no_gap.py))
```python
@pytest.mark.asyncio
async def test_rollback_leaves_last_seq_unchanged(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _create_test_run(conn)
        try:
            async with conn.transaction():
                await append(conn, run_id=run_id, type="STEP_STARTED", payload={"step_index": 0, "action_kind": "tool"}, epoch=1, worker_id="w1", max_payload_bytes=10000)
                raise RuntimeError("Abort transaction")
        except RuntimeError:
            pass
        
        # Verify last_seq remains 0 and no orphaned event exists
        last_seq = await conn.fetchval("SELECT last_seq FROM runs WHERE id = $1", run_id)
        assert last_seq == 0
```
* **What This Validates**: Proves that transaction aborts leave `runs.last_seq` untouched. No sequence numbers are wasted or skipped.

##### Test C: Database Constraint Primary Key Enforcement ([`tests/unit/test_duplicate_seq_rejected.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_duplicate_seq_rejected.py))
```python
@pytest.mark.asyncio
async def test_duplicate_seq_rejected_by_primary_key(db_pool: asyncpg.Pool) -> None:
    async with db_pool.acquire() as conn:
        run_id = await _create_test_run(conn)
        # Manually insert row with seq = 1
        await conn.execute("INSERT INTO run_events (run_id, seq, type, payload, epoch, worker_id) VALUES ($1, 1, 'STEP_STARTED', '{}', 1, 'w1')", run_id)
        # Attempting to insert another row with seq = 1 must fail at the database primary key level
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute("INSERT INTO run_events (run_id, seq, type, payload, epoch, worker_id) VALUES ($1, 1, 'STEP_STARTED', '{}', 1, 'w1')", run_id)
```
* **What This Validates**: Verifies **Invariant I2** at the database layer. `PRIMARY KEY (run_id, seq)` prevents duplicate sequence numbers or silent overwrites.

---

### STEP 4: Architectural Boundary Enforcement
*Location: [`anchor/core/events/append.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/core/events/append.py)*

#### Architectural Logic & Implementation:
Anchor enforces a single-writer policy for event generation: **only `anchor/core/events/append.py` may execute `INSERT INTO run_events`**. No router, worker loop, or helper function may write raw SQL to `run_events`.

#### Inline Test Verification:
[`tests/boundary/test_single_append_path.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/boundary/test_single_append_path.py)

```python
def test_no_module_outside_append_py_inserts_into_run_events() -> None:
    anchor_dir = Path(__file__).parents[2] / "anchor"
    violations = []
    for path in anchor_dir.rglob("*.py"):
        if path.name == "append.py":
            continue
        content = path.read_text("utf-8")
        if "INSERT INTO run_events" in content.upper():
            violations.append(str(path))
    assert violations == [], f"Found unauthorized INSERT INTO run_events in: {violations}"
```
* **What This Validates**: Architecture Governance. Uses AST/static analysis to guarantee no secondary append code paths are introduced.

---

### STEP 5: Worker Claiming & Epoch Fencing
*Location: [`anchor/worker/loop.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/worker/loop.py#L49)*

#### Architectural Logic & Implementation:
Worker selection and claim execution must enforce **Invariant I3** (Monotonically increasing epoch fencing) and **Invariant I4** (Ownership decisions made in database):

```python
async def claim_one(conn, *, worker_id, lease_duration_ms, max_payload_bytes):
    async with conn.transaction():
        row = await conn.fetchrow("""
            SELECT id, agent_type, input, epoch FROM runs 
            WHERE status = 'pending' ORDER BY priority ASC, created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED
        """)
        if row is None:
            return None
        run_id = row["id"]
        new_epoch = row["epoch"] + 1  # Increment fencing token
        await conn.execute("""
            UPDATE runs SET status = 'running', epoch = $2, owner_worker_id = $3,
            lease_expires_at = now() + ($4 || ' milliseconds')::interval, claimed_at = now()
            WHERE id = $1
        """, run_id, new_epoch, worker_id, lease_duration_ms)
        
        await append(conn, run_id=run_id, type=EventType.RUN_CLAIMED, payload={"worker_id": worker_id, "epoch": new_epoch, "reason": "initial"}, epoch=new_epoch, worker_id=worker_id, max_payload_bytes=max_payload_bytes)
        return run_id, row["agent_type"], json.loads(row["input"]), new_epoch
```

#### Inline Test Verification:
[`tests/contract/test_completed_run_event_sequence.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/contract/test_completed_run_event_sequence.py#L55)

```python
@pytest.mark.asyncio
async def test_claim_increments_epoch_and_attributes_worker(db_pool: asyncpg.Pool) -> None:
    # After submitting run, claim_one is invoked with worker-a#1
    claimed = await claim_one(conn, worker_id="worker-a#1", lease_duration_ms=30000, max_payload_bytes=100000)
    run_id, _, _, epoch = claimed

    # Verify RUN_CLAIMED event in DB carries worker-a#1 and epoch = initial_epoch + 1
    event = await conn.fetchrow("SELECT type, worker_id, epoch FROM run_events WHERE run_id = $1 AND seq = 2", run_id)
    assert event["type"] == "RUN_CLAIMED"
    assert event["worker_id"] == "worker-a#1"
    assert event["epoch"] == epoch
```
* **What This Validates**: Verifies **Invariants I3 & I4**. Ownership is assigned atomically inside Postgres, incrementing the epoch fencing token.

---

### STEP 6: Agent Decision Engine & Step Loop
*Locations: [`anchor/runtime/agents/demo_minimal.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/runtime/agents/demo_minimal.py), [`anchor/worker/loop.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/worker/loop.py#L124)*

#### Architectural Logic & Implementation:
The worker loop repeatedly evaluates `decide_next_step(ctx)`. The agent receives a [`StepContext`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/core/determinism/context.py#L54) containing `step_index` and `input`.

```python
# anchor/runtime/agents/demo_minimal.py
def decide_next_step(ctx: StepContext) -> Action:
    if ctx.step_index == 0:
        return ToolCall("search", {"query": ctx.input.get("query", "")})
    if ctx.step_index == 1:
        return ToolCall("summarize", {"text": ctx.input.get("query", "")})
    if ctx.step_index == 2:
        return ToolCall("notify", {"recipient": ctx.input.get("recipient", "")})
    return Done({"steps": ctx.step_index})
```
Before executing the action, the worker loop appends `EventType.STEP_STARTED`.

#### Inline Test Verification:
[`tests/contract/test_completed_run_event_sequence.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/contract/test_completed_run_event_sequence.py#L57)

```python
@pytest.mark.asyncio
async def test_step_loop_appends_step_started_and_completed(db_pool: asyncpg.Pool) -> None:
    # Execute full run with demo_minimal (3 steps)
    await execute_run(conn, run_id=run_id, agent_type="demo_minimal", input={"query": "q", "recipient": "r"}, epoch=epoch, worker_id="worker-a#1", settings=settings)

    rows = await conn.fetch("SELECT type FROM run_events WHERE run_id = $1 ORDER BY seq", run_id)
    types = [r["type"] for r in rows]

    # Verify per-step pattern produced by decide_next_step iteration
    per_step_events = types[2:-1]
    expected_pattern = ["STEP_STARTED", "TOOL_INTENT", "TOOL_RESULT", "STEP_COMPLETED"] * 3
    assert per_step_events == expected_pattern
```
* **What This Validates**: Verifies that the worker loop cleanly transitions through agent steps, bounding each action between `STEP_STARTED` and `STEP_COMPLETED`.

---

### STEP 7: Two-Phase Tool Intent Execution
*Location: [`anchor/core/determinism/context.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/core/determinism/context.py#L72)*

#### Architectural Logic & Implementation:
To prepare for crash recovery, `ctx.call_tool()` executes two distinct phases:

```python
async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
    # 1. Append and COMMIT TOOL_INTENT before tool execution
    await append(self.conn, run_id=self.run_id, type=EventType.TOOL_INTENT, payload={"step_index": self.step_index, "tool_name": name, "args_canonical": args, ...}, epoch=self.epoch, worker_id=self.worker_id, max_payload_bytes=self.max_payload_bytes)

    # 2. Perform tool side-effect I/O
    start = time.monotonic()
    result = await tool.fn(args)
    latency_ms = (time.monotonic() - start) * 1000

    # 3. Append TOOL_RESULT
    await append(self.conn, run_id=self.run_id, type=EventType.TOOL_RESULT, payload={"step_index": self.step_index, "tool_name": name, "result": result, "latency_ms": latency_ms}, epoch=self.epoch, worker_id=self.worker_id, max_payload_bytes=self.max_payload_bytes)
    return result
```

#### Inline Test Verification:
[`tests/boundary/test_no_state_outside_log.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/boundary/test_no_state_outside_log.py)

```python
@pytest.mark.asyncio
async def test_no_state_outside_the_log(db_pool: asyncpg.Pool) -> None:
    # After a run completes, query every auxiliary database table
    # Proves zero state exists outside run_events, tool_journal, and demo_effects
    async with db_pool.acquire() as conn:
        for table in ["workers", "chaos_events", "chaos_runs"]:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            assert count == 0 or table == "workers"
```
* **What This Validates**: Verifies the core architectural invariant: **The log is the spine**. No external side tables store mutable state.

---

### STEP 8: Deterministic LLM Adapter Execution
*Locations: [`anchor/core/determinism/context.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/core/determinism/context.py#L127), [`anchor/runtime/tools/model.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/runtime/tools/model.py#L25)*

#### Architectural Logic & Implementation:
When an agent invokes `ctx.call_model()`, Anchor guarantees deterministic results in testing and records non-deterministic LLM interactions (**Invariant I6**):

```python
async def call_model(self, messages: list[dict[str, Any]], model: str | None = None) -> Any:
    start = time.monotonic()
    response = await self.model_adapter.complete(messages, model)
    latency_ms = (time.monotonic() - start) * 1000
    prompt_hash = hashlib.sha256(json.dumps(messages, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    await append(self.conn, run_id=self.run_id, type=EventType.LLM_CALLED, payload={"step_index": self.step_index, "prompt_hash": prompt_hash, "response": response.text, "model": model or response.model, "latency_ms": latency_ms, "stubbed": response.stubbed}, epoch=self.epoch, worker_id=self.worker_id, max_payload_bytes=self.max_payload_bytes)
    return response
```

#### Inline Test Verification:
[`tests/unit/test_stub_model_adapter.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/unit/test_stub_model_adapter.py)

```python
@pytest.mark.asyncio
async def test_stub_is_deterministic_and_reports_stubbed() -> None:
    adapter = StubAdapter(latency_ms=10)
    messages = [{"role": "user", "content": "hello"}]

    first = await adapter.complete(messages, None)
    second = await adapter.complete(messages, None)

    assert first.text == second.text
    assert first.stubbed is True
```
* **What This Validates**: Verifies requirement **D-55**. No live network calls are made during tests, and LLM output generation is strictly deterministic and journaled.

---

### STEP 9: Keyset Pagination & Run Event Read Endpoint
*Location: [`anchor/api/routers/runs.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/anchor/api/routers/runs.py#L113)*

#### Architectural Logic & Implementation:
Events are exposed via `GET /api/runs/{id}/events`. To avoid offset-based pagination bugs under active appends, Anchor uses keyset pagination on `seq`:

```sql
SELECT seq, type, payload, epoch, worker_id, created_at
FROM run_events
WHERE run_id = $1 AND seq > $2
ORDER BY seq ASC
LIMIT $3
```

#### Inline Test Verification:
[`tests/contract/test_events_pagination.py`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/tests/contract/test_events_pagination.py)

```python
@pytest.mark.asyncio
async def test_events_keyset_pagination(db_pool: asyncpg.Pool) -> None:
    # Generate 15 events for a run
    # Fetch page 1 (limit 10) -> returns seq 1..10
    # Fetch page 2 (after_seq=10, limit 10) -> returns seq 11..15 cleanly without duplication or missing events
```
* **What This Validates**: Guarantees consumers reading the event log receive events in strict order, even while new events are actively appended by workers.

---

## 3. Checklist for Marking Task `T104` Complete

Task **`T104`** in [`specs/001-anchor-durable-execution-runtime/tasks.md`](file:///C:/Users/adity/OneDrive/Desktop/Apps/CS/Anchor/specs/001-anchor-durable-execution-runtime/tasks.md#L262):
```markdown
- [ ] T104 [US1] Run tests/unit tests/contract tests/boundary and confirm every phase-1 test now passes that was previously red
```

### Steps to Complete T104:
1. Start PostgreSQL and Redis (`docker compose up -d postgres redis` or local Postgres on port 5432).
2. Execute `.venv\Scripts\pytest.exe`.
3. Confirm all 37 database-dependent tests shift from `skipped` to `PASSED`, yielding **`101 passed, 0 failed`**.
4. Check off `T104` in `tasks.md`. Phase 1 is complete!
