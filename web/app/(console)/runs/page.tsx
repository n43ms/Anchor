/**
 * anchor-spec.md §13.3 — the primary list view. Each row carries the
 * compact thread strand (§24.3) as a visual summary; the owning-worker
 * column stays because the compact strand cannot identify which workers
 * touched a run (§24.8).
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useRunsList } from "@/hooks/useRunsList";
import { StatusPill } from "@/components/primitives/StatusPill";
import { RunThread } from "@/components/run/RunThread";
import type { RunStatus } from "@/lib/types";

const FILTERS: RunStatus[] = ["pending", "running", "completed", "failed", "needs_review"];

export default function AllRunsPage() {
  const [active, setActive] = useState<RunStatus[]>([]);
  const { data, error } = useRunsList(active.length ? active : undefined);

  return (
    <div data-testid="all-runs-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">all runs</h1>

      <div className="mb-3 flex gap-2">
        {FILTERS.map((status) => {
          const isOn = active.includes(status);
          return (
            <button
              key={status}
              type="button"
              onClick={() => setActive((prev) => (isOn ? prev.filter((s) => s !== status) : [...prev, status]))}
              className={`rounded border px-2 py-1 text-xs transition-colors duration-fast ${
                isOn ? "border-ink-primary text-ink-primary" : "border-gridline text-ink-muted"
              }`}
              aria-pressed={isOn}
            >
              {status.replace("_", " ")}
            </button>
          );
        })}
      </div>

      {error && !data && <p className="text-sm text-status-critical">could not load runs</p>}
      {!error && !data && <p className="text-sm text-ink-muted">loading…</p>}
      {data && data.items.length === 0 && <p className="text-sm text-ink-muted">no runs match this filter</p>}

      {data && data.items.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs text-ink-muted">
              <th className="pb-2 pr-3">run</th>
              <th className="pb-2 pr-3">agent</th>
              <th className="pb-2 pr-3">status</th>
              <th className="pb-2 pr-3">owner</th>
              <th className="pb-2 pr-3">elapsed</th>
              <th className="pb-2">thread</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((run) => (
              <tr key={run.id} className="border-t border-gridline">
                <td className="py-2 pr-3 font-data text-ink-primary">
                  <Link href={`/runs/${run.id}`} className="hover:underline">
                    {run.display_id ?? `run_${run.id}`}
                  </Link>
                </td>
                <td className="py-2 pr-3 text-ink-secondary">{run.agent_type}</td>
                <td className="py-2 pr-3">
                  <StatusPill status={run.status} />
                </td>
                <td className="py-2 pr-3 font-data text-xs text-ink-secondary">{run.owner_worker_id ?? "—"}</td>
                <td className="figures-tabular py-2 pr-3 text-ink-secondary">{Math.round(run.elapsed_ms / 1000)}s</td>
                <td className="py-2">
                  <RunThread segments={run.segments} compact animate={run.status === "running"} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
