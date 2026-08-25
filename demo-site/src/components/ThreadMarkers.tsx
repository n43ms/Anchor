import React from "react";
import type { ThreadMarker } from "./runTypes";

const VIEW_WIDTH = 620;
const STRAND_Y = 44;

export function ThreadMarkers({
  markers,
  getY,
}: {
  markers: ThreadMarker[];
  getY?: (x: number) => number;
}) {
  return (
    <g className="strand-markers-layer">
      {markers.map((marker, i) => {
        const x = marker.t * VIEW_WIDTH;
        const y = getY ? getY(x) : STRAND_Y;
        const isHandoff = marker.kind === "handoff";
        const isToolCall = marker.kind === "side_effect";
        const isReconciled = marker.kind === "reconciled";
        const size = isHandoff ? 5.5 : 4;
        const stepDisplay = marker.stepNumber !== undefined ? String(marker.stepNumber) : isHandoff ? "⇄" : String(i + 1);

        return (
          <g key={marker.key} transform={`translate(${x}, ${y})`} className="strand-marker-node">
            {/* Shape & Color Coded Markers: Handoff Beacon, Side-Effect Amber Square, Reconciled Green Ring, Model Blue Circle */}
            {isHandoff ? (
              <circle r={size + 2} fill="#10b981" fillOpacity="0.3" stroke="#10b981" strokeWidth="1.5" />
            ) : isToolCall ? (
              <rect
                x={-size}
                y={-size}
                width={size * 2}
                height={size * 2}
                rx="1.5"
                fill="#f59e0b"
                stroke="#fbbf24"
                strokeWidth="1.5"
              />
            ) : isReconciled ? (
              <circle r={size} fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="2 1" />
            ) : (
              /* Blue / Indigo Circle for LLM Model Calls */
              <circle r={size} fill="#3b82f6" stroke="#60a5fa" strokeWidth="1.5" />
            )}

            {/* Step Label Number below strand */}
            <text
              y={isHandoff ? -12 : 16}
              textAnchor="middle"
              fontSize="9"
              fontWeight="bold"
              fill={isHandoff ? "#10b981" : isToolCall ? "#fbbf24" : isReconciled ? "#34d399" : "#60a5fa"}
              className="strand-number-text"
            >
              {stepDisplay}
            </text>
          </g>
        );
      })}
    </g>
  );
}

