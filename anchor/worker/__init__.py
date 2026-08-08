"""The worker process: execution loop, renewer, admission, retry, registry.

`worker/` follows the protocol defined in `core/`; it does not define one.
Nothing here enforces a safety property directly — every guarantee it relies
on is a call into `core/` or a database constraint.
"""
