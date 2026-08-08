"""The journaled clock, randomness, id generation, and the StepContext surface.

Every crossing of the determinism boundary — `ctx.now()`, `ctx.random()`,
`ctx.new_id()`, `ctx.call_model()`, `ctx.call_tool()` — is implemented here.
Agent code reaches the outside world only through this package's
`StepContext`.
"""
