Phase 3 Testing — Full Docker + manual walkthrough
Setup
powershell
cd ops/compose
docker compose up -d
docker compose ps

Verify all services up: postgres, redis, api, worker×3.

Test 1: Prove SKIP LOCKED (multiple workers claim in parallel)
1a. Submit 3 runs via Swagger

Open http://localhost:8000/docs

POST /api/runs three times with different inputs:

json
{
  "agent_type": "professor_outreach",
  "input": {"interests": "quantum"},
  "client_request_key": "phase3-test-001"
}
json
{
  "agent_type": "professor_outreach",
  "input": {"interests": "AI"},
  "client_request_key": "phase3-test-002"
}
json
{
  "agent_type": "professor_outreach",
  "input": {"interests": "robotics"},
  "client_request_key": "phase3-test-003"
}

Note the three run IDs — let's say 47, 48, 49.

1b. Watch workers claim them in parallel

In a terminal, tail worker logs:

powershell
docker compose logs -f worker

Expected output (happens within milliseconds):

worker-1 | run claimed: run_id=47, worker_id=worker-a#1, epoch=1
worker-2 | run claimed: run_id=48, worker_id=worker-b#1, epoch=1
worker-3 | run claimed: run_id=49, worker_id=worker-c#1, epoch=1

Key observation: All three happen at the same time (or within milliseconds). Without SKIP LOCKED, one would have to wait for the others.

1c. Verify in database
powershell
docker compose exec postgres psql -U anchor -d anchor
sql
SELECT id, status, owner_worker_id FROM runs WHERE id IN (47, 48, 49);

Expected:

 id | status  | owner_worker_id
----+---------+-----------------
 47 | running | worker-a#1
 48 | running | worker-b#1
 49 | running | worker-c#1

All three claimed by different workers. ✓

Test 2: Prove background renewal (lease stays alive)
2a. Submit a run that takes longer than lease duration

First, let's see what the lease duration is:

sql
SELECT lease_duration_ms, renewal_interval_ms FROM runtime_config;

Typical: lease_duration_ms = 4000 (4 seconds), renewal_interval_ms = 1000 (renew every 1 second).

2b. Create an agent that deliberately takes 10 seconds
python
# anchor/runtime/agents/slow_agent.py
import asyncio
from anchor.core.actions import Done

async def decide_next_step(ctx):
    # First call: sleep for 10 seconds (longer than 4-second lease)
    if not ctx.has_result("slow_step"):
        # In Phase 2, this would get fenced (lease expires at 4s)
        # In Phase 3, renewal extends lease every 1s, so we finish at 10s
        await asyncio.sleep(10)
        return ToolCall("slow_step", {})
    
    return Done({"slept": 10})

Actually, better: use a tool that's slow:

python
# anchor/runtime/agents/slow_agent.py
from anchor.core.actions import ToolCall, Done

async def decide_next_step(ctx):
    if not ctx.has_result("slow_tool"):
        # This tool will take 10 seconds
        return ToolCall("slow_tool", {"duration": 10})
    
    return Done({"slow_tool": "completed"})

Add the tool:

python
# anchor/runtime/tools.py
async def slow_tool(args):
    import asyncio
    duration = args.get("duration", 5)
    await asyncio.sleep(duration)
    return {"slept": duration}

DEMO_TOOLS = {
    ...
    "slow_tool": Tool(name="slow_tool", fn=slow_tool, safety="naturally_safe"),
    ...
}

Register the agent:

python
# anchor/runtime/agent_registry.py
agent_registry.register("slow_agent", agents.slow_agent.decide_next_step)

Rebuild:

powershell
docker compose up -d --build
2c. Submit a run with this agent
powershell
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "slow_agent",
    "input": {},
    "client_request_key": "phase3-slow-001"
  }'

Note the run ID — let's say 50.

2d. Watch the lease being renewed

In database, open new terminal:

powershell
docker compose exec postgres psql -U anchor -d anchor

Watch the lease_expires_at column being extended:

sql
-- Run this every 1 second
SELECT id, lease_expires_at, now() FROM runs WHERE id = 50;

Expected pattern:

t=0s:   lease_expires_at = 14:02:04 (now + 4s)
t=1s:   lease_expires_at = 14:02:05 (extended by renewer)
t=2s:   lease_expires_at = 14:02:06 (extended again)
t=3s:   lease_expires_at = 14:02:07
...
t=10s:  lease_expires_at = 14:02:14
t=11s:  RUN_COMPLETED, lease_expires_at = NULL

Key observation: The lease keeps moving forward every 1 second. If renewal didn't exist (Phase 2), it would expire at t=4s and the run would be stolen.

2e. Verify the run completes (not fenced)
powershell
curl http://localhost:8000/api/runs/50

Expected (after 11 seconds):

json
{
  "id": 50,
  "status": "completed",
  "owner_worker_id": null,
  "finished_at": "2026-08-09T14:02:11Z"
}

If renewal didn't work, you'd see the status stuck at running with a different owner_worker_id (fenced).

Test 3: Prove one worker can execute multiple runs concurrently
3a. Set up a single-worker scenario

Edit docker-compose.yml:

yaml
services:
  worker:
    # Change from replicas: 3 to replicas: 1
    deploy:
      replicas: 1

Rebuild:

powershell
docker compose down
docker compose up -d --build
docker compose ps

Now only one worker.

3b. Submit 2 fast runs
powershell
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "professor_outreach",
    "input": {"interests": "quantum"},
    "client_request_key": "phase3-concurrent-001"
  }'

curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "professor_outreach",
    "input": {"interests": "AI"},
    "client_request_key": "phase3-concurrent-002"
  }'

Note the run IDs — let's say 51, 52.

3c. Watch them execute in parallel

In worker logs:

powershell
docker compose logs -f worker

Expected:

worker | run claimed: run_id=51, worker_id=worker-a#1, epoch=1
worker | run claimed: run_id=52, worker_id=worker-a#1, epoch=1
worker | run 51: step 0 completed in 5ms
worker | run 52: step 0 completed in 4ms
worker | run 51: step 1 completed in 3ms
worker | run 52: step 1 completed in 2ms
...

Key observation: Both runs are executing on the same worker (same worker_id). Steps from both runs are interleaved (step 0 of 51, step 0 of 52, step 1 of 51, step 1 of 52, etc.).

3d. Time it

Phase 2 (sequential): two 6-second runs = 12 seconds total
Phase 3 (concurrent): two 6-second runs = ~6 seconds total

Watch the timestamps:

powershell
curl http://localhost:8000/api/runs/51
curl http://localhost:8000/api/runs/52

Compare created_at and finished_at. Both should start at roughly the same time and finish at roughly the same time (6 seconds apart, not 12).

Test 4: Prove TaskGroup cleanup (crash handling)
4a. Restore 3 workers
yaml
deploy:
  replicas: 3
powershell
docker compose up -d --build
4b. Submit a run
powershell
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "professor_outreach",
    "input": {},
    "client_request_key": "phase3-crash-001"
  }'

Note the run ID — let's say 53. Note which worker claimed it.

4c. Kill the worker mid-execution

Watch logs to see it executing, then:

powershell
docker compose kill worker-1
4d. Verify clean state (no orphaned renewal)

In database:

sql
SELECT id, owner_worker_id, lease_expires_at FROM runs WHERE id = 53;

Expected immediately after kill:

 id | owner_worker_id | lease_expires_at
----+-----------------+------------------
 53 | worker-a#1      | 2026-08-09 14:02:07

Wait 4 seconds for lease to expire.

Then (after lease expires):

powershell
curl http://localhost:8000/api/workers

A new worker should claim run 53:

powershell
curl http://localhost:8000/api/runs/53

Expected:

json
{
  "id": 53,
  "status": "running",
  "owner_worker_id": "worker-b#1",  // different worker!
  "epoch": 2  // incremented
}

Wait for completion:

json
{
  "id": 53,
  "status": "completed",
  "owner_worker_id": null,
  "epoch": 2
}

Key observation: Renewal task was cancelled when Worker-A died (TaskGroup cleanup). Lease wasn't extended endlessly. Another worker picked it up cleanly.

4e. Restart the killed worker
powershell
docker compose up -d worker-1
docker compose ps

Should see worker-1 back online with a new incarnation.

Summary checklist
 Test 1: Three runs claimed simultaneously (SKIP LOCKED)
 Test 2: 10-second step completes without fencing (renewal extends lease)
 Test 3: Two runs on one worker execute in parallel (TaskGroup)
 Test 4: Killed worker's renewal stops cleanly, run is picked up (TaskGroup cancellation)
 Bonus: Check event logs show no duplicates
powershell
# Event log for a run
curl http://localhost:8000/api/runs/51/events | jq '.[] | select(.type == "TOOL_RESULT") | .payload.tool_name'

# Should show each tool called once (no duplicates)
One command to run all Phase 3 tests
powershell
docker compose exec api pytest \
  tests/concurrency/test_exactly_one_claim.py \
  tests/concurrency/test_claim_under_load.py \
  tests/failure/test_long_step_not_fenced.py \
  tests/failure/test_taskgroup_cancels_sibling.py \
  -v

This proves Phase 3 all at once.