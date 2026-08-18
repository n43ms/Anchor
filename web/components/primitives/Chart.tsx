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

  return (
    <div className="rounded-md border border-gridline bg-surface-panel p-4" aria-labelledby={titleId}>
      <div className="flex items-center justify-between">
        <h3 id={titleId} className="text-sm text-ink-secondary">
          {title}
        </h3>
        <div className="flex gap-1 text-xs">
          <button
            type="button"
            onClick={() => setView("chart")}
            className={`rounded px-2 py-1 transition-colors duration-fast ${view === "chart" ? "bg-surface-page text-ink-primary" : "text-ink-muted"}`}
            aria-pressed={view === "chart"}
          >
            chart
          </button>
          <button
            type="button"
            onClick={() => setView("table")}
            className={`rounded px-2 py-1 transition-colors duration-fast ${view === "table" ? "bg-surface-page text-ink-primary" : "text-ink-muted"}`}
            aria-pressed={view === "table"}
          >
            table
          </button>
        </div>
      </div>

      {view === "chart" ? (
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} className="mt-3" role="img">
          {series.map((s) => {
            const pts = s.points
              .map((p, i) => {
                const x = (i / Math.max(s.points.length - 1, 1)) * width;
                const y = height - (p.y / maxY) * height;
                return `${x},${y}`;
              })
              .join(" ");
            return <polyline key={s.name} points={pts} fill="none" stroke={s.color} strokeWidth={2} />;
          })}
        </svg>
      ) : (
        <table className="mt-3 w-full text-left text-xs">
          <thead>
            <tr className="text-ink-muted">
              <th className="pr-4">x</th>
              {series.map((s) => (
                <th key={s.name} className="pr-4">
                  {s.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="figures-tabular">
            {(series[0]?.points ?? []).map((p, i) => (
              <tr key={String(p.x) + i}>
                <td className="pr-4 text-ink-secondary">{p.x}</td>
                {series.map((s) => (
                  <td key={s.name} className="pr-4 text-ink-primary">
                    {s.points[i]?.y ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {series.length >= 2 && (
        <ul className="mt-3 flex gap-4 text-xs text-ink-secondary">
          {series.map((s) => (
            <li key={s.name} className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} aria-hidden="true" />
              {s.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
