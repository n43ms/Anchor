/**
 * anchor-spec.md §13.3 — the primary list view. Each row carries the
 * compact thread strand (§24.3) as a visual summary; the owning-worker
 * column stays because the compact strand cannot identify which workers
 * touched a run (§24.8).
 */
"use client";

import { useState } from "react";
import { Link } from "react-router-dom";
import { useRunsList } from "@/hooks/useRunsList";
import { StatusPill } from "@/components/primitives/StatusPill";
import { RunThread } from "@/components/run/RunThread";
import { api, ApiRequestError } from "@/lib/api";
import type { RunStatus } from "@/lib/types";
import { RotateCcw, Search, ArrowUpRight } from "lucide-react";

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
    <div data-testid="all-runs-page" className="space-y-5 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">All Runs</h1>
            <span className="rounded-full bg-strand-gold/10 px-2 py-0.5 font-mono text-[10px] text-strand-gold border border-strand-gold/30">
              {filteredItems.length} WORKFLOWS
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono">Durable execution histories and runtime threads across workers</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleResetDemo}
            className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.02] px-3.5 py-2 text-xs font-mono text-zinc-300 hover:text-white hover:border-white/[0.2] transition-all shadow-sm"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset Demo Runs</span>
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-400 font-mono backdrop-blur-xl">
          {actionMessage}
        </div>
      )}

      {/* Filter & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/[0.08] bg-black/40 p-3.5 backdrop-blur-2xl">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-mono text-zinc-500 mr-1">FILTER:</span>
          {FILTERS.map((status) => {
            const isOn = active.includes(status);
            return (
              <button
                key={status}
                type="button"
                onClick={() => setActive((prev) => (isOn ? prev.filter((s) => s !== status) : [...prev, status]))}
                className={`rounded-lg border px-2.5 py-1 text-xs font-mono transition-all duration-fast ${
                  isOn
                    ? "border-strand-gold/50 bg-strand-gold/20 text-strand-gold shadow-sm font-semibold"
                    : "border-white/[0.06] bg-white/[0.02] text-zinc-400 hover:text-white hover:bg-white/[0.04]"
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
              className="text-xs font-mono text-zinc-500 hover:text-white underline ml-1.5"
            >
              clear
            </button>
          )}
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="search runs or agents…"
            className="rounded-xl border border-white/[0.08] bg-white/[0.02] pl-8 pr-3 py-1.5 text-xs font-mono text-white placeholder:text-zinc-500 focus:border-strand-gold focus:outline-none w-64 transition-all"
          />
        </div>
      </div>

      {error && !data && <p className="text-sm text-rose-400 font-mono">could not load runs</p>}
      {!error && !data && <p className="text-sm text-zinc-500 font-mono">loading runs stream…</p>}
      {data && filteredItems.length === 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-12 text-center text-sm font-mono text-zinc-500 backdrop-blur-2xl">
          no runs match the current filter
        </div>
      )}

      {data && filteredItems.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-2xl">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-xs font-mono text-zinc-400 uppercase tracking-wider">
                <th className="py-3 pl-4 pr-3 font-medium">Run ID</th>
                <th className="py-3 pr-3 font-medium">Agent</th>
                <th className="py-3 pr-3 font-medium">Status</th>
                <th className="py-3 pr-3 font-medium">Owner</th>
                <th className="py-3 pr-3 font-medium">Elapsed</th>
                <th className="py-3 pr-4 font-medium w-48">Runtime Thread</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredItems.map((run) => (
                <tr key={run.id} className="transition-colors hover:bg-white/[0.03] group">
                  <td className="py-3 pl-4 pr-3 font-mono text-xs font-bold">
                    <Link to={`/runs/${run.id}`} className="text-white group-hover:text-strand-gold transition-colors inline-flex items-center gap-1">
                      <span>{run.display_id ?? `run_${run.id}`}</span>
                      <ArrowUpRight className="h-3 w-3 text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </Link>
                  </td>
                  <td className="py-3 pr-3 text-xs text-zinc-300 font-medium">{run.agent_type}</td>
                  <td className="py-3 pr-3">
                    <StatusPill status={run.status} />
                  </td>
                  <td className="py-3 pr-3 font-mono text-xs text-zinc-400">
                    {run.owner_worker_id ? (
                      <span className="rounded bg-white/[0.04] px-2 py-0.5 text-zinc-200 border border-white/[0.06]">
                        {run.owner_worker_id}
                      </span>
                    ) : (
                      <span className="text-zinc-600">—</span>
                    )}
                  </td>
                  <td className="figures-tabular py-3 pr-3 font-mono text-xs text-zinc-400">
                    {Math.round(run.elapsed_ms / 1000)}s
                  </td>
                  <td className="py-3 pr-4 w-48">
                    <RunThread segments={run.segments} compact />
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
