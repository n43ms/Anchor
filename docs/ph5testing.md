# Testing phase 5 — the two-phase journal and "no double execution"

**Scope of this guide.** Phase 5 is the point at which Anchor's headline claim — *effectively-once
tool execution: no side effect runs twice, across any crash* — starts being true. This document is
two things: a manual, eyes-on-the-terminal walkthrough that shows the guarantee holding (and shows
`needs_review` being reached honestly instead of guessed), and a reference for running the automated
test suite that backs it. Read the manual section first if you have never seen the system run; read
the automated section first if you just want to know the suite is green.

**What "done" looks like for this phase**, restated from the constitution's exit gate: *the "no
double email" guarantee holds under a crash injected inside the uncertainty window, for each of the
three declared policies* — `retry_safe`, `reconcilable`, `unsafe`.

---

## Part A — Automated tests

### A.1 Prerequisites

- Python 3.12, `uv` installed (`pyproject.toml` pins the dependency set).
- A disposable PostgreSQL 16 and Redis 7 for the test suite. **Do not point tests at the
  `docker compose` dev stack's database** — the autouse fixture in `tests/conftest.py` truncates
  every table before each test, which would erase whatever you're using the dev stack to demo in
  Part B. Use a separate pair of containers:

  ```bash
  docker run -d --rm --name anchor-test-pg  -e POSTGRES_USER=anchor -e POSTGRES_PASSWORD=anchor \
    -e POSTGRES_DB=anchor_test -p 5432:5432 postgres:16
  docker run -d --rm --name anchor-test-redis -p 6379:6379 redis:7
  ```

  (These are the same images and defaults `tests/conftest.py` and `.github/workflows/ci.yml` assume,
  so no extra environment variables are required — `ANCHOR_TEST_DATABASE_URL` and
  `ANCHOR_TEST_REDIS_URL` already default to `localhost:5432/anchor_test` and `localhost:6379/1`.)

- Apply migrations against the test database once:

  ```bash
  uv run alembic -c ops/migrations/alembic.ini upgrade head
  ```

  (Alembic reads `ANCHOR_DATABASE_URL`; export it to the test DSN first —
  `export ANCHOR_DATABASE_URL=postgresql://anchor:anchor@localhost:5432/anchor_test` — or the
  migration applies to whatever your shell already has configured for `ANCHOR_DATABASE_URL`, which
  during normal development is the dev stack, not the test one. Applying it twice is harmless.)

### A.2 Everything phase 5 added, in isolation

```bash
# The property test that protects the entire idempotency mechanism — no DB needed.
uv run pytest tests/property/test_canonical_serialization.py -q

# Key derivation, framing, and stability across a simulated replay — no DB needed
# except test_journal_one_intent_per_key.py / test_journal_three_state_lookup.py.
uv run pytest tests/unit/test_idempotency_key_framing.py \
              tests/replay/test_key_identical_across_replay.py -q

# The journal table's own guarantees: PK uniqueness, the result-once trigger,
# the three-state lookup.
uv run pytest tests/unit/test_journal_one_intent_per_key.py \
              tests/unit/test_tool_journal_result_once.py \
              tests/unit/test_journal_three_state_lookup.py -q

# Tool registration: the three refusal conditions, the same rules as table CHECKs,
# and fleet-wide declaration conflicts.
uv run pytest tests/unit/test_tool_registration_refusals.py \
              tests/unit/test_tool_registry_checks.py \
              tests/failure/test_tool_declaration_conflict.py -q

# The headline guarantee itself: one test per declared policy, plus the
# Unknown()-escalates-like-unsafe case.
uv run pytest tests/failure/test_uncertainty_window.py -q

# demo_effects: the proof surface's own uniqueness, and that a legitimate
# retry_safe re-execution does not trip it.
uv run pytest tests/failure/test_demo_effects_unique.py -q

# Ordering guarantees: intent committed before invocation, one side effect per step,
# and a completed key replays via STEP_SKIPPED_ON_REPLAY without re-invoking the tool.
uv run pytest tests/failure/test_intent_committed_before_invocation.py \
              tests/unit/test_one_side_effect_per_step.py \
              tests/replay/test_step_skipped_on_replay_emitted.py -q

# needs_review holds no lease (the terminal-state-style CHECK), and the resolve
# endpoint's three outcomes end to end over a real ASGI app.
uv run pytest tests/boundary/test_needs_review_holds_no_lease.py \
              tests/contract/test_resolve_endpoint.py -q
```

### A.3 The whole suite, plus the gates CI runs

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy            # project config already scopes this to anchor/ + tests/
uv run pytest -q       # unit, property, replay, concurrency, failure, boundary, contract
```

All four must be clean before treating phase 5 as done — this is exactly what
`.github/workflows/ci.yml` runs on push, migrations included.

### A.4 What a failure here would mean

- A failure in `tests/property/test_canonical_serialization.py` means the idempotency key mechanism
  itself is unsound — treat it as the highest-priority failure in the suite, because everything else
  in this phase assumes canonicalization is deterministic.
- A failure in `tests/failure/test_uncertainty_window.py` means the "no double email" claim does not
  hold for at least one declared category — this is the one test class this phase exists to make
  pass.
- A failure in `tests/failure/test_demo_effects_unique.py`'s first test (forced duplicate rejected)
  means the database constraint that backs the entire proof surface is missing or was weakened —
  stop and treat this as a schema regression, not a flaky test.

---

## Part B — Manual, holistic walkthrough

This section runs the real system — three workers, a real PostgreSQL, real HTTP — and watches the
guarantee hold with your own eyes, the same way a reviewer would.

### B.1 Bring the stack up

```bash
cd ops/compose
docker compose up --build
```

Wait for `api` and all three `worker` replicas to report healthy. Confirm:

```bash
curl -s http://localhost:8000/api/health | python -m json.tool
```

Expect `"deployment_mode": "local"`, `"worker_count": 3`, `"degraded": false`.

> **Note on timing.** The demo tools' simulated latency is currently a small constant (`0.05s`) kept
> that way deliberately for test speed, not yet tuned to the ~2–5s-per-step demo-quality bar a public
> guided demo would want. Runs below complete in well under a second of tool time; the walkthrough
> still exercises every mechanism, it just does not *look* like a 25–40s demo.

### B.2 The happy path — `demo_short`

```bash
curl -s -X POST http://localhost:8000/api/runs \
  -H 'content-type: application/json' \
  -d '{"agent_type": "demo_short", "input": {"topic": "durable execution"}, "is_demo": true}' \
  | tee /tmp/run.json | python -m json.tool
RUN_ID=$(python -c "import json;print(json.load(open('/tmp/run.json'))['id'])")
```

Poll until terminal:

```bash
watch -n1 "curl -s http://localhost:8000/api/runs/$RUN_ID | python -m json.tool"
```

Once `status` is `completed`, read the full story back from the log — this is the audit trail the
constitution calls the spine of the system:

```bash
curl -s "http://localhost:8000/api/runs/$RUN_ID/events" | python -m json.tool
```

Look for, in order: `RUN_SUBMITTED` → `RUN_CLAIMED` → `REPLAY_COMPLETED` → per step
`STEP_STARTED` → (`TOOL_INTENT` → `TOOL_RESULT`) or `LLM_CALLED` → `STEP_COMPLETED` → `RUN_COMPLETED`.
Every `TOOL_INTENT` carries an `idempotency_key`; find its matching `TOOL_RESULT` and confirm the keys
match.

Then check the proof surface directly — the row count a reviewer can trust without reading the log
at all:

```bash
curl -s "http://localhost:8000/api/runs/$RUN_ID/effects" | python -m json.tool
```

Expect one row per side-effecting tool call (`web_search`, `fetch_page`, `create_ticket`,
`charge_card` each appear once — `demo_short` never calls `send_email`).

### B.3 The tool registry

```bash
curl -s http://localhost:8000/api/tools | python -m json.tool
```

Confirm all five named tools (`web_search`, `fetch_page`, `create_ticket`, `send_email`,
`charge_card`) plus the three phase-1 placeholders are listed, each with `"executable": true` and
`"conflict": null` — no worker has yet registered a conflicting declaration for any of them.

### B.4 Reaching `needs_review` honestly

`demo_unsafe` calls `send_email` (declared `unsafe`) at step 2. Landing a real crash inside its
uncertainty window — between the committed `TOOL_INTENT` and its `TOOL_RESULT` — means killing a
worker in the ~50ms gap between those two events, which is genuinely hard to time by hand at the
tools' current test-speed latency. Two practical options, in order of how much they change the
system versus how reliable they are:

**Option 1 — race a container kill against the log** (no code changes, low odds per attempt):

```bash
curl -s -X POST http://localhost:8000/api/runs \
  -H 'content-type: application/json' \
  -d '{"agent_type": "demo_unsafe", "input": {"recipient": "oncall@example.invalid"}, "is_demo": true}'

# In another terminal, watch for the intent:
docker compose logs -f worker | grep -m1 TOOL_INTENT
# The instant that line appears, kill the worker that logged it:
docker compose ps worker   # find the container name/id
docker kill <that-worker-container>
```

If it misses, the run simply completes normally and `send_email`'s `demo_effects` row appears once —
itself a correct, if less dramatic, demonstration. Re-run a few times.

**Option 2 — widen the window** (one local code change, reliable): bump `_LATENCY_S` in
`anchor/runtime/tools/demo.py` to a few seconds, `docker compose up --build worker` to rebuild just
the worker image, then repeat Option 1 — a multi-second window is trivial to hit by eye. Revert the
change afterward; it exists only to make the race winnable by a human, not as a permanent setting.

When you do land inside the window, poll the run:

```bash
curl -s "http://localhost:8000/api/runs/$RUN_ID" | python -m json.tool
```

Expect `"status": "needs_review"`, `"owner_worker_id": null`, `"lease_expires_at": null`, and a
`needs_review` object naming the exact call (`tool_name: "send_email"`, the `idempotency_key`, and
`available_resolutions: ["mark_executed", "mark_not_executed", "retry"]`). This is `I8` made visible:
the system is telling you, specifically, what it does not know — not guessing either way.

### B.5 Resolving it

Pick one:

```bash
# "It did happen" — writes the missing result now, attributed to the operator, and resumes.
curl -s -X POST "http://localhost:8000/api/runs/$RUN_ID/resolve" \
  -H 'content-type: application/json' -d '{"resolution": "mark_executed", "note": "confirmed in provider dashboard"}'

# "It did not happen" — authorizes real execution on the next resumption.
curl -s -X POST "http://localhost:8000/api/runs/$RUN_ID/resolve" \
  -H 'content-type: application/json' -d '{"resolution": "mark_not_executed"}'

# Re-consult the tool's own declared policy from a clean slate — for an unsafe
# tool this re-enters needs_review immediately, which is expected.
curl -s -X POST "http://localhost:8000/api/runs/$RUN_ID/resolve" \
  -H 'content-type: application/json' -d '{"resolution": "retry"}'
```

After `mark_executed` or `mark_not_executed`, the run returns to `pending`; watch it get reclaimed and
run to `completed`, then re-check `/effects` — **exactly one** `send_email` row, regardless of which
resolution you picked, because the whole point of the mechanism is that the count never depends on
how many times a worker actually attempted the call.

### B.6 Tearing down

```bash
docker compose down -v   # -v also drops the dev Postgres volume
docker stop anchor-test-pg anchor-test-redis   # if you started the test containers in Part A
```

---

## Known gaps in this pass

- **No timed, deterministic in-product way to crash exactly inside a tool's uncertainty window
  yet.** That is phase 8's chaos harness (`uncertainty_crash_injected`); until then, B.4's "race a
  container kill" or "temporarily widen the latency" are the only manual options, and the automated
  suite (`tests/failure/test_uncertainty_window.py`) is the reliable way to exercise all three
  policies deterministically.
- **T291** (execute the full V5 walkthrough end to end against a live `docker compose` fleet) has not
  been run from this environment — no Docker available here. Part B above is written so you can run
  it yourself and confirm the same six outcomes quickstart.md's V5 names.
