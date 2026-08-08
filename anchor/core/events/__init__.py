"""Event types, payload models, the single append path, and sequence handling.

`anchor.core.events.append` is the only code in the system permitted to
`INSERT INTO run_events` (tests/boundary/test_single_append_path.py enforces
this). Every writer — worker, API, chaos harness, operator resolution — goes
through it.
"""
