Testing Phase 4 — three ways
Way 1: Manual SQL test (fastest, most direct)
powershell
docker compose exec postgres psql -U anchor -d anchor

Then run this SQL:

sql
-- Create a test run
INSERT INTO runs (id, agent_type, input, status, epoch, owner_worker_id)
VALUES (999, 'test', '{}', 'running', 1, 'worker-a#1');

-- Write an event with epoch=1 (should succeed)
INSERT INTO run_events (run_id, type, payload, epoch, worker_id)
VALUES (999, 'TOOL_INTENT', '{}', 1, 'worker-a#1');

-- Check: should have 1 row
SELECT COUNT(*) FROM run_events WHERE run_id = 999;
-- Expected: 1

-- Now simulate reclaim: increment epoch to 2
UPDATE runs SET epoch = 2 WHERE id = 999;

-- Try to write with stale epoch=1 (should FAIL)
INSERT INTO run_events (run_id, type, payload, epoch, worker_id)
VALUES (999, 'TOOL_RESULT', '{}', 1, 'worker-a#1');
-- Expected: ERROR: lease fenced (AN001)

-- Check: should still have 1 row (zombie write rejected)
SELECT COUNT(*) FROM run_events WHERE run_id = 999;
-- Expected: 1

-- Try to write with correct epoch=2 (should succeed)
INSERT INTO run_events (run_id, type, payload, epoch, worker_id)
VALUES (999, 'TOOL_RESULT', '{}', 2, 'worker-b#1');

-- Check: should have 2 rows now
SELECT COUNT(*) FROM run_events WHERE run_id = 999;
-- Expected: 2

-- Cleanup
DELETE FROM run_events WHERE run_id = 999;
DELETE FROM runs WHERE id = 999;

If you see:

ERROR:  lease fenced (AN001)

Then Phase 4 works. ✓

Way 2: Pytest (automated)
powershell
docker compose exec api pytest tests/failure/test_zombie_worker_is_fenced.py -v

This test does the same thing programmatically. If it passes, Phase 4 works.

If the test doesn't exist, create it:

python
# tests/failure/test_zombie_worker_is_fenced.py
import pytest
from anchor.core.leases import claim_one
from anchor.core.events import append
from anchor.core.events.types import EventType

async def test_zombie_worker_is_fenced():
    """Prove that a zombie worker with stale epoch is rejected."""
    
    # 1. Claim a run
    claimed = await claim_one(conn, "worker-a#1", lease_duration_ms=4000)
    run_id, epoch = claimed
    assert epoch == 1
    
    # 2. Write with correct epoch (should succeed)
    await append(
        conn,
        run_id=run_id,
        type=EventType.TOOL_INTENT,
        payload={"tool": "search"},
        epoch=1,
        worker_id="worker-a#1",
        step_index=0
    )
    
    # 3. Simulate reclaim (epoch increments to 2)
    await conn.execute("UPDATE runs SET epoch = epoch + 1 WHERE id = $1", run_id)
    
    # 4. Try to write with stale epoch (should FAIL)
    with pytest.raises(Exception) as exc_info:
        await append(
            conn,
            run_id=run_id,
            type=EventType.TOOL_RESULT,
            payload={"result": "found"},
            epoch=1,  # ← stale epoch
            worker_id="worker-a#1",
            step_index=0
        )
    
    assert "lease fenced" in str(exc_info.value).lower()
    
    # 5. Verify the write was rejected (still only 1 event)
    events = await conn.fetch("SELECT * FROM run_events WHERE run_id = $1", run_id)
    assert len(events) == 1
    
    # 6. Write with correct epoch (should succeed)
    await append(
        conn,
        run_id=run_id,
        type=EventType.TOOL_RESULT,
        payload={"result": "found"},
        epoch=2,  # ← correct epoch
        worker_id="worker-b#1",
        step_index=0
    )
    
    # Verify both writes are now there
    events = await conn.fetch("SELECT * FROM run_events WHERE run_id = $1", run_id)
    assert len(events) == 2

Run it:

powershell
docker compose exec api pytest tests/failure/test_zombie_worker_is_fenced.py -v
Way 3: Docker setup + manual test

If you want to see it work end-to-end in the system:

powershell
# Terminal 1: Watch the API logs
docker compose logs -f api

# Terminal 2: Watch the worker logs
docker compose logs -f worker

# Terminal 3: Submit a run
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "professor_outreach", "input": {}, "client_request_key": "phase4-test"}'

# Note the run ID (let's say 60)

# Terminal 4: Open psql and do the manual test above
docker compose exec postgres psql -U anchor -d anchor
-- (run the SQL from Way 1, but with run_id=60)
The one-command verification
powershell
docker compose exec postgres psql -U anchor -d anchor -c "
INSERT INTO runs (id, agent_type, input, status, epoch, owner_worker_id) 
VALUES (999, 'test', '{}', 'running', 1, 'a');

INSERT INTO run_events (run_id, type, payload, epoch, worker_id) 
VALUES (999, 'X', '{}', 1, 'a');

UPDATE runs SET epoch = 2 WHERE id = 999;

INSERT INTO run_events (run_id, type, payload, epoch, worker_id) 
VALUES (999, 'Y', '{}', 1, 'a');
" 2>&1 | grep -i "fenced"

If you see lease fenced, Phase 4 works. ✓

Checklist
 Trigger exists: \df check_epoch_current shows the function
 Trigger fires: stale epoch write raises error
 Correct epoch writes succeed
 Rejected writes don't insert a row (count stays same)
 Epoch increments on reclaim (1 → 2 → 3)