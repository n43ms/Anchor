"""Self-registration, heartbeat telemetry, and the kill subscriber.

Worker identity is `{label}#{incarnation}` and is never reused across a
process restart (research.md D-42) — see `identity.py`.
"""
