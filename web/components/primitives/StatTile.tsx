/**
 * anchor-spec.md §22.5: KPI row of stat tiles — label, value, optional
 * 12px sparkline. Value uses proportional figures (never tabular-nums,
 * which is reserved for columns that must align vertically).
 */
"use client";

import { useEffect, useId, useRef, useState } from "react";

export function StatTile({
  label,
  value,
  sparkline,
  emphasize = false,
  badge,
}: {
  label: string;
  value: string | number;
  sparkline?: number[];
  /** The one figure per view permitted to render large — the duplicate-effect count. */
  emphasize?: boolean;
  badge?: string;
}) {
  const [changed, setChanged] = useState(false);
  const prevValue = useRef(value);

  useEffect(() => {
    if (prevValue.current !== value) {
      setChanged(true);
      const t = window.setTimeout(() => setChanged(false), 400);
      prevValue.current = value;
      return () => window.clearTimeout(t);
    }
  }, [value]);

  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl transition-all duration-base hover:border-white/[0.2] hover:bg-white/[0.02] shadow-sm ${
        emphasize ? "ring-1 ring-strand-gold/40 border-strand-gold/30" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="text-xs font-mono font-medium text-zinc-400 uppercase tracking-wider">{label}</div>
        {badge && (
          <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-mono font-semibold text-emerald-400 border border-emerald-500/30">
            {badge}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <div
          className={`figures-proportional font-ui font-extrabold transition-all duration-base ${
            emphasize ? "text-4xl text-strand-gold" : "text-3xl text-white"
          } ${changed ? "scale-105 text-emerald-400" : ""}`}
        >
          {value}
        </div>
        {sparkline && sparkline.length > 1 && <Sparkline values={sparkline} />}
      </div>
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const gradId = useId();
  const width = 96;
  const height = 20;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - 2 - ((v - min) / range) * (height - 4);
      return `${x},${y}`;
    })
    .join(" ");

  const areaPoints = `0,${height} ${points} ${width},${height}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} className="overflow-visible" aria-hidden="true">
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="var(--status-executing)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--status-executing)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill={`url(#${gradId})`} />
      <polyline points={points} fill="none" stroke="var(--status-executing)" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
