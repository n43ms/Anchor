"""Demo agents: demo_minimal, demo_short, demo_long, demo_unsafe.

Every module in this package is walked by the AST determinism checker
(anchor.core.determinism.ast_check) and MUST NOT reference `datetime`,
`time`, `random`, or `uuid` directly.
"""
