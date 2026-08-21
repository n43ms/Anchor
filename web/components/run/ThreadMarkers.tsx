/**
 * Anchor Operator Console — Minimal HUD Thread Markers
 * Clean, minimal geometric shapes with ambient glow:
 * - Tool Calls: Minimal Warm Amber Square with ambient glow
 * - Model Calls: Minimal Deep Indigo Circle with ambient glow
 * - Handoff Beacons: Radiant Sun Gold Circle
 * - Reconciled: Emerald Mint Ring
 */
import type { MarkerKind, ThreadMarker } from "./types";

const VIEW_WIDTH = 620;
const STRAND_Y = 44;

/** Minimum horizontal gap (px, at VIEW_WIDTH scale) two adjacent labels need to both render. */
const MIN_LABEL_GAP = 36;

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
      {/* SVG Glow Filters for Ambient Lighting */}
      <defs>
        <filter id="glow-indigo" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#6366f1" floodOpacity="0.9" />
        </filter>
        <filter id="glow-amber" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#d97706" floodOpacity="0.9" />
        </filter>
        <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="3.5" floodColor="#fef08a" floodOpacity="0.95" />
        </filter>
      </defs>

      {markers.map((marker, i) => {
        const x = marker.t * VIEW_WIDTH;
        const y = getY ? getY(x) : STRAND_Y;
        const dropped = shouldDropLabel(markers, i);
        const isHandoff = marker.kind === "handoff";
        const isToolCall = marker.kind === "side_effect";
        const isReconciled = marker.kind === "reconciled";
        const size = isHandoff ? 5.5 : 4;
        const labelText = marker.label;
        const textWidth = Math.max(labelText.length * 6.4 + 10, 30);

        // Glowy themed badge styling
        const badgeBorder = isHandoff
          ? "rgba(254, 240, 138, 0.75)"
          : isToolCall
            ? "rgba(217, 119, 6, 0.85)"
            : isReconciled
              ? "rgba(52, 211, 153, 0.65)"
              : "rgba(99, 102, 241, 0.75)";

        const badgeFill = isHandoff
          ? "#0a0802"
          : isToolCall
            ? "#0d0601"
            : isReconciled
              ? "#020a06"
              : "#04050d";

        const textColor = isHandoff
          ? "#fef08a"
          : isToolCall
            ? "#fed7aa"
            : isReconciled
              ? "#d1fae5"
              : "#c7d2fe";

        return (
          <g
            key={marker.key}
            data-marker-kind={marker.kind}
            data-marker-label={marker.label}
            className="strand-marker-node"
          >
            <title>{marker.label}</title>

            {/* Minimal Ambient Marker Shape */}
            <MarkerShape kind={marker.kind} x={x} y={y} size={size} />

            {/* Sleek HUD Text Badge with Leader Line */}
            {!dropped && (
              <g className="strand-label-group">
                {/* Hairline connector tick from node to badge */}
                <line
                  x1={x}
                  y1={y - size - 1}
                  x2={x}
                  y2={y - size - 5}
                  stroke={badgeBorder}
                  strokeWidth={0.8}
                  strokeOpacity={0.85}
                />
                {/* Frosted Dark Badge */}
                <rect
                  x={x - textWidth / 2}
                  y={y - size - 18}
                  width={textWidth}
                  height={13}
                  rx={3}
                  fill={badgeFill}
                  fillOpacity={0.95}
                  stroke={badgeBorder}
                  strokeWidth={0.85}
                />
                <text
                  x={x}
                  y={y - size - 8.5}
                  textAnchor="middle"
                  className="strand-label-text select-none font-mono text-[8.5px] font-semibold tracking-wider"
                  fill={textColor}
                >
                  {labelText}
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
