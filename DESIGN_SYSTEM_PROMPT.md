# Anchor Frontend Design System & Aesthetic Specification (Master Reusable Prompt)

> **Instructions for AI Assistant / Designer**: Use this document as the single source of truth for all frontend architecture, visual aesthetics, component constructions, mathematical animations, and styling nitpicks. You must adhere strictly to every parameter, token ratio, opacity, and layout rule specified below. Never downgrade to generic flat UI, default Tailwind palettes, or generic dashboard templates.

---

## 1. Visual Paradigm: Hyper-Modern Specular Dark Glassmorphism

The design language combines **ultra-deep obsidian surfaces**, **frosted specular glass panels**, **monochromatic structural frameworks**, and **luminous high-precision neon telemetry** (Deep Indigo, Rich Warm Amber, Sun Gold, and Mint Emerald).

### Surface & Border Rules
1. **Backdrop Surface**: Deepest pure obsidian (`#050505` / `bg-[#050505]` / `bg-surface-page`).
2. **Glassmorphic Cards & Panels**:
   - Background: `bg-black/40` with `backdrop-blur-2xl`.
   - Border: Hairline specular border `border border-white/[0.08]`.
   - Border Radius: Large organic rounded corners (`rounded-2xl` for cards, `rounded-xl` for inner widgets).
   - Hover States: Micro-specular sheen: `transition-all duration-200 hover:border-white/[0.20] hover:bg-white/[0.02]`.
   - Inner Containers: Nested panels use `border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl`.
3. **Dividers & Gridlines**: Hairline translucent borders (`border-white/[0.06]` or `border-white/[0.08]`). Never use thick or opaque solid gray dividers.

---

## 2. Color Palette & Lighting Channels

All telemetry channels have strict semantic assignments and glowing ambient lighting filters:

```
┌─────────────────┬──────────────────────┬────────────────────────────────────────────────────────┐
│ Channel         │ Hex / RGB            │ Semantic Assignment & Ambient Lighting                 │
├─────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Sun Gold        │ #f6c453 / #fef08a    │ Primary Golden Ribbon, Live Execution Spine            │
│                 │                      │ Glow: feDropShadow stdDev=3.5 floodColor=#fef08a       │
├─────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Deep Indigo     │ #6366f1 / #818cf8    │ Model Calls, Timeline Tracks, Worker Progress Fill     │
│                 │                      │ Glow: feDropShadow stdDev=3.0 floodColor=#6366f1       │
├─────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Warm Amber      │ #d97706 / #f59e0b    │ External Tool Calls, Stale Alerts                      │
│                 │                      │ Glow: feDropShadow stdDev=3.0 floodColor=#d97706       │
├─────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Mint Emerald    │ #34d399 / #059669    │ Worker Handoffs, Reconciled Steps, Live Cluster Uptime │
│                 │                      │ Glow: feDropShadow stdDev=2.0 floodColor=#059669       │
├─────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Rose Crimson    │ #f43f5e / #e11d48    │ Worker Kill Triggers, Fencing Collision Alerts         │
├─────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ Muted Slate     │ #a1a1aa / #71717a    │ Secondary telemetry labels, inactive filters           │
└─────────────────┴──────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Typography Hierarchy & Dual-Family Discipline

Only two typographic families are permitted across the entire application:

1. **Aesthetic UI Proportional Font (`--font-ui`)**:
   - Family: `"Geist", -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif`
   - Usage: Page headers, KPI values, card titles, and **Thread Numerical Legend Badges**.
   - Features: `figures-proportional` for hero counters, `font-extrabold` / `font-bold` for titles.
2. **Precision Monospace Data Font (`--font-data`)**:
   - Family: `"Geist Mono", "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace`
   - Usage: Machine identifiers (`worker-1#2`, `run_019`), execution logs, step metadata, elapsed durations, and tabular table alignments.
   - Features: `figures-tabular` for vertically aligned numbers.

---

## 4. 2D Runtime Execution Thread (`RunThread.tsx`)

The centerpiece of the operator console is the continuous, flowing 2D multi-strand golden ribbon visualizing live durable execution.

### Calibrated Strand Architecture
- **Strand Bundle Count**: 15 continuous Bézier paths (1 Primary Main Strand + 14 Background Strands).
- **Main Golden Strand (Calibrated 78% Opacity)**:
  ```tsx
  {/* Underglow Bloom */}
  <path d={mainPath} fill="none" stroke="var(--strand-gold)" strokeWidth={2.8} strokeOpacity={0.22} strokeLinecap="round" />
  
  {/* Primary Main Light Golden Spine (78% translucent) */}
  <path className="strand-path" d={mainPath} fill="none" stroke="var(--strand-gold)" strokeWidth={1.35} strokeOpacity={0.78} strokeLinecap="round" />
  
  {/* Incandescent Core Highlight (78% translucent) */}
  <path d={mainPath} fill="none" stroke="rgb(254, 240, 138)" strokeWidth={0.75} strokeOpacity={0.78} strokeLinecap="round" />
  ```
- **14 Background Silk Strands (Delicate, Highly Translucent Paths)**: Rendered with subtle amber/gold shifts and delicate opacities (`0.10` to `0.26`) with `mix-blend-mode: plus-lighter`.
- **Edge Fade Mask**: Linear gradient SVG alpha mask fading to `0%` opacity at horizontal edges.
- **Wave Motion**: Smooth 60fps continuous requestAnimationFrame loop driving traveling sine/cosine wave harmonics `(u = (x / W) * 9.5 - t * 0.75)`.

---

## 5. Thread Marker Geometry & Floating Numerical Legend (`ThreadMarkers.tsx`)

### Geometric Marker Nodes (Minimal & Ambient)
All nested boxes, concentric outlines, and double boundaries are strictly forbidden. Markers must be pure geometric primitives:
- **Tool Calls**: Warm Amber Square (`width={8} height={8} rx={1.5} fill="#d97706"`) with `#glow-amber`.
- **Model Calls**: Deep Indigo Circle (`r={4} fill="#6366f1"`) with `#glow-indigo`.
- **Handoffs**: Warm Amber Circle Beacon (`r={5.5} fill="#d97706"`) with `#glow-amber`.
- **Replayed / Reconciled Steps**: Clean Mint Ring (`r={4} fill="none" stroke="#34d399" strokeWidth={1.8}`).
- **Hover Stability**: Zero hover scaling transforms or jumpy resizing (`.strand-marker-node` has no hover scale).

### Floating Numbers as the Legend Key (No Enclosing Circle)
- No rectangular text boxes or heavy name tags on the ribbon.
- Pure numerical digits (`1`, `2`, `3`...) float cleanly above the marker nodes connected by a hairline vertical connector tick (`strokeWidth={0.75} strokeOpacity={0.65}`).
- **Tool Calls & Handoffs**: Numbers and icons use rich saturated warm amber color (`#f59e0b` text with `#d97706` radial glow halo) matching the tool call squares.
- **Model Calls**: Numbers use deep indigo/ice-blue color (`#e0e7ff`).
- **No Circle Boundary**: The number text floats freely without a bounding border.
- **Font**: Rendered in the aesthetic UI font (`.strand-number-text text-[10px] font-extrabold`).
- **Radial Glow Halo**: A soft `<radialGradient>` (40% core opacity fading to 0%) sits directly behind each number.
- **Text Drop-Glow**: Filtered with subtle `feDropShadow stdDeviation="1.8"`.
- **Synchronized Call Names**: Below the worker bar, each full step call name pill displays a matching colored numerical badge (`[1]`, `[2]`, `[3]`) acting as the interactive legend key.

---

## 6. TimelineTrack & Worker Progress Bar Calibration

### TimelineTrack Segments
- **Block Fill**: Solid flat 20% Indigo (`bg-indigo-500/20`), **strictly NO gradient**.
- **Block Border**: Refined crisp hairline `border border-indigo-400/25`.
- **Block Glow**: Micro ambient shadow `shadow-[0_0_8px_rgba(99,102,241,0.15)]`.
- **Replayed Steps on Timeline**: Rendered with dashed border (`borderLeft: 1px dashed rgba(165, 180, 252, 0.5)`) and 45% opacity (`opacity-[0.45]`).
- **Fencing Collision Marker**: Understated floating badge with a delicate dashed hairline divider (`border-l border-dashed border-rose-400/40`), completely non-overlapping with worker blocks.

### WorkerBar (Worker Segment Progress)
- **Container**: `h-2.5 rounded-full border border-indigo-500/25 bg-black/70 p-[1px] shadow-inner`.
- **Progress Fill**: Calibrated to **75% opacity** (`opacity-[0.75]`).
- **Fill Gradient**: `bg-gradient-to-r from-indigo-600 via-indigo-500 to-blue-400`.
- **Fill Glow**: Ambient blue-violet shadow `shadow-[0_0_12px_rgba(99,102,241,0.55)]`.

---

## 7. Responsive Layout & System Inspector Drawer (`ConsoleLayout.tsx`)

### Layout Architecture
- **Header**: Compact `h-14` glass bar with cluster status indicator.
- **Sidebar**: Fixed `w-64` navigation drawer.
- **Center Workspace**: Max-width `max-w-6xl` responsive fluid layout.
- **Right System Inspector**:
  - Width: `w-80` (`20rem`).
  - Spring Physics: Framer Motion spring drawer `initial={{ width: 0, opacity: 0, x: 20 }} animate={{ width: "20rem", opacity: 1, x: 0 }} transition={{ type: "spring", stiffness: 350, damping: 30 }}`.
  - Collapsed State: Sleek vertical icon badge (`[writing-mode:vertical-rl]`) on right edge.

### Responsive Grid & Header Anti-Overflow Rules
- **KPI Telemetry Matrix**: Configured with `grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4`. When the Inspector is toggled open on standard displays, the grid automatically adapts to 2 spacious columns rather than getting squeezed.
- **Stat Cards (`StatTile.tsx`)**:
  - Container header: `flex items-start justify-between gap-2.5`.
  - Title: `min-w-0 flex-1 text-xs font-mono font-medium text-zinc-400 uppercase tracking-wider leading-snug`.
  - Status Badge: `shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[9.5px] font-mono font-semibold`.
  - The badge never overflows card boundaries regardless of inspector state.
- **Section Headers**: All section badges (`TOTAL`, `NODES`, `WORKFLOWS`, `PENDING`) maintain an explicit left margin (`ml-3.5`) to avoid crowding section titles.

---

## 8. Background 3D Silk Ribbon Canvas (`GoldenThreadsCanvas.tsx`)

- **Rendering Engine**: `@react-three/fiber` and Three.js with full screen canvas placed at `z-index: -1`.
- **Structure**: 64 continuous vector paths (line strips) with 80 vertices per strand additively blended.
- **Trajectory Mathematical Model**:
  - Base dip: `baseTrajectory(x) = -0.45 * cos((x / 16) * (PI / 2)) - 0.2`
  - Volumetric Pinch: `pinchFactor(x) = 0.24 + 0.76 * ((x / 16)^2)` (pinched tight in center, expanding outward).
  - Continuous wave offset: `u = x - 1.15 * t`.
- **Luminous Core Centerpiece**: Smooth 3D `TubeGeometry` along Catmull-Rom spline with emissive gold intensity `2.8` and incandescent white highlights.

---

## 9. Animation & Timing Specification

```
--transition-fast:     150ms  (button hovers, tab switches)
--transition-base:     200ms  (card border hovers, opacity fades)
--transition-emphatic: 250ms  (modal entries, drawer expands)
--transition-smooth:   350ms  (layout reflows, width transitions)
--ease-out:            cubic-bezier(0.16, 1, 0.3, 1)
--ease-bounce:         cubic-bezier(0.34, 1.56, 0.64, 1)
```

- **Pulsing Lights**: Status dots use `animate-pulse` coupled with radial shadows (`shadow-glow-emerald`, `shadow-glow-gold`, `shadow-glow-amber`).

---

## 10. Code Implementation Quick Reference

### Standard Card Template
```tsx
<div className="group relative overflow-hidden rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl transition-all duration-200 hover:border-white/[0.20] hover:bg-white/[0.02] shadow-sm">
  <div className="flex items-start justify-between gap-2.5">
    <h3 className="min-w-0 flex-1 text-xs font-mono font-medium text-zinc-400 uppercase tracking-wider leading-snug">
      Section Title
    </h3>
    <span className="shrink-0 whitespace-nowrap rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[9.5px] font-mono font-semibold text-emerald-400">
      HEALTHY
    </span>
  </div>
  <div className="mt-3 text-3xl font-ui font-extrabold text-white">
    {value}
  </div>
</div>
```

### Strand Marker Node Template
```tsx
{/* Geometric Marker Node */}
<rect x={x - 4} y={y - 4} width={8} height={8} rx={1.5} fill="#d97706" filter="url(#glow-amber)" />

{/* Floating Aesthetic Number */}
<line x1={x} y1={y - 5} x2={x} y2={y - 8} stroke="rgba(217, 119, 6, 0.9)" strokeWidth={0.75} strokeOpacity={0.65} />
<circle cx={x} cy={y - 13} r={8.5} fill="url(#radial-glow-amber)" pointerEvents="none" />
<text x={x} y={y - 9.5} textAnchor="middle" className="strand-number-text select-none text-[10px] font-extrabold" fill="#f59e0b" filter="url(#glow-num-amber)">
  {stepNumber}
</text>
```

---
*Copy this file to reuse the exact frontend design system across any prompt or session.*
