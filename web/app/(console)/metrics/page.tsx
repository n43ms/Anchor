import { useState } from "react";
import { useMetrics } from "@/hooks/useMetrics";
import { Chart } from "@/components/primitives/Chart";
import { StatTile } from "@/components/primitives/StatTile";
import { BarChart3 } from "lucide-react";

const WINDOWS = ["1h", "24h", "7d", "30d"] as const;

export default function MetricsPage() {
  const [window, setWindow] = useState<"1h" | "24h" | "7d" | "30d">("24h");
  const { data, error } = useMetrics(window);

  if (error && !data) return <p className="text-sm font-mono text-rose-400">could not load metrics</p>;
  if (!data) return <p className="text-sm font-mono text-zinc-500">loading telemetry metrics…</p>;

  const stateSeries = data.run_state_distribution.map((b) => ({ x: b.bucket, y: Object.values(b.counts).reduce((a, c) => a + c, 0) }));
  const fencingSeries = (data.fencing_events_series ?? []).map((f) => ({ x: f.bucket, y: f.count }));
  const throughputSeries = (data.throughput_by_worker_count ?? []).map((t) => ({ x: t.worker_count, y: t.steps_per_second }));

  return (
    <div data-testid="metrics-page" className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Aggregated Telemetry Metrics</h1>
            <span className="rounded-full bg-strand-gold/10 px-2.5 py-0.5 font-mono text-[10px] text-strand-gold border border-strand-gold/30">
              WINDOW: {window}
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono">
            Cluster step rate, run state distribution, and fencing telemetry
          </p>
        </div>
        <div className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.02] p-1 backdrop-blur-xl">
          {WINDOWS.map((w) => (
            <button
              key={w}
              type="button"
              onClick={() => setWindow(w)}
              className={`rounded-lg px-3 py-1 text-xs font-mono font-medium transition-all ${
                window === w
                  ? "bg-strand-gold/20 text-strand-gold border border-strand-gold/40 shadow-sm"
                  : "text-zinc-400 hover:text-white hover:bg-white/[0.04]"
              }`}
            >
              {w}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="runs total" value={data.runs_total ?? 0} />
        <StatTile label="steps total" value={data.steps_total ?? 0} />
        <StatTile label="stranded runs" value={data.stranded_runs ?? 0} />
        <StatTile label="fencing events" value={data.fencing_events_series?.reduce((a, b) => a + b.count, 0) ?? 0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Chart title="run state distribution" series={[{ name: "runs", color: "var(--status-executing)", points: stateSeries }]} />
        <Chart title="fencing events over time" series={[{ name: "fencing", color: "var(--status-critical)", points: fencingSeries }]} />
        <Chart title="throughput vs worker count" series={[{ name: "measured", color: "var(--worker-1)", points: throughputSeries }]} />
      </div>

      {data.dead_letter_reasons && data.dead_letter_reasons.length > 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl space-y-3">
          <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">Dead-Letter Error Reasons</h2>
          <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.02]">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.03] text-zinc-400 uppercase tracking-wider">
                  <th className="py-2.5 pl-4 pr-3 font-medium">Error Type</th>
                  <th className="py-2.5 pr-4 font-medium text-right">Count</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {data.dead_letter_reasons.map((r) => (
                  <tr key={r.error_type} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-2.5 pl-4 pr-3 text-white">{r.error_type}</td>
                    <td className="figures-tabular py-2.5 pr-4 text-right text-zinc-300 font-bold">{r.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
