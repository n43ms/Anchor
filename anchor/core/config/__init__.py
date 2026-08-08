"""The fifteen settings, the two profiles, and the startup assertion.

No timing, retry, or concurrency constant is legal anywhere else in the
codebase (tests/boundary/test_no_hardcoded_constants.py enforces this). The
assertion in this package is what makes a self-fencing configuration
unstartable rather than merely inadvisable.
"""
