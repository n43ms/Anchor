"""Log to RunContext reconstruction — a pure fold over ordered events.

No I/O. `reconstruct()` takes an ordered list of events and returns the
context an agent resumes from. Its purity is what makes it testable against
hand-built and captured fixtures without a database.
"""
