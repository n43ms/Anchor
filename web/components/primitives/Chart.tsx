/**
 * anchor-spec.md §22.5. One hero figure per view lives in StatTile, not here.
 * This primitive enforces, structurally, the rules that are easy to forget:
 * no dual y-axis (there is only ever one y-scale), a table view for every
 * chart, and a legend only once there are two or more series.
 */
"use client";

import { useId, useState } from "react";

export interface ChartSeries {
  name: string;
  color: string;
  points: Array<{ x: string | number; y: number }>;
}

export function Chart({ title, series, height = 160 }: { title: string; series: ChartSeries[]; height?: number }) {
  const [view, setView] = useState<"chart" | "table">("chart");
  const titleId = useId();
  const width = 480;
  const allY = series.flatMap((s) => s.points.map((p) => p.y));
  const maxY = Math.max(...allY, 1);
  const isEmpty = series.length === 0 || series.every((s) => s.points.length === 0);

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl shadow-sm transition-all hover:border-white/[0.15]" aria-labelledby={titleId}>
      <div className="flex items-center justify-between">
        <h3 id={titleId} className="font-mono text-xs uppercase tracking-wider text-zinc-400 font-semibold">
          {title}
        </h3>
        <div className="flex gap-1.5 text-xs">
          <button
            type="button"
            onClick={() => setView("chart")}
            className={`rounded-lg px-2.5 py-1 font-mono text-[11px] transition-all duration-fast ${view === "chart" ? "bg-white/[0.08] text-white border border-white/10 shadow-sm" : "text-zinc-400 hover:text-white"}`}
            aria-pressed={view === "chart"}
          >
            chart
          </button>
          <button
            type="button"
            onClick={() => setView("table")}
            className={`rounded-lg px-2.5 py-1 font-mono text-[11px] transition-all duration-fast ${view === "table" ? "bg-white/[0.08] text-white border border-white/10 shadow-sm" : "text-zinc-400 hover:text-white"}`}
            aria-pressed={view === "table"}
          >
            table
          </button>
        </div>
      </div>

      {isEmpty ? (
        <div
          className="mt-3 flex items-center justify-center rounded-xl border border-dashed border-white/[0.08] bg-white/[0.02] text-xs font-mono text-zinc-500"
          style={{ height }}
          data-testid="chart-empty-state"
        >
          no telemetry recorded in this window yet
        </div>
      ) : view === "chart" ? (
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} className="mt-3 overflow-visible" role="img">
          {series.map((s) => {
            const pts = s.points
              .map((p, i) => {
                const x = (i / Math.max(s.points.length - 1, 1)) * width;
                const y = height - (p.y / maxY) * height;
                return `${x},${y}`;
              })
              .join(" ");
            return <polyline key={s.name} points={pts} fill="none" stroke={s.color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />;
          })}
        </svg>
      ) : (
        <table className="mt-3 w-full text-left text-xs font-mono">
          <thead>
            <tr className="text-zinc-500 border-b border-white/[0.04] pb-1">
              <th className="pr-4 py-1">x</th>
              {series.map((s) => (
                <th key={s.name} className="pr-4 py-1">
                  {s.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="figures-tabular">
            {(series[0]?.points ?? []).map((p, i) => (
              <tr key={String(p.x) + i} className="border-b border-white/[0.02] hover:bg-white/[0.02]">
                <td className="pr-4 py-1 text-zinc-400">{p.x}</td>
                {series.map((s) => (
                  <td key={s.name} className="pr-4 py-1 text-zinc-200">
                    {s.points[i]?.y ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {series.length >= 2 && (
        <ul className="mt-3 flex gap-4 text-xs font-mono text-zinc-400">
          {series.map((s) => (
            <li key={s.name} className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full shadow-sm" style={{ backgroundColor: s.color }} aria-hidden="true" />
              {s.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
