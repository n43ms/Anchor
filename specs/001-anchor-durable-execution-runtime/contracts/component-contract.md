# UI component contract — `RunDetail` and `RunThread`

**Authority**: `anchor-spec.md` Addendum B (§24) in full, §22 for tokens, §13.2 for the requirements
this must still satisfy; constitution Principle VIII.

**Build what is described here.** Do not substitute a generic timeline library, a Gantt chart, or a
kanban layout. A generic timeline renders this data as a project schedule, which communicates nothing
about ownership handoff — and ownership handoff is the entire point.

## Props

```ts
RunDetail
  run       RunTimeline                  // from GET /api/runs/{id}/timeline
  onKill    (workerId: string) => void   // parent owns the API call and its errors
  now?      Date                         // injectable, for stable snapshots of "41s ago"

RunThread
  segments  TimelineSegment[]
  compact?  boolean = false
  animate?  boolean = true               // parent may force-freeze
```

**No data fetching, no WebSocket, no API call inside either component.** Kill is raised to the parent.
Injecting `now` matters more than it looks: relative timestamps make snapshot tests flap, and this
component will be snapshot-tested.

`ended_at === null` identifies the current owner. That single field drives the kill button's target,
the active-step styling, and which strand segment is still growing — **so it is trusted rather than
re-derived.**

## The primary view — stacked worker bars

- **Header**: `run_47 · refund-agent` as the title; `started 41s ago · 5 steps` beneath; a status
  pill on the right carrying **text and, for `needs_review`/`failed`, an icon** — because
  `completed`-green against `failed`-red measures ΔE 4.1 for a deuteranopic reader.
- **Worker id column**: fixed width, monospace, bold, small, in that worker's identity hue. Fixed
  width so bars align to a common left edge — bars starting at different x positions cannot be
  compared by eye. Ids read `worker-a#3` — label plus incarnation — and **the hue derives from the
  label**, so a worker that restarts mid-run keeps its color while remaining a distinct identity in
  the log.
- **The bar**: rounded track, filled portion is that worker's progress, **fill is the worker's
  identity hue** (`#3987e5` → `#d95926` → `#199e70` on dark, in claim order), unfilled portion is a
  neutral surface step — **never a lighter tint of the worker's hue**, which would read as a
  magnitude ramp and imply the empty portion carried a value.
- **Step labels** below each bar, aligned to roughly where each step falls. The active step's label is
  **bold in primary ink with a trailing ellipsis** — never amber, because text never wears a data
  color.
- **The log**: per segment, monospace, 11px, muted ink for `info`, success for `success`, warning for
  `warning`. Per-segment rather than one block, so every line is attributed to the worker that wrote
  it.
- **The handoff divider**: dashed, with a centered pill reading `{worker_id} lease expired` in danger
  colors. **This is the money moment. It must never be collapsed, hidden behind a toggle, or animated
  away.**
- **The footer**: `{duplicate_side_effects} duplicate side effects · {handoff_count} handoff(s) ·
  {recovery_seconds}s recovery` on the left, `kill {current_worker_id}` on the right in danger
  styling. The duplicate count **leads the line** because it is the guarantee. `recovery_seconds` is
  **suppressed entirely when `handoff_count === 0`** rather than shown as `0.0s`. The kill button
  targets the segment with `ended_at === null` and is disabled with a stated reason when the run is
  terminal.

## The thread view — `RunThread`

Below the bars, same card, thin divider, small muted label `thread view`.

**A thin animated strand, not the bars again.** If it reads as a second progress bar it has failed:
the bars answer *how far*, the strand answers *what happened, in what order, and where ownership
changed*.

- **Geometry**: inline SVG, viewBox ≈ `0 0 620 70`, one continuous wavy path of smooth béziers —
  never straight segments. Stroke 2–2.5px, noticeably thinner than the bars.
- **Color**: **one gold along the whole length** — `#F6C453` on dark, `#7A6300` on light. Not a shade
  per worker. Segment boundaries are marked by the enlarged `handoff` marker, not by a change of
  shade. The measurement that forces this: strand-gold-2 `#B87309` against worker-2 orange
  `#d95926` is **CVD ΔE 1.2** — the same color to a colorblind reader. Two channels asserting the
  same fact in different languages, one of them unreliable, is worse than one channel asserting it
  well.
- **Markers**, and **shape is required, not decorative**:

  | Event | Color | Shape |
  |---|---|---|
  | ordinary step completion | muted `#898781` | circle |
  | a real side effect executed | `#d03b3b` | **square** |
  | reconciled safely / confirmed no duplicate | `#0ca30c` | **ring** |

  The red/green pair remains at CVD ΔE 4.1 and cannot be fixed with color. Circle, square, and ring
  are distinguishable under every form of color blindness, in grayscale, and in a compressed screen
  recording. **Do not ship the markers as three colored circles.**
- **Marker labels**: 11–12px, muted, near each circle — `read`, `check`, `sent once`, `done`. Never
  overlapping the strand. A label that will not fit is **dropped, not clipped**. `sent once` is the
  best two words in the interface: it states the guarantee in the reader's own language, right next to
  the marker proving it.
- **Flow animation**: `stroke-dasharray`/`stroke-dashoffset` via CSS keyframes, 2.5–3.5s per cycle,
  linear, subtle. This is the one permitted exception to the ban on ambient motion, and it earns it
  because the strand represents execution in progress. **It MUST stop when the run reaches a terminal
  state** — a strand that keeps flowing after the run finished is decoration, and it also lies.
- **Reduced motion**: freeze the dashoffset. Colors, markers, and labels all remain.
- **Live extension**: a new step event extends the path in real time rather than snapping.
- **`compact`**: strand only, smaller, for a runs-list row. **It cannot communicate *which* workers
  touched a run — only that a handoff occurred — so it is not a substitute for the runs list's
  owning-worker column. Keep that column.**

## Required mock states

Beyond the happy path, because these are where the component will actually break:

1. Zero handoffs → footer suppression
2. Three or more handoffs → the beyond-three color rule
3. `needs_review` → the third preset's path
4. 40 steps → label collision and the rail fallback
5. **Currently orphaned — no segment has `ended_at === null`.** This is the state the component is in
   during the most important two seconds of the demo. **It is the easiest to forget and the one a
   reviewer will see.**

Reference mock: 5 steps, 2 workers, 1 handoff, 0 duplicate side effects, 3.1s recovery. It must
render meaningfully with no live backend.

## Styling constraints

Dark, dense, monospace-leaning. Tailwind utilities for layout; signature colors as CSS custom
properties. Both token sets defined, no hardcoded colors. No decorative gradients, shadows, or glow
anywhere — the strand's flow is the single intentional exception. All text sentence case. Monospace
only where alignment carries meaning: run ids, worker ids, epochs, keys, timestamps, log lines — not
the prose subtitle, not the step labels.

## Build constraint

**Ask before making structural changes beyond adding these components and their preview page.** New
top-level directories, changes to the repository structure, routing reorganizations, and added
dependencies are discussed first. Adding the component, its sub-component, its mock data, and one
preview route needs no further approval.
