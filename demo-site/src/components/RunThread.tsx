import React, { useMemo, useState, useEffect } from "react";
import "./strand.css";
import type { TimelineSegment } from "../lib/types";
import { deriveMarkers } from "./runTypes";
import { ThreadMarkers } from "./ThreadMarkers";

const VIEW_WIDTH = 620;
const SAMPLES_PER_STRAND = 90;

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

function getBaseY(x: number, centerY: number, amplitude: number): number {
  const norm = (x / VIEW_WIDTH) * 2 - 1;
  return centerY + (norm * norm - 0.35) * amplitude * 0.45;
}

function getPinch(x: number): number {
  const norm = (x / VIEW_WIDTH) * 2 - 1;
  return 0.3 + 0.7 * (norm * norm);
}

function getDisplacement(x: number, time: number, strandIdx: number, amplitude: number): number {
  const u = (x / VIEW_WIDTH) * 9.5 - time * 0.75;
  const pinch = getPinch(x);

  if (strandIdx === 0) {
    return pinch * (0.55 * Math.sin(u) + 0.24 * Math.sin(2.0 * u + 0.4) + 0.1 * Math.cos(3.6 * u - 0.2)) * amplitude;
  }

  const cfg = BACKGROUND_STRAND_CONFIGS[strandIdx - 1] || BACKGROUND_STRAND_CONFIGS[0];
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

function generateSmoothStrandPath(strandIdx: number, time: number, centerY: number, amplitude: number): string {
  const step = VIEW_WIDTH / (SAMPLES_PER_STRAND - 1);
  const pts: { x: number; y: number }[] = [];

  for (let p = 0; p < SAMPLES_PER_STRAND; p++) {
    const x = p * step;
    const baseY = getBaseY(x, centerY, amplitude);
    const disp = getDisplacement(x, time, strandIdx, amplitude);
    pts.push({ x, y: baseY + disp });
  }

  if (pts.length === 0) return "";
  let d = `M${pts[0].x.toFixed(2)},${pts[0].y.toFixed(2)}`;

  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = i > 0 ? pts[i - 1] : pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = i < pts.length - 2 ? pts[i + 2] : p2;

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
  headerMode = false,
}: {
  segments: TimelineSegment[];
  compact?: boolean;
  headerMode?: boolean;
}) {
  const markers = useMemo(() => deriveMarkers(segments), [segments]);
  const viewHeight = headerMode ? 64 : compact ? 32 : 88;
  const centerY = headerMode ? 32 : compact ? 16 : 44;
  const amplitude = headerMode ? 26 : compact ? 5 : 15;

  const [time, setTime] = useState(0);

  useEffect(() => {
    let animId: number;
    let start: number | null = null;

    const tick = (now: number) => {
      if (start === null) start = now;
      const dt = (now - start) / 1000;
      setTime(dt);
      animId = requestAnimationFrame(tick);
    };

    animId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animId);
  }, []);

  const mainPath = generateSmoothStrandPath(0, time, centerY, amplitude);

  return (
    <div className={`strand-bundle-container w-full overflow-hidden select-none ${headerMode ? "h-full flex items-center" : "py-1"}`}>
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${viewHeight}`}
        preserveAspectRatio={headerMode ? "none" : "xMidYMid meet"}
        className="w-full h-full overflow-visible"
        style={{ maxHeight: headerMode ? "100%" : compact ? "32px" : "100px" }}
      >
        {/* 14 Oscillating Background Ribbon Strands (Rendered in headerMode or full view) */}
        {(!compact || headerMode) &&
          BACKGROUND_STRAND_CONFIGS.map((cfg, idx) => {
            const pathData = generateSmoothStrandPath(idx + 1, time, centerY, amplitude);
            return (
              <path
                key={cfg.id}
                d={pathData}
                fill="none"
                stroke="#f6c453"
                strokeWidth={headerMode ? cfg.width * 1.4 : cfg.width}
                strokeOpacity={headerMode ? Math.min(cfg.opacity * 2.0, 0.85) : cfg.opacity}

                className="strand-ribbon-path"
              />
            );
          })}


        {/* Primary Main Glowing Golden Strand Spine (Hidden in headerMode for clean background wave) */}
        {!headerMode && (
          <path
            d={mainPath}
            fill="none"
            stroke="#f6c453"
            strokeWidth={compact ? 2.5 : 3}
            className="strand-path"
          />
        )}

        {/* HUD Markers */}
        {!headerMode && (
          <ThreadMarkers
            markers={markers}
            getY={(x) => getBaseY(x, centerY, amplitude) + getDisplacement(x, time, 0, amplitude)}
          />
        )}
      </svg>
    </div>
  );
}


