"""Idempotency keys, canonical serialization, and uncertainty policies.

The two-phase journal (`TOOL_INTENT` before invocation, `TOOL_RESULT` after)
lives here, keyed by a SHA-256 hash over canonical JSON. This package is what
makes "no tool executes twice" a property of the database rather than a
convention of the caller.
"""
