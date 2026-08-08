"""The adversarial test rig: harness, invariants, and the published report.

Deliberately not durable — an API restart mid-run marks the chaos run
`abandoned` rather than resuming it. Making the harness durable would mean
running it on Anchor, which is circular and compromises the independence of
the proof (plan.md Phase 8).
"""
