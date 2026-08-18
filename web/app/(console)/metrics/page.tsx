/**
 * anchor-spec.md §12, §22.5 — the metrics visualized rather than merely
 * tracked. No dual-axis chart: recovery latency and throughput get
 * separate charts.
 */
"use client";

import { useMetrics } from "@/hooks/useMetrics";
import { Chart } from "@/components/primitives/Chart";
import { StatTile } from "@/components/primitives/StatTile";

export default function MetricsPage() {
  const { data, error } = useMetrics();

  if (error && !data) return <p className="text-sm text-status-critical">could not load metrics</p>;
  if (!data) return <p className="text-sm text-ink-muted">loading…</p>;

  const stateSeries = data.run_state_distribution.map((b) => ({ x: b.bucket, y: Object.values(b.counts).reduce((a, c) => a + c, 0) }));
  const fencingSeries = (data.fencing_events_series ?? []).map((f) => ({ x: f.bucket, y: f.count }));
  const throughputSeries = (data.throughput_by_worker_count ?? []).map((t) => ({ x: t.worker_count, y: t.steps_per_second }));

  return (
    <div data-testid="metrics-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">metrics</h1>

      <div className="mb-4 grid grid-cols-4 gap-4">
        <StatTile label="runs total" value={data.runs_total ?? 0} />
        <StatTile label="steps total" value={data.steps_total ?? 0} />
        <StatTile label="stranded runs" value={data.stranded_runs ?? 0} />
        <StatTile label="fencing events" value={data.fencing_events_series?.reduce((a, b) => a + b.count, 0) ?? 0} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Chart title="run state distribution" series={[{ name: "runs", color: "var(--status-executing)", points: stateSeries }]} />
        <Chart title="fencing events over time" series={[{ name: "fencing", color: "var(--status-critical)", points: fencingSeries }]} />
        <Chart title="throughput vs worker count" series={[{ name: "measured", color: "var(--worker-1)", points: throughputSeries }]} />
      </div>

      {data.dead_letter_reasons && data.dead_letter_reasons.length > 0 && (
        <div className="mt-4">
          <h2 className="mb-2 text-sm text-ink-secondary">dead-letter reasons</h2>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-ink-muted">
                <th className="pb-2 pr-3">error type</th>
                <th className="pb-2">count</th>
              </tr>
            </thead>
            <tbody>
              {data.dead_letter_reasons.map((r) => (
                <tr key={r.error_type} className="border-t border-gridline">
                  <td className="py-1.5 pr-3 text-ink-primary">{r.error_type}</td>
                  <td className="figures-tabular py-1.5 text-ink-secondary">{r.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
