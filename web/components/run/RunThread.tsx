/**
 * anchor-spec.md §24.3, §24.8.
 *
 * Runtime Execution Thread:
 * - Full Detail View: 15-Strand Execution Thread Stream with step markers & 60fps wave motion
 * - Compact Cockpit View: Static, zero-overhead topological run shape with step markers matching the thread
 */
"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import "./strand.css";
import type { TimelineSegment } from "@/lib/types";
import { deriveMarkers } from "./types";
import { ThreadMarkers } from "./ThreadMarkers";

const VIEW_WIDTH = 620;
const STRAND_COUNT = 15; // 1 Main + 14 Background strands for thread visualization density
const SAMPLES_PER_STRAND = 90;

// 14 Background Execution Strands (delicate, highly translucent paths)
const BACKGROUND_STRAND_CONFIGS = [
  { id: 1, opacity: 0.22, width: 1.1, phaseMult: 0.8, radialOffset: -1.4 },
  { id: 2, opacity: 0.14, width: 0.85, phaseMult: 1.6, radialOffset: 1.5 },
  { id: 3, opacity: 0.25, width: 1.2, phaseMult: 2.5, radialOffset: -0.9 },
  { id: 4, opacity: 0.10, width: 0.75, phaseMult: 3.4, radialOffset: 1.1 },
  { id: 5, opacity: 0.20, width: 1.0, phaseMult: 4.2, radialOffset: -1.7 },
  { id: 6, opacity: 0.23, width: 1.1, phaseMult: 5.1, radialOffset: 0.7 },
  { id: 7, opacity: 0.13, width: 0.8, phaseMult: 5.9, radialOffset: -1.2 },
  { id: 8, opacity: 0.18, width: 0.95, phaseMult: 6.8, radialOffset: 1.8 },
  { id: 9, opacity: 0.26, width: 1.25, phaseMult: 7.6, radialOffset: -0.5 },
  { id: 10, opacity: 0.16, width: 0.85, phaseMult: 8.5, radialOffset: 1.3 },
  { id: 11, opacity: 0.13, width: 0.9, phaseMult: 9.3, radialOffset: -1.5 },
  { id: 12, opacity: 0.18, width: 1.05, phaseMult: 10.1, radialOffset: 0.9 },
  { id: 13, opacity: 0.11, width: 0.8, phaseMult: 11.0, radialOffset: -0.7 },
  { id: 14, opacity: 0.15, width: 0.95, phaseMult: 11.8, radialOffset: 1.4 },
];

// Macroscopic base trajectory for full ribbon
function getBaseY(x: number, centerY: number, amplitude: number): number {
  const norm = (x / VIEW_WIDTH) * 2 - 1; // -1 to 1
  return centerY + (norm * norm - 0.35) * amplitude * 0.45;
}

// 3D volumetric pinch for full ribbon
function getPinch(x: number): number {
  const norm = (x / VIEW_WIDTH) * 2 - 1;
  return 0.3 + 0.7 * (norm * norm);
}

// Calculates displacement for a given strand at (x, time)
function getDisplacement(
  x: number,
  time: number,
  strandIdx: number,
  amplitude: number
): number {
  const u = (x / VIEW_WIDTH) * 9.5 - time * 0.75;
  const pinch = getPinch(x);

  if (strandIdx === 0) {
    // Primary Main Light-Golden Strand
    return (
      pinch *
      (0.55 * Math.sin(u) +
        0.24 * Math.sin(2.0 * u + 0.4) +
        0.1 * Math.cos(3.6 * u - 0.2)) *
      amplitude
    );
  }

  const cfg = BACKGROUND_STRAND_CONFIGS[strandIdx - 1] ?? BACKGROUND_STRAND_CONFIGS[0]!;
  const phase = cfg.phaseMult;
  const radial = cfg.radialOffset;
  const twist = strandIdx * 0.8 + time * 0.18;

  return (
    pinch *
    (radial * Math.cos(twist + 0.1 * u) +
      0.48 * Math.sin(u + phase) +
      0.22 * Math.sin(2.0 * u + 2 * phase) +
      0.09 * Math.cos(3.6 * u - phase)) *
    amplitude
  );
}

// Builds a smooth, continuous cubic Bézier SVG path string for full ribbon
function generateSmoothStrandPath(
  strandIdx: number,
  time: number,
  centerY: number,
  amplitude: number
): string {
  const step = VIEW_WIDTH / (SAMPLES_PER_STRAND - 1);
  const pts: { x: number; y: number }[] = [];

  for (let p = 0; p < SAMPLES_PER_STRAND; p++) {
    const x = p * step;
    const baseY = getBaseY(x, centerY, amplitude);
    const disp = getDisplacement(x, time, strandIdx, amplitude);
    pts.push({ x, y: baseY + disp });
  }

  if (pts.length === 0) return "";
  let d = `M${pts[0]!.x.toFixed(2)},${pts[0]!.y.toFixed(2)}`;

  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = i > 0 ? pts[i - 1]! : pts[i]!;
    const p1 = pts[i]!;
    const p2 = pts[i + 1]!;
    const p3 = i < pts.length - 2 ? pts[i + 2]! : p2;

    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;

    d += ` C${cp1x.toFixed(2)},${cp1y.toFixed(2)} ${cp2x.toFixed(2)},${cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
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
  terminal?: boolean;
}) {
  const totalSteps = segments.reduce((n, s) => n + s.steps.length, 0);
  const markers = useMemo(() => deriveMarkers(segments), [segments]);

  // In compact mode: static rendering with 0 CPU/memory overhead
  // In active full detail view: animated wave (always moves even when run halts/finishes)
  const flowing = !compact && animate !== false;


  const viewHeight = compact ? 26 : 88;
  const centerY = compact ? 13 : 44;
  const amplitude = compact ? 5 : 15;

  const [time, setTime] = useState(0);
  const animRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number | null>(null);

  // Smooth continuous 60fps requestAnimationFrame loop (only for full detail view)
  useEffect(() => {
    if (!flowing) return;

    const tick = (now: number) => {
      if (lastTimeRef.current !== null) {
        const dt = Math.min((now - lastTimeRef.current) / 1000, 0.05);
        setTime((prev) => prev + dt);
      }
      lastTimeRef.current = now;
      animRef.current = requestAnimationFrame(tick);
    };

    animRef.current = requestAnimationFrame(tick);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      lastTimeRef.current = null;
    };
  }, [flowing]);

  // Main Light Golden Strand (Strand 0)
  const mainPath = useMemo(() => {
    if (compact) return "";
    return generateSmoothStrandPath(0, time, centerY, amplitude);
  }, [time, centerY, amplitude, compact]);

  // 10 Dark Golden Background Strands (only for full view)
  const secondaryStrands = useMemo(() => {
    if (compact) return [];
    return BACKGROUND_STRAND_CONFIGS.map((cfg) => {
      const d = generateSmoothStrandPath(cfg.id, time, centerY, amplitude);
      return {
        id: cfg.id,
        d,
        opacity: cfg.opacity,
        strokeWidth: cfg.width,
      };
    });
  }, [time, centerY, amplitude, compact]);

  // Evaluates exact Y coordinate on the Main Light Golden Strand for anchoring step markers
  const getMainStrandY = (x: number): number => {
    const baseY = getBaseY(x, centerY, amplitude);
    const disp = getDisplacement(x, time, 0, amplitude);
    return baseY + disp;
  };

  return (
    <div className="strand-bundle-container relative w-full overflow-visible">
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${viewHeight}`}
        width="100%"
        height={viewHeight}
        role="img"
        aria-label={`run thread, ${totalSteps} steps, ${segments.length} segment${
          segments.length === 1 ? "" : "s"
        }`}
        data-testid="run-thread"
        className="overflow-visible select-none"
        shapeRendering="geometricPrecision"
      >
        <defs>
          {/* Edge transparency mask */}
          <linearGradient id="strand-edge-mask" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="white" stopOpacity="0" />
            <stop offset="6%" stopColor="white" stopOpacity="0.85" />
            <stop offset="50%" stopColor="white" stopOpacity="1" />
            <stop offset="94%" stopColor="white" stopOpacity="0.85" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <mask id="strand-fade-mask">
            <rect x="0" y="0" width={VIEW_WIDTH} height={viewHeight} fill="url(#strand-edge-mask)" />
          </mask>
        </defs>

        {/* Compact Mode: Static, zero-overhead topological run shape preview */}
        {compact ? (
          <CompactRunShape segments={segments} />
        ) : (
          /* Full View: 11-Strand Interwoven Ribbon Bundle with Multi-Color HUD Markers */
          <>
            <g mask="url(#strand-fade-mask)">
              {secondaryStrands.map((strand) => (
                <path
                  key={strand.id}
                  d={strand.d}
                  fill="none"
                  stroke="var(--strand-gold)"
                  strokeOpacity={strand.opacity}
                  strokeWidth={strand.strokeWidth}
                  className="strand-ribbon-path"
                />
              ))}

              {/* Main Light Golden Thread Underglow Bloom */}
              <path
                d={mainPath}
                fill="none"
                stroke="var(--strand-gold)"
                strokeWidth={2.8}
                strokeOpacity={0.22}
                strokeLinecap="round"
              />

              {/* Primary Main Light Golden Execution Spine (78% translucent) */}
              <path
                className="strand-path"
                data-flowing={flowing ? "true" : "false"}
                d={mainPath}
                fill="none"
                stroke="var(--strand-gold)"
                strokeWidth={1.35}
                strokeOpacity={0.78}
                strokeLinecap="round"
              />
              {/* Incandescent Pale Sun Gold Core Highlight (78% translucent) */}
              <path
                d={mainPath}
                fill="none"
                stroke="var(--strand-gold)"
                strokeWidth={0.75}
                strokeOpacity={0.78}
                strokeLinecap="round"
              />
            </g>

            {/* Precision HUD Step Markers mathematically anchored ON the main strand */}
            <ThreadMarkers markers={markers} getY={getMainStrandY} />
          </>
        )}
      </svg>
    </div>
  );
}

/**
 * CompactRunShape renders a lightweight, static (zero CPU/memory overhead)
 * approximate topological shape of the run for the Execution Stream Cockpit:
 * - Enlarged golden markers matching the thread color (var(--strand-gold))
 * - Step-by-step deflection trajectory representing model vs tool vs replay vs handoff
 * - Baseline timeline guide
 */
function CompactRunShape({
  segments,
}: {
  segments: TimelineSegment[];
}) {
  const allSteps: {
    key: string;
    stepIndex: number;
    actionKind: string;
    status: string;
    isHandoff: boolean;
    workerId: string;
  }[] = [];

  segments.forEach((seg, sIdx) => {
    if (sIdx > 0) {
      allSteps.push({
        key: `handoff-${seg.worker_id}-${sIdx}`,
        stepIndex: -1,
        actionKind: "handoff",
        status: "done",
        isHandoff: true,
        workerId: seg.worker_id,
      });
    }
    seg.steps.forEach((step) => {
      allSteps.push({
        key: `step-${seg.worker_id}-${step.step_index}`,
        stepIndex: step.step_index,
        actionKind: step.action_kind,
        status: step.status,
        isHandoff: false,
        workerId: seg.worker_id,
      });
    });
  });

  const total = allSteps.length;
  const W = VIEW_WIDTH;
  const midY = 13;

  if (total === 0) {
    return (
      <g>
        <line x1={8} y1={midY} x2={W - 8} y2={midY} stroke="var(--hairline-ring)" strokeWidth={1} strokeDasharray="3 3" />
        <circle cx={16} cy={midY} r={3.5} fill="var(--strand-gold)" stroke="var(--ink-primary)" strokeWidth={0.8} />
      </g>
    );
  }

  // Calculate coordinates for each step
  const pts = allSteps.map((s, i) => {
    const x = total === 1 ? W / 2 : 16 + (i / (total - 1)) * (W - 32);
    let y = midY;
    if (s.isHandoff) {
      y = 6; // Elevated peak for worker handoff
    } else if (s.actionKind === "tool") {
      y = 8.5; // Elevated deflection for tool call
    } else if (s.actionKind === "model") {
      y = 15.5; // Lower baseline for model inference
    } else if (s.status === "skipped_on_replay") {
      y = 18; // Replay offset
    }
    return { ...s, x, y };
  });

  // Build smooth trajectory line
  let pathD = `M${pts[0]!.x.toFixed(1)},${pts[0]!.y.toFixed(1)}`;
  if (pts.length === 1) {
    pathD = `M8,${midY} L${pts[0]!.x.toFixed(1)},${pts[0]!.y.toFixed(1)} L${W - 8},${midY}`;
  } else {
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = i > 0 ? pts[i - 1]! : pts[i]!;
      const p1 = pts[i]!;
      const p2 = pts[i + 1]!;
      const p3 = i < pts.length - 2 ? pts[i + 2]! : p2;

      const cp1x = p1.x + (p2.x - p0.x) / 5;
      const cp1y = p1.y + (p2.y - p0.y) / 5;
      const cp2x = p2.x - (p3.x - p1.x) / 5;
      const cp2y = p2.y - (p3.y - p1.y) / 5;

      pathD += ` C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
  }

  return (
    <g>
      {/* Background Guide Rail */}
      <line x1={8} y1={midY} x2={W - 8} y2={midY} stroke="var(--hairline-ring)" strokeWidth={1} />

      {/* Trajectory Underglow Bloom */}
      <path d={pathD} fill="none" stroke="var(--strand-gold)" strokeWidth={2.8} strokeOpacity={0.25} strokeLinecap="round" />

      {/* Trajectory Golden Strand (78% translucent) */}
      <path d={pathD} fill="none" stroke="var(--strand-gold)" strokeWidth={1.35} strokeOpacity={0.78} strokeLinecap="round" />
      <path d={pathD} fill="none" stroke="var(--strand-gold)" strokeWidth={0.7} strokeOpacity={0.78} strokeLinecap="round" />

      {/* Minimal Step Markers Matching the Golden Thread Color */}
      {pts.map((p) => {
        if (p.isHandoff) {
          // Handoff: Clean Golden Circle with White Core
          return (
            <g key={p.key}>
              <circle cx={p.x} cy={p.y} r={3.6} fill="var(--strand-gold)" stroke="var(--ink-primary)" strokeWidth={0.8} />
              <circle cx={p.x} cy={p.y} r={1.2} fill="var(--ink-primary)" />
            </g>
          );
        }

        if (p.actionKind === "tool") {
          // Tool Call: Simple Minimal Golden Square
          return (
            <rect
              key={p.key}
              x={p.x - 2.8}
              y={p.y - 2.8}
              width={5.6}
              height={5.6}
              rx={1.2}
              fill="var(--strand-gold)"
            />
          );
        }

        if (p.status === "skipped_on_replay") {
          // Replayed Step: Clean Minimal Golden Ring
          return (
            <circle
              key={p.key}
              cx={p.x}
              cy={p.y}
              r={2.8}
              fill="none"
              stroke="var(--strand-gold)"
              strokeWidth={1.5}
            />
          );
        }

        // Model Call: Simple Minimal Golden Circle
        return (
          <circle
            key={p.key}
            cx={p.x}
            cy={p.y}
            r={2.8}
            fill="var(--strand-gold)"
          />
        );
      })}
    </g>
  );
}
