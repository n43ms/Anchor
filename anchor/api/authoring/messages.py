"""Teaching messages for the six authoring checks (plan.md P9.1, T573).

`contracts/openapi.yaml`'s `ValidationReport.findings[].message` doc: "An
error that teaches the invariant is worth more than the feature that
produced it" (FR-124). Every message here names the line, the mistake, and
the specific replacement — never just the rule.
"""

from __future__ import annotations


def determinism_message(line: int, column: int, banned_name: str, replacement: str) -> str:
    return (
        f"line {line} references {banned_name!r} directly. Agent code must call {replacement} "
        "instead, so the value is journaled and replay returns the same result "
        "(constitution Principle III, the determinism boundary)."
    )


def return_shape_message(line: int, *, empty: bool = False) -> str:
    if empty:
        return (
            f"line {line} returns nothing. decide_next_step must return exactly one of "
            "ToolCall(...), ModelCall(...) or Done(...) on every path — a step that returns "
            "control without an action stalls the worker loop."
        )
    return (
        f"line {line} returns a value that is not a ToolCall(...), ModelCall(...) or Done(...) "
        "call. decide_next_step must return exactly one of the three action types, or the "
        "runtime has nothing it can act on."
    )


def module_state_message(line: int, name: str) -> str:
    return (
        f"line {line} mutates module-level state ({name!r}) from inside a function. State held "
        "outside ctx does not survive a handoff — the runtime reconstructs ctx fresh from the "
        f"journal on every attempt, but {name!r} is not part of that journal and will not be "
        "there on the next worker, or the next replay."
    )


def unregistered_tool_message(line: int, tool_name: str) -> str:
    return (
        f"line {line} calls ToolCall({tool_name!r}, ...), but {tool_name!r} is not in the live "
        "tool registry. This fails now, in the editor, rather than at step 3 of a live run — "
        "register the tool first, or check the spelling against GET /api/tools."
    )


def missing_safety_message(line: int, tool_name: str) -> str:
    return (
        f"line {line} declares tool {tool_name!r} with @anchor.tool(...) but no safety= "
        "argument. Every tool must declare 'retry_safe', 'reconcilable' or 'unsafe' explicitly "
        "— there is no default, because guessing a safety category is exactly the kind of "
        "guess this runtime refuses to make on your behalf."
    )


def self_recursion_message(line: int, function_name: str) -> str:
    return (
        f"line {line}: every return path in {function_name!r} calls {function_name!r} again, "
        "with no ToolCall, ModelCall or Done reachable. This step can only return itself, which "
        "is an infinite run — decide_next_step must have a reachable path to an action."
    )
