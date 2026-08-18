# Live-data component states

Constitution Principle VIII: every component that renders live data handles loading, empty, and
error explicitly. Checklist, updated as pages are added:

| Component / page | loading | empty | error |
|---|---|---|---|
| Dashboard | ✅ `loading…` | n/a (always has a fleet) | ✅ `could not reach the api` |
| All runs | ✅ | ✅ `no runs match this filter` | ✅ |
| Run detail | ✅ | n/a | ✅ connection-warning banner |
| Needs review (list) | ✅ | ✅ `nothing needs review` | ✅ |
| Needs review (detail) | ✅ | ✅ `not currently in the uncertainty window` | ✅ per-action |
| Fleet | ✅ (via stale banner) | ✅ `no workers registered` | ✅ per-kill-action |
| Deployments | ✅ (via stale banner) | ✅ `no workers registered` | inherits Fleet's |
| Tool registry | ✅ | ✅ `no tools registered` | ✅ |
| Test run | n/a (form) | n/a | ✅ per-submission |
| Metrics | ✅ | charts render 0-valued series rather than nothing | ✅ |
| Logs | n/a (search-first) | ✅ `no events` | inherits polling |
| Environment | ✅ | n/a | ✅ save error |
| `ModeBanner` | ✅ `connecting to the api…` | n/a | ✅ database-unreachable line |

`RunDetail` and `RunThread` themselves are pure functions of props (component-contract.md) and
perform no fetching, so their loading/error states are the *caller's* responsibility — the table
above is where that responsibility is discharged.
