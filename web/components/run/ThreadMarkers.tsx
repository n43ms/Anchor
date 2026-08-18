/**
 * anchor-spec.md §24.3, §24.7 — shape is required, not decorative. The
 * red/green pair (side-effect vs reconciled) sits at CVD ΔE 4.1 and cannot
 * be fixed with color, so circle / square / ring must survive on their own
 * in grayscale, under every form of color blindness, and in a compressed
 * screen recording.
 */
import type { MarkerKind, ThreadMarker } from "./types";

const VIEW_WIDTH = 620;
const STRAND_Y = 35;

const MARKER_COLOR_VAR: Record<MarkerKind, string> = {
  ordinary: "var(--marker-ordinary)",
  side_effect: "var(--marker-side-effect)",
  reconciled: "var(--marker-reconciled)",
  handoff: "var(--strand-gold)",
};

/** Minimum horizontal gap (px, at VIEW_WIDTH scale) two adjacent labels need to both render. */
const MIN_LABEL_GAP = 34;

function shouldDropLabel(markers: ThreadMarker[], index: number): boolean {
  if (markers[index].kind === "handoff") return false; // the money moment — never dropped
  const x = markers[index].t * VIEW_WIDTH;
  const prev = markers[index - 1];
  const next = markers[index + 1];
  if (prev && Math.abs(x - prev.t * VIEW_WIDTH) < MIN_LABEL_GAP) return true;
  if (next && Math.abs(next.t * VIEW_WIDTH - x) < MIN_LABEL_GAP && next.kind === "handoff") return true;
  return false;
}

export function ThreadMarkers({ markers }: { markers: ThreadMarker[] }) {
  return (
    <g>
      {markers.map((marker, i) => {
        const x = marker.t * VIEW_WIDTH;
        const dropped = shouldDropLabel(markers, i);
        const color = MARKER_COLOR_VAR[marker.kind];
        const isHandoff = marker.kind === "handoff";
        const size = isHandoff ? 6 : 4;

        return (
          <g key={marker.key} data-marker-kind={marker.kind} data-marker-label={marker.label}>
            <MarkerShape kind={marker.kind} x={x} y={STRAND_Y} size={size} color={color} />
            {!dropped && (
              <text
                x={x}
                y={STRAND_Y - size - 6}
                textAnchor="middle"
                className="font-ui"
                fontSize={isHandoff ? 12 : 11}
                fill={isHandoff ? "var(--strand-gold)" : "var(--ink-muted)"}
              >
                {marker.label}
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}

function MarkerShape({ kind, x, y, size, color }: { kind: MarkerKind; x: number; y: number; size: number; color: string }) {
  if (kind === "side_effect") {
    return <rect x={x - size} y={y - size} width={size * 2} height={size * 2} fill={color} data-shape="square" />;
  }
  if (kind === "reconciled") {
    return <circle cx={x} cy={y} r={size} fill="none" stroke={color} strokeWidth={2} data-shape="ring" />;
  }
  if (kind === "handoff") {
    return <circle cx={x} cy={y} r={size} fill={color} data-shape="circle" data-handoff="true" />;
  }
  return <circle cx={x} cy={y} r={size} fill={color} data-shape="circle" />;
}
