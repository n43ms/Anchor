# The tool contract — registration and safety declarations

**Authority**: `anchor-spec.md` §3.3 (idempotency and the uncertainty window), §7 (`tool_registry`),
§26.3 step 4; constitution Principle IV.

A tool is a plain function. **Anchor does not care what is inside it.** What Anchor requires is a
declaration of what happens if it is executed twice — and that declaration is
**the only Anchor-specific concept a developer has to learn.**

## Registration

```python
register_tool(
    name="send_email",
    fn=send_email,
    safety="unsafe",                    # retry_safe | reconcilable | unsafe
    reconcile_fn=None,                  # required when safety="reconcilable"
    naturally_idempotent=False,
    provider_accepts_key=False,
    description="Sends a message to a recipient.",
)
```

Registration **fails** when:

- `safety` is absent or not one of the three categories — the decision must be made deliberately, and
  there is no default to fall back to
- `safety="reconcilable"` and `reconcile_fn` is absent
- `safety="retry_safe"` and neither `naturally_idempotent` nor `provider_accepts_key` is true — a
  tool cannot be declared safe to re-execute without naming *why* it is safe

The last two rules are also table `CHECK` constraints (see
[data-model.md](../data-model.md) §4), so a row inserted by any path still satisfies them. A registry
row that claims a category it cannot support is exactly the failure that would turn `I1` into a wish.

**Declarations are content-hashed** (research.md D-46). `register_tool` hashes the five
safety-relevant fields and upserts at worker startup. If an existing row carries a **different** hash,
the conflict is recorded with both `code_version`s and **that tool is refused for execution
fleet-wide** — that tool only, not the worker and not the fleet — until an operator resolves it.

The reason is specific rather than defensive: the registry is a table and the declaration is code, so
during a rolling deploy the two can disagree about *the policy that resolves the uncertainty window*.
A tool reclassified from `unsafe` to `retry_safe` between builds means a crash inside that window
**halts for review on one worker and re-executes on another**, in the same fleet,
non-deterministically. `I8` says uncertainty is resolved by the tool's declared policy; if "the
declared policy" is ambiguous, `I8` has no content.

## The three categories

| Category | Meaning | Behaviour on entering the uncertainty window |
|---|---|---|
| `retry_safe` | Naturally idempotent, or the provider deduplicates on a passed-through key | Re-execute, **passing the idempotency key through** so the provider deduplicates on their side. This is how payment APIs work and is the strongest option available. |
| `reconcilable` | You can ask whether the effect occurred | Run `reconcile_fn` and branch on the answer |
| `unsafe` | Neither of the above applies | Mark the run `needs_review`, halt, surface the specific ambiguous call in the console. **Do not guess.** |

## `reconcile_fn`

```python
def reconcile(args: dict, idempotency_key: str) -> ReconcileResult: ...
```

Returns `Executed(result)`, `NotExecuted()`, or `Unknown()`. **`Unknown()` escalates to
`needs_review`** — a reconciliation function that cannot determine the answer must say so rather than
default to either branch. That escalation path is required, because a reconciler that guesses is
worse than no reconciler: it converts an honest halt into a silent double execution.

`reconcile_fn` is called with the same canonical arguments the intent recorded, so it can locate the
effect by the same key the tool would have used.

## The two-phase journal, from the tool's point of view

```
append TOOL_INTENT   (idempotency_key, canonical args, safety)   ← committed BEFORE invocation
invoke the tool      (bounded by step_timeout, always)
append TOOL_RESULT   (same key, result)
```

The intent is committed before invocation. That ordering is the whole mechanism: it means a crash can
leave the system *uncertain*, but never leaves it *unaware* that something might have happened. The
inverse ordering — execute, then record — would make an unrecorded side effect possible, which the
constitution forbids outright.

## The demo tool set

Fake, but named after real consequential actions, because `send_email` makes the double-execution
risk intuitive without a word of explanation. At least one tool in each category, so all three
policies are reachable from the interface (§21.5).

| Tool | Safety | Why |
|---|---|---|
| `web_search` | `retry_safe` | Read-only; naturally idempotent |
| `fetch_page` | `retry_safe` | Read-only |
| `create_ticket` | `reconcilable` | A ticket with a given external key can be queried |
| `send_email` | `unsafe` | Cannot be un-sent and cannot be queried. **The `needs_review` path.** |
| `charge_card` | `retry_safe` | Only because the provider accepts an idempotency key — the declaration names the reason |

Every one writes a `demo_effects` row, and that table's `UNIQUE (idempotency_key)` constraint means a
double execution is **rejected by the database** rather than merely counted. The row count is the
ground truth a reviewer can check without trusting the log.
