"""Claim, renew, expiry, and fencing-token enforcement.

Ownership of a run is decided by exactly one SQL statement (the claim CTE)
and defended by exactly one database trigger (the epoch write gate). This
package is the Python side of both: it issues the statement and translates
the trigger's rejection into `LeaseFencedError`.
"""
