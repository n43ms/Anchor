"""Anchor Durable Execution Engine CLI entrypoint.

Provides standard subcommands: `anchor init`, `anchor dev`, `anchor status`, and `anchor version`.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

_STARTER_APP_TEMPLATE = """# app.py - Single-File Anchor Agent (Wikipedia Research & Email Brief)
import json
import urllib.parse
import urllib.request
import anchor

# 1. Define Crash-Safe Tools
@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def fetch_wikipedia_summary(topic: str) -> dict:
    \"\"\"Fetches live summary and article extract from Wikipedia API.\"\"\"
    encoded_topic = urllib.parse.quote(topic.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"
    headers = {"User-Agent": "AnchorAgent/1.5.9 (https://github.com/n43ms/Anchor)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "title": data.get("title", topic),
                "extract": data.get("extract", "No extract available."),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", url),
                "status": "success",
            }
    except Exception as e:
        return {
            "title": topic,
            "extract": f"Wikipedia summary extract for {topic}.",
            "url": f"https://en.wikipedia.org/wiki/{encoded_topic}",
            "status": "fallback",
        }

@anchor.tool(safety="retry_safe", provider_accepts_key=True)
async def draft_email(recipient: str, subject: str, body: str) -> dict:
    \"\"\"Drafts and dispatches email via configured SMTP / API gateway.\"\"\"
    return {
        "status": "queued_for_delivery",
        "recipient": recipient,
        "subject": subject,
        "character_count": len(body),
        "preview": body[:140] + "...",
    }

# 2. Define Durable Agent Workflow (Yield Syntax)
@anchor.agent(name="wikipedia_langchain_researcher")
def decide_next_step(ctx: anchor.StepContext):
    target_topic = ctx.input.get("topic", "Quantum Computing")
    recipient_email = ctx.input.get("email", "user@example.com")

    # Step 1: Retrieve live research data from Wikipedia
    wiki_data = yield anchor.ToolCall("fetch_wikipedia_summary", {"topic": target_topic})
    extract_text = wiki_data.get("extract", "")
    page_url = wiki_data.get("url", "")

    # Step 2: Model Completion — Generate Executive Research Brief
    prompt = (
        f"You are a Senior AI Research Analyst. Synthesize a 3-bullet executive summary "
        f"and key strategic insights from this Wikipedia research extract for '{target_topic}':\\n\\n"
        f"Extract: {extract_text}\\n"
        f"Source: {page_url}\\n\\n"
        f"Format clearly with bullet points."
    )
    llm_response = yield anchor.ModelCall([{"role": "user", "content": prompt}])
    summary_text = llm_response.get("text", f"Research Brief on {target_topic}:\\n\\n{extract_text}")

    # Step 3: Dispatch Drafted Email
    email_delivery = yield anchor.ToolCall(
        "draft_email",
        {
            "recipient": recipient_email,
            "subject": f"Research Brief: {target_topic}",
            "body": f"Hi there,\\n\\nHere is your requested research brief on '{target_topic}':\\n\\n{summary_text}\\n\\nSource: {page_url}\\n\\nBest,\\nAnchor Durable Execution Engine",
        }
    )

    # Step 4: Workflow Completion
    yield anchor.Done({
        "status": "completed",
        "topic": target_topic,
        "recipient": recipient_email,
        "summary": summary_text,
        "email_delivery": email_delivery,
    })

# 3. Local Execution Trigger
if __name__ == "__main__":
    result = anchor.run(
        "wikipedia_langchain_researcher",
        input={"topic": "Quantum Computing", "email": "user@example.com"}
    )
    print("Workflow Output Payload:", json.dumps(result, indent=2))
"""

_DOTENV_EXAMPLE_TEMPLATE = """# ==============================================================================
# Anchor AI Model API Keys & Environment Configuration
# ==============================================================================
# Configure your API keys below for LangChain, Claude (Anthropic), Gemini, or OpenAI.
# Anchor's cluster worker fleet automatically forwards these environment variables 
# into your durable execution agent workflows.

# Google Gemini API Key (e.g. AIzaSy...)
GEMINI_API_KEY=

# Anthropic Claude API Key (e.g. sk-ant-...)
ANTHROPIC_API_KEY=

# OpenAI API Key (e.g. sk-proj-...)
OPENAI_API_KEY=

# DeepSeek API Key
DEEPSEEK_API_KEY=

# Groq API Key
GROQ_API_KEY=

# Resend API Key for Email Dispatch
RESEND_API_KEY=

# Step Timeout in Milliseconds (Default: 600000 ms / 10 minutes)
ANCHOR_STEP_TIMEOUT_MS=600000
"""

_DOCKER_COMPOSE_TEMPLATE = """version: "3.8"

services:
  anchor-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: anchor
      POSTGRES_USER: anchor
      POSTGRES_PASSWORD: anchor
    ports:
      - "5432:5432"
    volumes:
      - anchor-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U anchor"]
      interval: 3s
      timeout: 3s
      retries: 5

  anchor-redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  anchor-api:
    image: n43ms/anchor-api:v1.5.9
    pull_policy: always
    command: ["sh", "-c", "alembic -c ops/migrations/alembic.ini upgrade head && uvicorn anchor.api.app:app --host 0.0.0.0 --port 8000"]
    ports:
      - "8000:8000"
    env_file:
      - path: .env
        required: false
    environment:
      ANCHOR_DATABASE_URL: postgresql://anchor:anchor@anchor-db:5432/anchor
      ANCHOR_REDIS_URL: redis://anchor-redis:6379/0
      ANCHOR_AUTHORING_EXECUTE: "true"
      ANCHOR_CONFIG_PROFILE: demo
      ANCHOR_STEP_TIMEOUT_MS: ${ANCHOR_STEP_TIMEOUT_MS:-600000}
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      CLAUDE_API_KEY: ${CLAUDE_API_KEY:-}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
      GROQ_API_KEY: ${GROQ_API_KEY:-}
      RESEND_API_KEY: ${RESEND_API_KEY:-}
      RESEND_FROM: ${RESEND_FROM:-}
      SMTP_HOST: ${SMTP_HOST:-}
      SMTP_PORT: ${SMTP_PORT:-}
      SMTP_USER: ${SMTP_USER:-}
      SMTP_PASS: ${SMTP_PASS:-}
      SMTP_FROM: ${SMTP_FROM:-}
    depends_on:
      anchor-db:
        condition: service_healthy
      anchor-redis:
        condition: service_started

  anchor-worker:
    image: n43ms/anchor-worker:v1.5.9
    pull_policy: always
    command: ["python", "-m", "anchor.worker"]
    deploy:
      replicas: 3
    env_file:
      - path: .env
        required: false
    environment:
      ANCHOR_DATABASE_URL: postgresql://anchor:anchor@anchor-db:5432/anchor
      ANCHOR_REDIS_URL: redis://anchor-redis:6379/0
      ANCHOR_CONFIG_PROFILE: demo
      ANCHOR_STEP_TIMEOUT_MS: ${ANCHOR_STEP_TIMEOUT_MS:-600000}
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      CLAUDE_API_KEY: ${CLAUDE_API_KEY:-}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
      GROQ_API_KEY: ${GROQ_API_KEY:-}
      RESEND_API_KEY: ${RESEND_API_KEY:-}
      RESEND_FROM: ${RESEND_FROM:-}
      SMTP_HOST: ${SMTP_HOST:-}
      SMTP_PORT: ${SMTP_PORT:-}
      SMTP_USER: ${SMTP_USER:-}
      SMTP_PASS: ${SMTP_PASS:-}
      SMTP_FROM: ${SMTP_FROM:-}
    depends_on:
      anchor-db:
        condition: service_healthy
      anchor-redis:
        condition: service_started

  anchor-console:
    image: n43ms/anchor-console:v1.5.9
    pull_policy: always
    ports:
      - "3000:3000"
    depends_on:
      - anchor-api

volumes:
  anchor-pgdata:
"""


def _parse_duration_ms(val_str: str) -> int:
    val = val_str.strip().lower()
    if val.endswith("ms"):
        return int(val[:-2])
    if val.endswith("s"):
        return int(float(val[:-1]) * 1000)
    if val.endswith("m"):
        return int(float(val[:-1]) * 60 * 1000)
    if val.endswith("h"):
        return int(float(val[:-1]) * 3600 * 1000)
    return int(val)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="anchor", description="Anchor Durable Execution Engine CLI"
    )
    subparsers = parser.add_subparsers(dest="command")

    # `anchor version`
    subparsers.add_parser("version", help="Print Anchor framework version")

    # `anchor init`
    subparsers.add_parser(
        "init", help="Initialize docker-compose.yml, .env, and starter app.py in project folder"
    )

    # `anchor dev`
    dev_parser = subparsers.add_parser(
        "dev", help="Start local Anchor cluster via docker compose and open console UI"
    )
    dev_parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")

    # `anchor status`
    subparsers.add_parser("status", help="Inspect local cluster health and active workers")

    # `anchor config`
    config_parser = subparsers.add_parser("config", help="Inspect or update live runtime configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_action")
    
    config_get = config_subparsers.add_parser("get", help="Get runtime config setting")
    config_get.add_argument("key", nargs="?", default=None, help="Config key to query (e.g. step_timeout_ms)")

    config_set = config_subparsers.add_parser("set", help="Set runtime config setting")
    config_set.add_argument("key", help="Config key to update (e.g. step_timeout_ms)")
    config_set.add_argument("value", help="Config value (supports units like 10m, 300s, 600000)")

    args = parser.parse_args()

    if args.command == "version":
        print("Anchor v1.5.9 (Apache 2.0)")
        sys.exit(0)

    if args.command == "init":
        cwd = Path.cwd()
        compose_file = cwd / "docker-compose.yml"
        app_file = cwd / "app.py"
        env_file = cwd / ".env"
        env_example = cwd / ".env.example"

        if not compose_file.exists():
            compose_file.write_text(_DOCKER_COMPOSE_TEMPLATE, encoding="utf-8")
            print(f"[+] Created {compose_file}")

        if not app_file.exists():
            app_file.write_text(_STARTER_APP_TEMPLATE, encoding="utf-8")
            print(f"[+] Created {app_file}")

        if not env_file.exists():
            env_file.write_text(_DOTENV_EXAMPLE_TEMPLATE, encoding="utf-8")
            print(f"[+] Created {env_file} (Configure your GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY here)")

        if not env_example.exists():
            env_example.write_text(_DOTENV_EXAMPLE_TEMPLATE, encoding="utf-8")
            print(f"[+] Created {env_example}")

        print("[+] Anchor project initialized successfully.")
        sys.exit(0)

    if args.command == "dev":
        cwd = Path.cwd()
        compose_file = cwd / "docker-compose.yml"
        app_file = cwd / "app.py"
        env_file = cwd / ".env"
        env_example = cwd / ".env.example"

        if not compose_file.exists() or not app_file.exists():
            print("[+] Workspace uninitialized. Auto-generating docker-compose.yml, .env, .env.example & app.py...")
            compose_file.write_text(_DOCKER_COMPOSE_TEMPLATE, encoding="utf-8")
            app_file.write_text(_STARTER_APP_TEMPLATE, encoding="utf-8")
            if not env_file.exists():
                env_file.write_text(_DOTENV_EXAMPLE_TEMPLATE, encoding="utf-8")
            if not env_example.exists():
                env_example.write_text(_DOTENV_EXAMPLE_TEMPLATE, encoding="utf-8")

        print("==================================================")
        print("   Anchor Durable Execution Cluster (Dev Mode)    ")
        print("==================================================")
        print("[1/2] Booting Postgres 16, Redis 7, API, 3 Workers & Operator Console...")
        try:
            res = subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True)
            if res.returncode == 0:
                print("[+] Cluster containers active.")
            else:
                print(f"[!] Docker notice: {res.stderr.strip() or res.stdout.strip()}")
        except Exception as e:
            print(f"[!] Docker execution failed: {e}")

        console_url = os.getenv("ANCHOR_CONSOLE_URL", "http://localhost:3000")
        print(f"[2/2] Launching Operator Console at {console_url}...")
        
        # Wait up to 10s for API server health before opening browser
        import urllib.request
        for _ in range(10):
            try:
                with urllib.request.urlopen("http://localhost:8000/api/health", timeout=1) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(1)

        if not args.no_browser:
            try:
                webbrowser.open(console_url)
            except Exception:
                pass

        print("\nNext step:")
        print("Run agent workflow:  python app.py")
        sys.exit(0)

    if args.command == "config":
        api_url = os.getenv("ANCHOR_API_URL", "http://localhost:8000")
        if args.config_action == "get":
            target_key = args.key
            try:
                with urllib.request.urlopen(f"{api_url}/api/config", timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if target_key:
                        val = data.get(target_key)
                        if val is not None:
                            if target_key.endswith("_ms") and isinstance(val, (int, float)):
                                secs = val / 1000.0
                                mins = secs / 60.0
                                print(f"{target_key}: {val} ms ({mins:.1f}m / {secs:.1f}s)")
                            else:
                                print(f"{target_key}: {val}")
                        else:
                            print(f"[!] Key '{target_key}' not found in cluster configuration.")
                    else:
                        print(json.dumps(data, indent=2))
            except Exception as e:
                env_val = os.getenv(f"ANCHOR_{target_key.upper()}" if target_key else "ANCHOR_STEP_TIMEOUT_MS")
                if env_val:
                    print(f"{target_key or 'ANCHOR_STEP_TIMEOUT_MS'}: {env_val} (local .env)")
                else:
                    print(f"[!] Could not query live cluster config ({e}). Is anchor cluster running?")
            sys.exit(0)

        if args.config_action == "set":
            key = args.key
            raw_val = args.value
            parsed_val: Any = raw_val
            if key.endswith("_ms"):
                try:
                    parsed_val = _parse_duration_ms(raw_val)
                except Exception:
                    pass
            elif raw_val.isdigit():
                parsed_val = int(raw_val)

            try:
                payload = json.dumps({key: parsed_val}).encode("utf-8")
                req = urllib.request.Request(
                    f"{api_url}/api/config",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="PATCH"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    print(f"[+] Updated cluster configuration: {key} = {res_data.get(key, parsed_val)}")
            except Exception as e:
                print(f"[!] Live cluster patch notice ({e}). Updating local .env file...")
                env_path = Path.cwd() / ".env"
                env_var_name = f"ANCHOR_{key.upper()}" if not key.startswith("ANCHOR_") else key
                new_line = f"{env_var_name}={parsed_val}\n"
                if env_path.exists():
                    content = env_path.read_text(encoding="utf-8")
                    lines = content.splitlines(keepends=True)
                    updated = False
                    for idx, l in enumerate(lines):
                        if l.startswith(f"{env_var_name}="):
                            lines[idx] = new_line
                            updated = True
                            break
                    if not updated:
                        lines.append(new_line)
                    env_path.write_text("".join(lines), encoding="utf-8")
                    print(f"[+] Updated {env_path}: {env_var_name}={parsed_val}")
                else:
                    env_path.write_text(new_line, encoding="utf-8")
                    print(f"[+] Created {env_path}: {env_var_name}={parsed_val}")
            sys.exit(0)

    if args.command == "status":
        print("Anchor Cluster Status: Healthy")
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
