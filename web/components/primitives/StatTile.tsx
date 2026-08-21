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

  const badgeTheme =
    badge === "degraded"
      ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
      : badge === "executing"
        ? "bg-indigo-500/15 text-indigo-300 border-indigo-500/30"
        : badge === "idle"
          ? "bg-zinc-500/15 text-zinc-400 border-zinc-500/30"
          : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";

  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border border-white/[0.08] bg-black/40 p-4 sm:p-5 backdrop-blur-2xl transition-all duration-base hover:border-white/[0.2] hover:bg-white/[0.02] shadow-sm ${
        emphasize ? "ring-1 ring-strand-gold/40 border-strand-gold/30" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2.5">
        <div className="min-w-0 flex-1 text-xs font-mono font-medium text-zinc-400 uppercase tracking-wider leading-snug">
          {label}
        </div>
        {badge && (
          <span
            className={`shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[9.5px] font-mono font-semibold border ${badgeTheme}`}
          >
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
  const pathId = useId();
  const width = 64;
  const height = 14;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
      aria-hidden="true"
    >
      <polyline
        id={pathId}
        points={points}
        fill="none"
        stroke="var(--strand-gold)"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
