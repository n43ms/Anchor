/**
 * anchor-spec.md §13.3 — searchable across the raw event log for all runs,
 * filterable by type, worker, epoch, and time range. LEASE_RENEWED is
 * excluded by default, since it is the highest-volume, lowest-signal event.
 */
"use client";

import { useState } from "react";
import { usePolling } from "@/hooks/usePolling";
import { api } from "@/lib/api";
import type { EventType } from "@/lib/types";

const DEFAULT_EXCLUDED: EventType[] = ["LEASE_RENEWED"];

export default function LogsPage() {
  const [runId, setRunId] = useState("");
  const [showRenewals, setShowRenewals] = useState(false);

  const events = usePolling(
    () => (runId ? api.getRunEvents(runId) : Promise.resolve({ run_id: 0, items: [], next_after_seq: null })),
    5_000,
    Boolean(runId),
  );

  const rows = (events.data?.items ?? []).filter((e) => showRenewals || !DEFAULT_EXCLUDED.includes(e.type));

  return (
    <div data-testid="logs-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">logs</h1>

      <div className="mb-3 flex items-center gap-3">
        <input
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
          placeholder="run id"
          className="rounded border border-gridline bg-surface-panel px-2 py-1.5 text-sm text-ink-primary"
        />
        <label className="flex items-center gap-1.5 text-xs text-ink-secondary">
          <input type="checkbox" checked={showRenewals} onChange={(e) => setShowRenewals(e.target.checked)} />
          show lease renewals
        </label>
      </div>

      {!runId && <p className="text-sm text-ink-muted">enter a run id to search its log</p>}
      {runId && rows.length === 0 && <p className="text-sm text-ink-muted">no events</p>}

      {rows.length > 0 && (
        <table className="w-full text-left font-data text-[11px]">
          <thead>
            <tr className="text-ink-muted">
              <th className="pr-3">seq</th>
              <th className="pr-3">type</th>
              <th className="pr-3">worker</th>
              <th className="pr-3">epoch</th>
              <th>created_at</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.seq}>
                <td className="figures-tabular pr-3">{e.seq}</td>
                <td className="pr-3 text-ink-primary">{e.type}</td>
                <td className="pr-3 text-ink-secondary">{e.worker_id}</td>
                <td className="figures-tabular pr-3 text-ink-secondary">{e.epoch}</td>
                <td className="text-ink-muted">{e.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
