"""The thin HTTP/WebSocket surface. Nothing here enforces a safety property.

Every router is a translation layer over `core/` and `worker/registry`. The
one deliberate, documented exception is the operator-resolution write, which
uses `core.events.append` directly and is permitted only on a leaseless run
(research.md D-24).
"""
