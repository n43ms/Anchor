/**
 * Anchor Operator Console — Glowy Indigo & Warm Dark-Orange Amber HUD Thread Markers
 * - Model Calls: Glowy Blue Deep Indigo (#6366f1 / #4f46e5)
 * - Tool Calls: Glowy Warm Dark-Orange Amber (#d97706 / #ea580c / #f97316)
 * - Handoff Beacons: Radiant Sun Gold & Diamond White (#fef08a)
 * - Reconciled: Emerald Mint Reticle (#34d399)
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
      {/* SVG Glow Filters for Deep Indigo & Dark Warm Amber */}
      <defs>
        <filter id="glow-indigo" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="0" stdDeviation="2.5" floodColor="#6366f1" floodOpacity="0.85" />
        </filter>
        <filter id="glow-amber" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="0" stdDeviation="2.5" floodColor="#d97706" floodOpacity="0.9" />
        </filter>
        <filter id="glow-gold" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#fef08a" floodOpacity="0.9" />
        </filter>
      </defs>

      {markers.map((marker, i) => {
        const x = marker.t * VIEW_WIDTH;
        const y = getY ? getY(x) : STRAND_Y;
        const dropped = shouldDropLabel(markers, i);
        const isHandoff = marker.kind === "handoff";
        const isToolCall = marker.kind === "side_effect";
        const isReconciled = marker.kind === "reconciled";
        const size = isHandoff ? 6.5 : 4.5;
        const labelText = marker.label;
        const textWidth = Math.max(labelText.length * 6.4 + 10, 30);

        // Glowy themed badge styling
        const badgeBorder = isHandoff
          ? "rgba(254, 240, 138, 0.75)"
          : isToolCall
            ? "rgba(217, 119, 6, 0.85)" // Glowy Warm Dark-Orange Amber for Tool Calls
            : isReconciled
              ? "rgba(52, 211, 153, 0.65)"
              : "rgba(99, 102, 241, 0.75)"; // Glowy Blue Deep Indigo for Model Calls

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
            ? "#fed7aa" // Warm Orangey-Amber text
            : isReconciled
              ? "#d1fae5"
              : "#c7d2fe"; // Light Indigo-Ice text for Model Calls

        return (
          <g
            key={marker.key}
            data-marker-kind={marker.kind}
            data-marker-label={marker.label}
            className="strand-marker-node"
          >
            <title>{marker.label}</title>

            {/* Precision Marker Shape */}
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
    // Tool Call: Glowy Warm Dark-Orange Amber Square (#d97706 / #ea580c)
    return (
      <g filter="url(#glow-amber)">
        <rect
          x={x - size - 1.2}
          y={y - size - 1.2}
          width={(size + 1.2) * 2}
          height={(size + 1.2) * 2}
          rx={2}
          fill="#0d0601"
          fillOpacity={0.95}
          stroke="rgba(217, 119, 6, 0.7)"
          strokeWidth={0.8}
        />
        <rect
          x={x - size}
          y={y - size}
          width={size * 2}
          height={size * 2}
          rx={1.5}
          fill="#d97706"
          stroke="#fed7aa"
          strokeWidth={0.9}
          data-shape="square"
        />
      </g>
    );
  }

  if (kind === "reconciled") {
    // Reconciled Step: Emerald Mint Reticle Ring (#34d399)
    return (
      <g>
        <circle cx={x} cy={y} r={size + 1.2} fill="#020a06" fillOpacity={0.95} />
        <circle
          cx={x}
          cy={y}
          r={size}
          fill="none"
          stroke="#34d399"
          strokeWidth={1.8}
          data-shape="ring"
        />
        <circle cx={x} cy={y} r={1.3} fill="#6ee7b7" />
      </g>
    );
  }

  if (kind === "handoff") {
    // Handoff Beacon: Radiant Sun Gold & Diamond White Core
    return (
      <g filter="url(#glow-gold)">
        <circle
          cx={x}
          cy={y}
          r={size + 1.8}
          fill="#0a0802"
          fillOpacity={0.95}
          stroke="rgba(254, 240, 138, 0.7)"
          strokeWidth={0.9}
        />
        <circle
          cx={x}
          cy={y}
          r={size}
          fill="var(--strand-gold)"
          stroke="#ffffff"
          strokeWidth={1.3}
          data-shape="circle"
          data-handoff="true"
        />
        <circle cx={x} cy={y} r={2} fill="#ffffff" />
      </g>
    );
  }

  // Model Call (Ordinary Step): Glowy Blue Deep Indigo (#6366f1 / #4f46e5 / #818cf8)
  return (
    <g filter="url(#glow-indigo)">
      <circle
        cx={x}
        cy={y}
        r={size + 1.2}
        fill="#04050d"
        fillOpacity={0.95}
        stroke="rgba(99, 102, 241, 0.6)"
        strokeWidth={0.8}
      />
      <circle
        cx={x}
        cy={y}
        r={size - 0.8}
        fill="#6366f1"
        stroke="#c7d2fe"
        strokeWidth={0.8}
        data-shape="circle"
      />
      <circle cx={x} cy={y} r={1.2} fill="#ffffff" />
    </g>
  );
}
