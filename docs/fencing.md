# Fencing: the zombie timeline

This is the phase-4 narrative — the zombie timeline, why the epoch must be
monotonic, and why the check must live in the database — required by T221
and, per constitution Principle II's Definition of Done, whiteboardable cold
without notes.

## The zombie timeline

1. **Worker A claims a run.** `core.leases.claim.claim_one` — one
   transaction — increments `runs.epoch` from 0 to 1, sets
   `owner_worker_id = 'worker-A'`, extends `lease_expires_at`, and appends
   `RUN_CLAIMED` at epoch 1. Worker A now believes, correctly, that it is
   the only writer for this run at epoch 1.
2. **Worker A stalls.** Its process, or just its event loop, stops making
   progress — a GC pause, a synchronous blocking call, a genuine crash. It
   does not matter which: from the outside, all three look identical. The
   renewer, sharing A's event loop, cannot run either — there is no
   separate thread or watchdog keeping it alive, deliberately (Principle
   VII).
3. **The lease expires.** `lease_expires_at` was evaluated against
   PostgreSQL's clock at the last successful renewal, not worker A's clock
   (`I5`). Once `now() > lease_expires_at` in the database, the run becomes
   an eligible reclaim candidate to anyone polling.
4. **Worker B reclaims it.** The same `claim_one` statement, running the
   `status = 'running' AND lease_expires_at < now()` branch, locks the row
   with `FOR UPDATE SKIP LOCKED`, increments `epoch` to 2, reassigns
   ownership, and appends `RUN_CLAIMED` (`reason:
   reclaimed_after_lease_expiry`) followed, in the same transaction, by
   `WORKER_FENCED` naming worker A, epoch 1, and epoch 2
   (`core.leases.fencing`). Worker B is now the only legitimate writer at
   epoch 2. Nothing about this step required worker A to be told, or even
   to actually be dead — only that its lease had lapsed.
5. **Worker A wakes up.** It does not know any of the above happened. It
   still holds epoch 1 in memory and, unaware, either:
   - **attempts to renew:** `core.leases.renew.renew_once`'s
     `WHERE id = $1 AND epoch = $2` guard now matches zero rows (the row's
     epoch is 2), so it raises `LeaseFencedError` locally — no write
     happens, because an `UPDATE` matching nothing is not a write, it is a
     no-op; or
   - **attempts to append an event** (e.g. `TOOL_INTENT` for its next
     step): the `run_events_epoch_gate` trigger compares `NEW.epoch = 1`
     against the row's current `epoch = 2` **inside the same transaction as
     the insert**, finds them unequal, and raises `AN001` — the insert
     never commits.
6. **Worker A withdraws.** Whichever way it discovered the mismatch,
   `LeaseFencedError` propagates to `worker.loop.run_claimed`'s
   `except* LeaseFencedError`, which discards worker A's in-memory state,
   writes nothing further through this run — not even an event describing
   what went wrong — and returns worker A to the idle poll loop. It does
   not retry. The incident is recorded only in worker A's own structured
   process log and the process-local fencing counter
   (`core.leases.fencing.record_local_fencing`), never in the run's log,
   because worker A no longer has any standing to write there.

At every point after step 4, the run's log contains a complete, self-
consistent account of what actually happened, written entirely by workers
who were entitled to write it. Worker A's belief that it still owned the run
never touches that log at all.

## Why the epoch must be monotonic

The epoch is the run's fencing token: a number that only ever increases,
assigned exactly once per successful claim, and checked on every single
write. Monotonicity is what turns "who owns this run" into a total order
that every writer — even one that has not heard from anyone else in
minutes — can check unilaterally, with no coordination beyond the one row
it is trying to write to.

If the epoch could decrement or be reused, a stale worker's belief that it
holds epoch N would sometimes be **correct again later** (if the epoch
wrapped or was reset), and a check that compares "my epoch" to "the current
epoch" could pass by coincidence rather than by genuine continued ownership.
Monotonicity is what makes "my epoch equals the current epoch" mean "I am
still the writer who most recently won a claim," full stop, with no second
case to reason about.

## Why the check must live in the database

Two workers who disagree about who owns a run cannot resolve that
disagreement by talking to each other — worker A, stalled, cannot be
reached, which is the entire premise of the scenario. The only thing both
workers can reach is PostgreSQL, and the only way a check "is my write
allowed" can be trustworthy is if it is evaluated **inside the same
transaction as the write it is guarding**, against a value that is itself
only ever changed inside a transaction that also holds the row lock
(`claim_one`).

An application-level check — read the epoch, compare it in Python, then
issue the write — has a window between the read and the write in which
another transaction can commit a claim. A `BEFORE INSERT` trigger that
takes its own lock on the run row (`SELECT epoch ... FOR UPDATE`) has no
such window, because there is no gap between "check" and "write" for another
transaction to land in — they are the same statement, in the same
transaction, serialized by the same row lock. Enforcing this anywhere
outside PostgreSQL would mean the property holds only as long as every
caller remembers to check first — which is precisely the kind of guarantee
concurrency defeats given enough load and enough time.
