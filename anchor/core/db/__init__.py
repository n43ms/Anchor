"""asyncpg pool, explicit SQL, and SQLSTATE-to-typed-error mapping.

No ORM on the hot path. Every statement is a named module-level constant
beside the function that issues it, so a query can be read and reasoned
about without indirection.
"""
