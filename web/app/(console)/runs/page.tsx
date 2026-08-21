/**
 * anchor-spec.md §13.3 — the primary list view. Each row carries the
 * compact thread strand (§24.3) as a visual summary; the owning-worker
 * column stays because the compact strand cannot identify which workers
 * touched a run (§24.8).
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { useRunsList } from "@/hooks/useRunsList";
import { StatusPill } from "@/components/primitives/StatusPill";
import { RunThread } from "@/components/run/RunThread";
import { api, ApiRequestError } from "@/lib/api";
import type { RunStatus } from "@/lib/types";

const FILTERS: RunStatus[] = ["pending", "running", "completed", "failed", "needs_review"];

export default function AllRunsPage() {
  const [active, setActive] = useState<RunStatus[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const { data, error, refresh } = useRunsList(active.length ? active : undefined);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const handleResetDemo = () => {
    setActionMessage(null);
    api
      .resetDemoRuns()
      .then((res) => {
        setActionMessage(`Reset demo runs: ${res.runs_deleted} deleted`);
        refresh();
      })
      .catch((err: unknown) => {
        setActionMessage(err instanceof ApiRequestError ? err.message : "reset failed");
      });
  };

  const filteredItems = (data?.items ?? []).filter((run) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const displayId = (run.display_id ?? `run_${run.id}`).toLowerCase();
    const agent = run.agent_type.toLowerCase();
    const worker = (run.owner_worker_id ?? "").toLowerCase();
    return displayId.includes(query) || agent.includes(query) || worker.includes(query);
  });

  return (
    <div data-testid="all-runs-page" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-ui text-base font-bold text-ink-primary">all runs</h1>
          <p className="text-xs text-ink-secondary">durable execution histories across workers</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleResetDemo}
            className="rounded border border-gridline bg-surface-panel px-3 py-1 text-xs text-ink-secondary hover:text-ink-primary hover:border-strand-gold/40 transition-colors shadow-sm"
          >
            reset demo runs
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="rounded-md border border-status-warning/40 bg-status-warning/10 px-3.5 py-2 text-xs text-status-warning">
          {actionMessage}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-ink-muted">filter:</span>
          {FILTERS.map((status) => {
            const isOn = active.includes(status);
            return (
              <button
                key={status}
                type="button"
                onClick={() => setActive((prev) => (isOn ? prev.filter((s) => s !== status) : [...prev, status]))}
                className={`rounded border px-2.5 py-1 text-xs font-medium transition-all duration-fast ${
                  isOn
                    ? "border-strand-gold bg-strand-gold/15 text-strand-gold shadow-sm"
                    : "border-gridline bg-surface-panel text-ink-secondary hover:text-ink-primary hover:border-baseline"
                }`}
                aria-pressed={isOn}
              >
                {status.replace("_", " ")}
              </button>
            );
          })}
          {active.length > 0 && (
            <button
              type="button"
              onClick={() => setActive([])}
              className="text-xs text-ink-muted hover:text-ink-primary underline ml-1"
            >
              clear
            </button>
          )}
        </div>

        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="search runs or agents…"
          className="rounded border border-gridline bg-surface-panel px-3 py-1 text-xs font-data text-ink-primary placeholder:text-ink-muted focus:border-strand-gold focus:outline-none w-56 transition-colors"
        />
      </div>

      {error && !data && <p className="text-sm text-status-critical">could not load runs</p>}
      {!error && !data && <p className="text-sm text-ink-muted">loading…</p>}
      {data && filteredItems.length === 0 && (
        <div className="rounded-lg border border-gridline bg-surface-panel p-8 text-center text-sm text-ink-muted">
          no runs match the current filter
        </div>
      )}

      {data && filteredItems.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gridline bg-surface-panel">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gridline bg-surface-page/60 text-xs text-ink-muted">
                <th className="py-2.5 pl-4 pr-3 font-medium">run</th>
                <th className="py-2.5 pr-3 font-medium">agent</th>
                <th className="py-2.5 pr-3 font-medium">status</th>
                <th className="py-2.5 pr-3 font-medium">owner</th>
                <th className="py-2.5 pr-3 font-medium">elapsed</th>
                <th className="py-2.5 pr-4 font-medium">thread summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gridline">
              {filteredItems.map((run) => (
                <tr key={run.id} className="transition-colors hover:bg-surface-page/40">
                  <td className="py-3 pl-4 pr-3 font-data text-xs">
                    <Link to={`/runs/${run.id}`} className="font-bold text-ink-primary hover:text-strand-gold transition-colors">
                      {run.display_id ?? `run_${run.id}`}
                    </Link>
                  </td>
                  <td className="py-3 pr-3 text-xs text-ink-secondary">{run.agent_type}</td>
                  <td className="py-3 pr-3">
                    <StatusPill status={run.status} />
                  </td>
                  <td className="py-3 pr-3 font-data text-xs text-ink-secondary">{run.owner_worker_id ?? "—"}</td>
                  <td className="figures-tabular py-3 pr-3 font-data text-xs text-ink-secondary">
                    {Math.round(run.elapsed_ms / 1000)}s
                  </td>
                  <td className="py-3 pr-4 w-44">
                    <RunThread segments={run.segments} compact animate={run.status === "running"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
