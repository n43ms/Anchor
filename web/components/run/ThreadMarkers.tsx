/**
 * Anchor Operator Console — Minimal Numbered Legend HUD Thread Markers
 * Clean, minimal geometric shapes with ambient glow and aesthetic floating numbers:
 * - Floating numbers use the aesthetic UI font with subtle radial glow highlights
 * - Tool Calls: Minimal Warm Amber Square with ambient glow & Clean Amber Number
 * - Model Calls: Minimal Deep Indigo Circle with ambient glow & Clean Indigo Number
 * - Handoff Beacons: Radiant Sun Gold Circle & Clean Gold "⇄" Icon
 * - Reconciled: Emerald Mint Ring & Clean Mint Number
 */
import type { MarkerKind, ThreadMarker } from "./types";

const VIEW_WIDTH = 620;
const STRAND_Y = 44;

/** Minimum horizontal gap (px, at VIEW_WIDTH scale) two adjacent labels need to both render. */
const MIN_LABEL_GAP = 18;

function shouldDropLabel(markers: ThreadMarker[], index: number): boolean {
  if (markers[index].kind === "handoff") return false; // Handoff is critical, never dropped
  const x = markers[index].t * VIEW_WIDTH;
  const prev = markers[index - 1];
  const next = markers[index + 1];
  if (prev && Math.abs(x - prev.t * VIEW_WIDTH) < MIN_LABEL_GAP) return true;
  if (next && Math.abs(next.t * VIEW_WIDTH - x) < MIN_LABEL_GAP && next.kind === "handoff") return true;
  return false;
}

export function ThreadMarkers({
  markers,
  getY,
}: {
  markers: ThreadMarker[];
  getY?: (x: number) => number;
}) {
  return (
    <g className="strand-markers-layer">
      {/* SVG Glow Filters & Radial Gradients for Subtle Radial Highlighting */}
      <defs>
        {/* Ambient Drop Shadow Filters for Marker Shapes */}
        <filter id="glow-indigo" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#6366f1" floodOpacity="0.9" />
        </filter>
        <filter id="glow-amber" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#d97706" floodOpacity="0.9" />
        </filter>
        <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="3.5" floodColor="#fef08a" floodOpacity="0.95" />
        </filter>

        {/* Very Slight Text Drop Glows for Aesthetic Numbers */}
        <filter id="glow-num-indigo" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="0" stdDeviation="1.8" floodColor="#818cf8" floodOpacity="0.85" />
        </filter>
        <filter id="glow-num-amber" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="0" stdDeviation="1.8" floodColor="#fbbf24" floodOpacity="0.85" />
        </filter>
        <filter id="glow-num-gold" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="0" stdDeviation="2.0" floodColor="#fef08a" floodOpacity="0.9" />
        </filter>
        <filter id="glow-num-mint" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="0" stdDeviation="1.8" floodColor="#34d399" floodOpacity="0.85" />
        </filter>

        {/* Soft Micro Radial Glow Highlights behind floating numbers */}
        <radialGradient id="radial-glow-indigo" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#6366f1" stopOpacity="0.32" />
          <stop offset="60%" stopColor="#6366f1" stopOpacity="0.10" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="radial-glow-amber" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#d97706" stopOpacity="0.32" />
          <stop offset="60%" stopColor="#d97706" stopOpacity="0.10" />
          <stop offset="100%" stopColor="#d97706" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="radial-glow-gold" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fef08a" stopOpacity="0.35" />
          <stop offset="60%" stopColor="#fef08a" stopOpacity="0.12" />
          <stop offset="100%" stopColor="#fef08a" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="radial-glow-mint" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#34d399" stopOpacity="0.32" />
          <stop offset="60%" stopColor="#34d399" stopOpacity="0.10" />
          <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
        </radialGradient>
      </defs>

      {markers.map((marker, i) => {
        const x = marker.t * VIEW_WIDTH;
        const y = getY ? getY(x) : STRAND_Y;
        const dropped = shouldDropLabel(markers, i);
        const isHandoff = marker.kind === "handoff";
        const isToolCall = marker.kind === "side_effect";
        const isReconciled = marker.kind === "reconciled";
        const size = isHandoff ? 5.5 : 4;
        const stepDisplay = marker.stepNumber !== undefined ? String(marker.stepNumber) : isHandoff ? "⇄" : String(i + 1);

        const glowType = isHandoff ? "gold" : isToolCall ? "amber" : isReconciled ? "mint" : "indigo";

        const badgeBorder = isHandoff
          ? "rgba(254, 240, 138, 0.75)"
          : isToolCall
            ? "rgba(217, 119, 6, 0.85)"
            : isReconciled
              ? "rgba(52, 211, 153, 0.65)"
              : "rgba(99, 102, 241, 0.75)";

        const textColor = isHandoff
          ? "#fef08a"
          : isToolCall
            ? "#fde047"
            : isReconciled
              ? "#a7f3d0"
              : "#e0e7ff";

        return (
          <g
            key={marker.key}
            data-marker-kind={marker.kind}
            data-marker-label={marker.label}
            className="strand-marker-node"
          >
            <title>{marker.stepNumber !== undefined ? `Step ${marker.stepNumber}: ` : ""}{marker.label}</title>

            {/* Minimal Ambient Marker Shape ON the Thread */}
            <MarkerShape kind={marker.kind} x={x} y={y} size={size} />

            {/* Aesthetic Floating Number with Slight Radial Glow Highlight */}
            {!dropped && (
              <g className="strand-label-group">
                {/* Hairline connector tick */}
                <line
                  x1={x}
                  y1={y - size - 1}
                  x2={x}
                  y2={y - size - 4}
                  stroke={badgeBorder}
                  strokeWidth={0.75}
                  strokeOpacity={0.65}
                />
                {/* Soft Micro Radial Glow Halo */}
                <circle
                  cx={x}
                  cy={y - size - 9}
                  r={8.5}
                  fill={`url(#radial-glow-${glowType})`}
                  pointerEvents="none"
                />
                {/* Clean Number in Aesthetic UI Font with Soft Glow */}
                <text
                  x={x}
                  y={y - size - 5.5}
                  textAnchor="middle"
                  className="strand-number-text select-none text-[10px] font-extrabold"
                  fill={textColor}
                  filter={`url(#glow-num-${glowType})`}
                >
                  {stepDisplay}
                </text>
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
}

function MarkerShape({
  kind,
  x,
  y,
  size,
}: {
  kind: MarkerKind;
  x: number;
  y: number;
  size: number;
}) {
  if (kind === "side_effect") {
    // Minimal Warm Amber Square with ambient glow
    return (
      <rect
        x={x - size}
        y={y - size}
        width={size * 2}
        height={size * 2}
        rx={1.5}
        fill="#d97706"
        filter="url(#glow-amber)"
        data-shape="square"
      />
    );
  }

  if (kind === "reconciled") {
    // Minimal Emerald Mint Ring
    return (
      <circle
        cx={x}
        cy={y}
        r={size}
        fill="none"
        stroke="#34d399"
        strokeWidth={1.8}
        data-shape="ring"
      />
    );
  }

  if (kind === "handoff") {
    // Minimal Radiant Gold Circle Beacon with ambient glow
    return (
      <circle
        cx={x}
        cy={y}
        r={size}
        fill="var(--strand-gold)"
        filter="url(#glow-gold)"
        data-shape="circle"
        data-handoff="true"
      />
    );
  }

  // Model Call (Ordinary Step): Minimal Deep Indigo Circle with ambient glow
  return (
    <circle
      cx={x}
      cy={y}
      r={size}
      fill="#6366f1"
      filter="url(#glow-indigo)"
      data-shape="circle"
    />
  );
}
