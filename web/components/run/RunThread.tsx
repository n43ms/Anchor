/**
 * anchor-spec.md §24.3, §24.8. A thin animated strand, not a second progress
 * bar — the bars (WorkerBar) answer "how far", this answers "what happened,
 * in what order, and where ownership changed". One gold along the whole
 * length; boundaries are marked structurally by the handoff marker, never
 * by a shade change (the measurement that forces this is in §24.7 — a
 * per-worker gold collides with worker-2's orange at CVD ΔE 1.2).
 *
 * No data fetching, no WebSocket, no API call — a pure function of props
 * (component-contract.md).
 */
"use client";

import { useMemo } from "react";
import "./strand.css";
import type { TimelineSegment } from "@/lib/types";
import { deriveMarkers } from "./types";
import { ThreadMarkers } from "./ThreadMarkers";

const VIEW_WIDTH = 620;
const VIEW_HEIGHT = 70;
const STRAND_Y = 35;
const AMPLITUDE = 14;

/** One continuous wavy path built from smooth bezier segments — never straight lines. */
function buildWavyPath(pointCount: number): string {
  if (pointCount <= 1) return `M0,${STRAND_Y} L${VIEW_WIDTH},${STRAND_Y}`;
  const segments = Math.max(pointCount - 1, 1);
  const step = VIEW_WIDTH / segments;

  let d = `M0,${STRAND_Y}`;
  for (let i = 0; i < segments; i++) {
    const x0 = i * step;
    const x1 = (i + 1) * step;
    const y0 = STRAND_Y + Math.sin(i * 1.1) * AMPLITUDE;
    const y1 = STRAND_Y + Math.sin((i + 1) * 1.1) * AMPLITUDE;
    const cx1 = x0 + step / 3;
    const cx2 = x0 + (2 * step) / 3;
    d += ` C${cx1},${y0} ${cx2},${y1} ${x1},${y1}`;
  }
  return d;
}

export function RunThread({
  segments,
  compact = false,
  animate = true,
  terminal = false,
}: {
  segments: TimelineSegment[];
  compact?: boolean;
  animate?: boolean;
  /** The run has reached a terminal state — the flow must stop (§24.3). */
  terminal?: boolean;
}) {
  const totalSteps = segments.reduce((n, s) => n + s.steps.length, 0);
  const markers = useMemo(() => deriveMarkers(segments), [segments]);
  const path = useMemo(() => buildWavyPath(Math.max(totalSteps, 1)), [totalSteps]);
  const flowing = animate && !terminal && totalSteps > 0;

  return (
    <svg
      viewBox={`0 0 ${VIEW_WIDTH} ${compact ? 24 : VIEW_HEIGHT}`}
      width="100%"
      height={compact ? 24 : VIEW_HEIGHT}
      role="img"
      aria-label={`run thread, ${totalSteps} steps, ${segments.length} segment${segments.length === 1 ? "" : "s"}`}
      data-testid="run-thread"
      className="overflow-visible"
    >
      <defs>
        <filter id="strand-golden-glow" x="-20%" y="-40%" width="140%" height="180%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path
        className="strand-path"
        data-flowing={flowing ? "true" : "false"}
        d={path}
        fill="none"
        stroke="var(--strand-gold)"
        strokeWidth={compact ? 2 : 2.5}
        strokeLinecap="round"
      />
      {!compact && <ThreadMarkers markers={markers} />}
      {compact && <CompactMarkers markers={markers} />}
    </svg>
  );
}

/** compact renders only the handoff markers — it cannot identify which
 * workers touched a run, only that a handoff occurred (§24.8); the
 * owning-worker column in the runs list is not optional because of this. */
function CompactMarkers({ markers }: { markers: ReturnType<typeof deriveMarkers> }) {
  const handoffs = markers.filter((m) => m.kind === "handoff");
  return (
    <g>
      {handoffs.map((m) => (
        <circle key={m.key} cx={m.t * VIEW_WIDTH} cy={12} r={4} fill="var(--strand-gold)" data-marker-kind="handoff" />
      ))}
    </g>
  );
}
