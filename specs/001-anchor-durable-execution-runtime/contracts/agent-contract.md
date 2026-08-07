# The agent contract — `StepContext` and `decide_next_step`

**Authority**: `anchor-spec.md` §25.3 (the determinism API), §26.3–§26.4 (the developer path and the
one constraint that must be taught), §3.2 (the determinism boundary); constitution Principle III.

This is the entire integration surface a developer writes against. **Everything else is
`docker compose`.**

## The function

```python
def decide_next_step(ctx: StepContext) -> ToolCall | ModelCall | Done: ...
```

It receives the reconstructed run state and returns **exactly one action**. It is then called again.

### The one constraint that must be taught, not discovered

> **The agent function returns one action and then returns control. It does not loop, and it does not
> hold state in variables across steps.** All state is read from `ctx`, which the runtime
> reconstructs from the log on every attempt.

An agent that loops internally is opaque to the runtime, and a crash inside that loop has nothing to
resume from. Yielding control at each step is what converts a fragile in-memory process into a
resumable one. The loop is expressed as a function of journaled history:

```python
def decide_next_step(ctx):
    if not ctx.has_result("search_professors"):
        return ToolCall("search_professors", {"field": ctx.input["field"]})

    professors = ctx.result_of("search_professors")
    done = ctx.completed_tool_args("send_email")        # from the log
    remaining = [p for p in professors if p["email"] not in done]

    if not remaining:
        return Done({"contacted": len(done)})

    p = remaining[0]
    if not ctx.has_result("fetch_page", {"url": p["url"]}):
        return ToolCall("fetch_page", {"url": p["url"]})

    return ToolCall("send_email", {"to": p["email"], "body": ctx.result_of("draft")})
```

The loop's progress lives in the journal, so "which professors have already been emailed" survives any
number of crashes, on any worker, without the agent tracking it.

## The `StepContext` surface

Agent code may reach the outside world **only** through this object.

| Call | Journaled as | On replay |
|---|---|---|
| `ctx.now()` | `NONDET_RECORDED` kind `time` | returns the recorded timestamp |
| `ctx.random()` | `NONDET_RECORDED` kind `random` | returns the recorded value |
| `ctx.new_id()` | `NONDET_RECORDED` kind `id` | returns the recorded identifier |
| `ctx.call_model(...)` | `LLM_CALLED` | returns the recorded completion; **no provider call** |
| `ctx.call_tool(name, args)` | `TOOL_INTENT` → `TOOL_RESULT` | returns the recorded result, or applies the tool's uncertainty policy |

`ctx.new_id()` is named separately from `ctx.random()` **deliberately**: a generated identifier that
differs across replay is the specific failure that defeats deduplication, so the call that produces
one is individually visible in the log and individually greppable in agent code.

### Read-only accessors over journaled history

| Accessor | Returns |
|---|---|
| `ctx.input` | The submission payload |
| `ctx.step_index` | The index of the step about to execute |
| `ctx.messages` | Accumulated conversation state, rebuilt from the log |
| `ctx.has_result(tool, args=None)` | Whether a completed result exists for that tool, optionally for those exact arguments |
| `ctx.result_of(tool, args=None)` | The recorded result, or raises if absent |
| `ctx.completed_tool_args(tool)` | Every argument set for which that tool has a recorded result — the mechanism that makes a resumable loop expressible |
| `ctx.attempt` | Attempt number for the current step |
| `ctx.is_replaying` | True while the fold over the log is still catching up. **Informational only** — branching on it makes replay non-deterministic and the validator flags it. |

### Actions

```python
ToolCall(name: str, args: dict)      # args must be JSON-native; see the canonicalization rules
ModelCall(messages: list, model: str | None = None)
Done(output: dict)
```

## Rules the runtime enforces

1. **No direct clock, randomness, or identifier generation.** A test walks the AST of every module
   under `anchor/runtime/agents/` and fails on any reference to `datetime`, `time`, `random`, or
   `uuid`. The authoring validator runs the same check interactively (D-27).
2. **Arguments must be JSON-native.** Object, array, string, integer, float, boolean, null. A `set`,
   a `datetime`, a `Decimal`, `NaN`, or `±Infinity` raises at call time with the path to the
   offending value — because the alternative is an idempotency key that varies across replay, which
   fails silently and defeats deduplication (D-13). The key itself is
   `sha256(canonical_json([run_id, step_index, action_name, args]))` — hashed over a canonical
   **array**, never a delimited string, so framing is unambiguous by construction rather than by
   argument about which characters are legal in a tool name (D-41).
3. **One side effect per step.** A step contains at most one side-effecting tool call, which is what
   makes `hash(run_id, step_index, action, args)` unique without a within-step counter (D-26).
4. **No module-level mutable state.** State held outside `ctx` does not survive a handoff and is the
   most likely authoring mistake.
5. **Return one of the three action types.** Anything else stalls the worker loop and is rejected by
   the validator.

## Registration

```python
agent_registry.register("my_agent", my_agent.decide_next_step)
```

### The pre-registration checklist

**Authority**: `anchor-spec.md` §35. Four lines, and each one names a mistake that this project's own
construction surfaced.

```
[ ] Every branch reads state from ctx, never a variable held across calls
[ ] Every loop filters using ctx.completed_tool_args(...), not a counter
[ ] There is a reachable Done(...) branch once the loop's work is exhausted
[ ] Every ctx.call_tool(...) checks ctx.has_result(...) first
```

The checklist restates rules 1–5 above in the order a developer actually violates them, and it is
written down here rather than deferred with the rest of Addendum F because it is **documentation of an
existing contract, not new product surface** — it costs four lines and adds nothing to the build.

**None of the four is statically checkable, and that is the point.** Rules 1 and 4 have partial static
proxies in the phase-9 validator (module-level mutable state; unregistered tool names). Rules 2 and 3
are statements about *business logic* — that a loop's filter is the right filter, that a terminal
branch is reachable for the inputs that will actually arrive — and no static analysis can verify intent
it was never told. See [research.md](../research.md) D-59 for why that ceiling is stated in the product
rather than only here.

## Crash behaviour of each `ctx` call

Stated because the constitution requires every I/O boundary to have one.

- `ctx.now()` / `ctx.random()` / `ctx.new_id()`: no external effect, so a crash before the journal
  write is safely re-derivable on the next attempt — **nothing in the world observed the discarded
  value**. This is exactly why the three are **buffered per step and written as one
  `NONDET_RECORDED` event in the same transaction as that step's `TOOL_INTENT`** (research.md D-47):
  durability is required not at the moment of the call but before anything depending on the value
  leaves the process, and the only such thing is a side effect. When `ctx.new_id()` feeds an
  idempotency key, the key's inputs and the intent therefore commit atomically — there is no
  interleaving in which an effect exists whose inputs are unrecorded. Values are still returned to
  agent code in call order and replayed in call order, by `call_ordinal`.
- `ctx.call_model(...)`: a crash after the provider call but before the journal write costs the call
  again on the next attempt. Money, not correctness. Stubbed by default, so normally free.
- `ctx.call_tool(...)`: a crash between the committed `TOOL_INTENT` and `TOOL_RESULT` is the
  uncertainty window, resolved by the tool's declared policy. **This is the only `ctx` call whose
  crash behaviour is a correctness question**, which is why it is the one wrapped in two phases.
