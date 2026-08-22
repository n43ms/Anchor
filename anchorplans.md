# Anchor Developer Experience (DX) & SDK Roadmap (`anchorplans.md`)

This document captures the design, architecture, and implementation blueprint for the **Anchor Ergonomic Developer SDK and DX Layer** (scheduled for **Phase 9: The Authoring Surface**).

---

## 1. Vision & Core Philosophy

Anchor separates into two clean, decoupled layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      1. ANCHOR DEVELOPER SDK (DX)                      │
│   • @anchor.tool(safety="...") decorator with type inference           │
│   • anchor.from_langchain(...) / anchor.from_openai(...) adapters      │
│   • Simple anchor dev CLI for 1-command local startup                  │
│   • Authoring Playground in Operator Console (/authoring)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Compiles down to standard
┌───────────────────────────────────▼────────────────────────────────────┐
│                    2. ANCHOR DURABLE ENGINE (CORE)                     │
│   • decide_next_step(ctx) pure state-machine contract                  │
│   • PostgreSQL Monotonic Epoch Gates & Append-Only Event Log           │
│   • Two-Phase Journal (Zero Duplicate Side Effects)                   │
│   • Real-Time 60fps Visual Execution Console & /needs-review Queue     │
└────────────────────────────────────────────────────────────────────────┘
```

> **The Core Rule**: The developer interface is radically simplified, while 100% of Anchor’s underlying mathematical durability guarantees (`I1`–`I8`), database triggers, and crash recovery mechanisms remain untouched and fully enforced.

---

## 2. The 3 Pillars of the New Developer Experience

### Pillar 1: Zero-Boilerplate Decorators (`@anchor.tool`)
Eliminates manual dictionary registration and parameter parsing:

```python
import anchor

@anchor.tool(safety="retry_safe")
async def scrape_webpage(url: str) -> dict[str, str]:
    """Fetches text from a URL."""
    return {"content": "..."}

@anchor.tool(safety="unsafe")
async def send_email(to: str, subject: str, body: str) -> dict[str, str]:
    """Sends a live email."""
    return {"status": "sent"}
```

- Automatically extracts tool parameter schemas from Python type hints and docstrings.
- Enforces the safety declaration (`retry_safe`, `reconcilable`, `unsafe`) at declaration time.
- Registers the tool directly with Anchor's Two-Phase Journal.

---

### Pillar 2: Native Framework Adapters (`anchor.from_langchain`, `anchor.from_openai`)
Eliminates manual 15-line response parsing loops by translating LangChain and OpenAI tool-calling outputs directly into Anchor's `ToolCall` and `Done` primitives:

```python
from langchain_openai import ChatOpenAI
import anchor

llm = ChatOpenAI(model="gpt-4o-mini")

# 1-line LangChain agent registration
agent = anchor.from_langchain(
    name="research_assistant",
    llm=llm,
    tools=[scrape_webpage, send_email],
    expected_steps=4
)
```

**How it works under the hood (§26.5):**
1. On each step, Anchor feeds reconstructed `ctx.messages` into `llm.invoke()`.
2. If the LLM returns `tool_calls`, the adapter yields an Anchor `ToolCall`.
3. If the LLM finishes, the adapter yields an Anchor `Done`.
4. Anchor executes the tools with PostgreSQL durability and zero duplicate side effects.

---

### Pillar 3: Single-Command Local Dev (`anchor dev`)
Eliminates the friction of running 3–4 separate terminal windows:

```bash
anchor dev --agents my_agent.py
```

- Starts ephemeral local storage (or connects to local Docker Compose).
- Boots the API server and Worker fleet in the background.
- Automatically opens **`http://localhost:5173`** in the default browser.

---

## 3. End-to-End Consumer Code Examples

### A. Pure Python (No Frameworks)
```python
import anchor

@anchor.tool(safety="retry_safe")
async def lookup_company(name: str) -> dict:
    return {"name": name, "industry": "Tech"}

@anchor.agent(name="company_analyst", expected_steps=3)
def decide_next_step(ctx: anchor.StepContext) -> anchor.Action:
    if ctx.step_index == 0:
        return anchor.ToolCall("lookup_company", {"name": ctx.input["company"]})
    return anchor.Done({"data": ctx.tool_results.get(0)})
```

---

### B. LangChain Agent with Anchor Durability
```python
import os
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import anchor

@tool
def calculate_tax(amount: float) -> float:
    """Calculates tax on an amount."""
    return amount * 0.15

# Wrap tool with Anchor safety
anchor_tax_tool = anchor.wrap_tool(calculate_tax, safety="retry_safe")

llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

agent = anchor.from_langchain(
    name="tax_agent",
    llm=llm,
    tools=[anchor_tax_tool],
    expected_steps=3
)
```

---

## 4. Constitution & Spec Alignment

| Spec Section | Clause | Alignment Verification |
|---|---|---|
| **§25.3 & Principle III** | Determinism Contract (`StepContext`) | **Fully Preserved**: All adapters return `ToolCall \| ModelCall \| Done` and read state strictly from `ctx`. |
| **§3.3 & Principle IV** | Tool Safety Categories | **Fully Preserved**: Every `@anchor.tool` requires explicit safety declaration (`retry_safe`, `reconcilable`, `unsafe`). |
| **§26.5** | Framework Adapters | **Direct Implementation**: Realizes the exact 50-line state rehydration adapter pattern specified in §26.5. |
| **§27** | Phase 9 Authoring Surface | **Scheduled in Phase 9**: Placed in the build order after Phase 8 (Chaos & Verification). |

---

## 5. Phase 9 Implementation Checklist

- [ ] **P9.1 SDK Core**: Create `anchor/sdk/decorators.py` for `@anchor.tool` and `@anchor.agent`.
- [ ] **P9.2 LangChain Adapter**: Create `anchor/sdk/adapters/langchain.py` with `from_langchain()`.
- [ ] **P9.3 OpenAI Adapter**: Create `anchor/sdk/adapters/openai.py` with `from_openai()`.
- [ ] **P9.4 Top-Level Exports**: Expose `anchor.tool`, `anchor.agent`, `anchor.from_langchain` in `anchor/__init__.py`.
- [ ] **P9.5 CLI Tooling**: Add `anchor dev` and `anchor worker` command line runner in `pyproject.toml`.
- [ ] **P9.6 In-Console Editor**: Mount **Tools → Authoring** (`/authoring`) in the React Console with Monaco Editor & live AST determinism validator.
- [ ] **P9.7 Verification Tests**: Add end-to-end unit and failure tests in `tests/contract/test_sdk_adapters.py`.
