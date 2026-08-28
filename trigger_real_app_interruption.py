"""
Triggers a real interruption during app.py's draft_email (safety="unsafe")
sending to adityaxnema@gmail.com with live Gemini LLM completion.

How it works:
1. Registers `wikipedia_langchain_researcher` from app.py.
2. Submits a new run (`Quantum Computing` -> `adityaxnema@gmail.com`).
3. Monitors progress: Step 0 (Wikipedia API) -> Step 1 (Gemini LLM) -> Step 2 (draft_email).
4. Hard kills the worker container (`docker kill`) during draft_email's 15s execution window.
5. Verifies cluster recovery transitions status to `NEEDS_REVIEW`.
6. Tests the API Guard (`resolution="retry"` -> HTTP 400 rejection).
"""

import asyncio
import json
import urllib.request
import urllib.error
import subprocess

API_URL = "http://localhost:8000"

def http_post(path: str, data: dict, expect_error: bool = False) -> tuple[int, dict]:
    url = f"{API_URL}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if expect_error:
            body = json.loads(e.read().decode("utf-8"))
            return e.code, body
        raise

def http_get(path: str) -> dict:
    url = f"{API_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))

async def run_real_agent_interruption():
    print("=" * 65)
    print("  Real Agent Workflow Interruption Trigger (app.py)")
    print("=" * 65)

    # 1. Register agent from app.py
    with open("app.py", "r", encoding="utf-8") as f:
        app_source = f.read()

    print("\n[1] Registering real agent 'wikipedia_langchain_researcher' from app.py...")
    http_post("/api/authoring/register", {
        "source": app_source,
        "agent_type": "wikipedia_langchain_researcher"
    })
    print("    [+] Agent registered successfully with cluster.")

    # 2. Submit run
    print("\n[2] Submitting run payload (Recipient: adityaxnema@gmail.com)...")
    code, submit = http_post("/api/runs", {
        "agent_type": "wikipedia_langchain_researcher",
        "input": {
            "topic": "Quantum Computing",
            "email": "adityaxnema@gmail.com"
        }
    })
    run_id = submit["id"]
    display_id = submit.get("display_id", f"run_{run_id}")
    print(f"    [+] Created Run #{run_id} ({display_id})")

    # 3. Watch events for draft_email TOOL_INTENT
    print("\n[3] Watching event log for 'draft_email' (unsafe) TOOL_INTENT...")
    print("    (Step 0: Wikipedia API -> Step 1: Gemini LLM -> Step 2: draft_email)")
    
    owner_worker = None
    hostname = None
    intent_found = False

    for attempt in range(600):
        try:
            events = http_get(f"/api/runs/{run_id}/events")
            for item in events.get("items", []):
                if item.get("type") == "TOOL_INTENT" and item.get("payload", {}).get("tool_name") == "draft_email":
                    intent_found = True
                    print(f"    [!] DETECTED TOOL_INTENT for 'draft_email' (Seq: #{item.get('seq')})")
                    break

            if intent_found:
                run_data = http_get(f"/api/runs/{run_id}")
                owner_worker = run_data.get("owner_worker_id")
                if owner_worker:
                    workers_data = http_get("/api/workers")
                    for w in workers_data.get("items", []):
                        if w.get("id") == owner_worker:
                            hostname = w.get("hostname")
                            break
                    break
        except Exception:
            pass
        await asyncio.sleep(0.1)

    if not intent_found or not owner_worker:
        print("[-] Timed out waiting for draft_email TOOL_INTENT.")
        return

    # 4. Kill worker container while sleeping
    print(f"\n[4] HARD KILLING worker container '{hostname or owner_worker}' mid-flight during draft_email...")
    cmd = f"docker kill {hostname or owner_worker}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"    [+] Worker killed: {res.stdout.strip()}")

    # 5. Polling status for needs_review
    print("\n[5] Waiting for cluster recovery monitor to transition run to 'needs_review'...")
    for _ in range(30):
        try:
            r = http_get(f"/api/runs/{run_id}")
            st = r.get("status")
            print(f"    - Run #{run_id} Status: {st.upper()}")
            if st == "needs_review":
                print("\n" + "=" * 65)
                print(f"  SUCCESS! Real Run #{run_id} ({display_id}) IS IN 'NEEDS_REVIEW' STATUS! ")
                print("=" * 65)
                
                # 6. Test API Guard: Retry resolution rejection
                print("\n[6] Verification: Testing API Guard for resolution='retry'...")
                status_code, err_body = http_post(f"/api/runs/{run_id}/resolve", {"resolution": "retry"}, expect_error=True)
                print(f"    - HTTP Response Code: {status_code}")
                print(f"    - Rejected Error Response: {json.dumps(err_body, indent=2)}")

                print("\n" + "=" * 65)
                print("👉 OPEN YOUR BROWSER NOW:  http://localhost:3000/needs-review/%d" % run_id)
                print("   1. Notice 'Retry (disabled)' button greyed out with explanatory tooltip.")
                print("   2. Click 'Mark Executed' or 'Mark Not Executed' to finish execution!")
                print("=" * 65 + "\n")
                return
        except Exception:
            pass
        await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(run_real_agent_interruption())
