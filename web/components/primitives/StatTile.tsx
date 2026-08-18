/**
 * anchor-spec.md §22.5: KPI row of stat tiles — label, value, optional
 * 12px sparkline. Value uses proportional figures (never tabular-nums,
 * which is reserved for columns that must align vertically).
 */
"use client";

import { useEffect, useRef, useState } from "react";

export function StatTile({
  label,
  value,
  sparkline,
  emphasize = false,
}: {
  label: string;
  value: string | number;
  sparkline?: number[];
  /** The one figure per view permitted to render large — the duplicate-effect count. */
  emphasize?: boolean;
}) {
  const [changed, setChanged] = useState(false);
  const prevValue = useRef(value);

  useEffect(() => {
    if (prevValue.current !== value) {
      setChanged(true);
      const t = window.setTimeout(() => setChanged(false), 300);
      prevValue.current = value;
      return () => window.clearTimeout(t);
    }
  }, [value]);

  return (
    <div className="rounded-md border border-gridline bg-surface-panel p-4">
      <div className="text-xs text-ink-muted">{label}</div>
      <div
        className={`figures-proportional mt-1 font-ui transition-colors duration-base ${
          emphasize ? "text-4xl" : "text-2xl"
        } ${changed ? "text-status-good" : "text-ink-primary"}`}
      >
        {value}
      </div>
      {sparkline && sparkline.length > 1 && <Sparkline values={sparkline} />}
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const width = 96;
  const height = 12;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} className="mt-2" aria-hidden="true">
      <polyline points={points} fill="none" stroke="var(--status-executing)" strokeWidth={1.5} />
    </svg>
  );
}
