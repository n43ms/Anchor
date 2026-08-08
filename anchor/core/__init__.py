"""Protocol logic: events, leases, journal, replay, determinism, db, config.

Pure and testable wherever possible; the only I/O this package performs is
against PostgreSQL. Every safety property claimed by the constitution is
enforced here or in the database itself — never in `worker/`, `api/`, or
`web/`.
"""
