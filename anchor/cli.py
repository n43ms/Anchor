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

_STARTER_APP_TEMPLATE = """# app.py - Single-File Anchor Agent
import anchor

# 1. Define Tools with explicit crash safety policies
@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def search_academic_papers(topic: str) -> dict:
    \"\"\"Read-only paper search.\"\"\"
    return {"papers": ["Paxos Made Simple", "Raft Consensus"]}

@anchor.tool(safety="unsafe")
async def send_summary_email(to: str, count: int) -> dict:
    \"\"\"Sends live email summary (non-idempotent side effect).\"\"\"
    return {"status": "delivered", "recipient": to}

# 2. Define Agent using line-by-line yield syntax
@anchor.agent(name="my_first_agent")
def decide_next_step(ctx: anchor.StepContext):
    search_data = yield anchor.ToolCall("search_academic_papers", {"topic": ctx.input["topic"]})
    papers = search_data["papers"]

    email_res = yield anchor.ToolCall("send_summary_email", {
        "to": ctx.input["email"],
        "count": len(papers)
    })

    yield anchor.Done({"status": "completed", "email_delivery": email_res})

# 3. Execution Trigger
if __name__ == "__main__":
    result = anchor.run(
        "my_first_agent",
        input={"topic": "Consensus Protocols", "email": "user@stanford.edu"}
    )
    print("Workflow Output Payload:", result)
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
      interval: 2s
      timeout: 5s
      retries: 10

  anchor-redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  anchor-api:
    image: n43ms/anchor-api:v1.5.0
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
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      CLAUDE_API_KEY: ${CLAUDE_API_KEY:-}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
      GROQ_API_KEY: ${GROQ_API_KEY:-}
    depends_on:
      anchor-db:
        condition: service_healthy
      anchor-redis:
        condition: service_started

  anchor-worker:
    image: n43ms/anchor-worker:v1.5.0
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
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      CLAUDE_API_KEY: ${CLAUDE_API_KEY:-}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
      GROQ_API_KEY: ${GROQ_API_KEY:-}
    depends_on:
      anchor-db:
        condition: service_healthy
      anchor-redis:
        condition: service_started

  anchor-console:
    image: n43ms/anchor-console:v1.5.0
    pull_policy: always
    ports:
      - "3000:3000"
    depends_on:
      - anchor-api

volumes:
  anchor-pgdata:
"""


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

    args = parser.parse_args()

    if args.command == "version":
        print("Anchor v1.5.0 (Apache 2.0)")
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

    if args.command == "status":
        print("Anchor Cluster Status: Healthy")
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
