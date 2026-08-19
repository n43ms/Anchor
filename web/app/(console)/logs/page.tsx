/**
 * anchor-spec.md §13.3 — searchable across the raw event log for all runs,
 * filterable by type, worker, epoch, and time range. LEASE_RENEWED is
 * excluded by default, since it is the highest-volume, lowest-signal event.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { usePolling } from "@/hooks/usePolling";
import { api } from "@/lib/api";
import type { EventType, RunEvent } from "@/lib/types";

const ALL_EVENT_TYPES: EventType[] = [
  "RUN_SUBMITTED",
  "RUN_CLAIMED",
  "REPLAY_COMPLETED",
  "STEP_STARTED",
  "LLM_CALLED",
  "TOOL_INTENT",
  "TOOL_RESULT",
  "NONDET_RECORDED",
  "STEP_COMPLETED",
  "STEP_SKIPPED_ON_REPLAY",
  "STEP_FAILED",
  "LEASE_RENEWED",
  "WORKER_FENCED",
  "RUN_COMPLETED",
  "RUN_FAILED",
  "RUN_CANCELLED",
  "RUN_NEEDS_REVIEW",
];

export default function LogsPage() {
  const [runId, setRunId] = useState("");
  const [workerFilter, setWorkerFilter] = useState("");
  const [showRenewals, setShowRenewals] = useState(false);
  const [selectedType, setSelectedType] = useState<string>("");

  const globalEvents = usePolling(
    () =>
      api.listEvents({
        worker_id: workerFilter || undefined,
        type: selectedType ? [selectedType] : undefined,
        limit: 100,
      }),
    4_000,
    !runId,
  );

  const scopedEvents = usePolling(
    () => (runId ? api.getRunEvents(runId) : Promise.resolve({ run_id: 0, items: [], next_after_seq: null })),
    4_000,
    Boolean(runId),
  );

  const rawItems: RunEvent[] = runId ? (scopedEvents.data?.items ?? []) : (globalEvents.data?.items ?? []);

  const rows = rawItems.filter((e) => {
    if (!showRenewals && e.type === "LEASE_RENEWED") return false;
    if (selectedType && e.type !== selectedType) return false;
    if (workerFilter && e.worker_id && !e.worker_id.includes(workerFilter)) return false;
    return true;
  });

  return (
    <div data-testid="logs-page" className="space-y-4">
      <div>
        <h1 className="font-ui text-base font-bold text-ink-primary">event logs</h1>
        <p className="text-xs text-ink-secondary">
          immutable append-only audit trail across all runs and workers
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-gridline bg-surface-panel p-3">
        <input
          value={runId}
          onChange={(e) => setRunId(e.target.value.trim())}
          placeholder="filter by run id (e.g. 1)"
          className="rounded border border-gridline bg-surface-page px-2.5 py-1.5 font-data text-xs text-ink-primary placeholder:text-ink-muted focus:border-strand-gold focus:outline-none"
        />

        <input
          value={workerFilter}
          onChange={(e) => setWorkerFilter(e.target.value.trim())}
          placeholder="filter by worker (e.g. worker-a#1)"
          className="rounded border border-gridline bg-surface-page px-2.5 py-1.5 font-data text-xs text-ink-primary placeholder:text-ink-muted focus:border-strand-gold focus:outline-none"
        />

        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="rounded border border-gridline bg-surface-page px-2.5 py-1.5 text-xs text-ink-primary focus:border-strand-gold focus:outline-none"
        >
          <option value="">all event types</option>
          {ALL_EVENT_TYPES.filter((t) => t !== "LEASE_RENEWED" || showRenewals).map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-1.5 text-xs text-ink-secondary cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showRenewals}
            onChange={(e) => setShowRenewals(e.target.checked)}
            className="rounded border-gridline accent-strand-gold"
          />
          <span>show lease renewals</span>
        </label>
      </div>

      {rows.length === 0 && (
        <div className="rounded-lg border border-gridline bg-surface-panel p-8 text-center text-sm text-ink-muted">
          no events found matching criteria
        </div>
      )}

      {rows.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gridline bg-surface-panel">
          <div className="overflow-x-auto">
            <table className="w-full text-left font-data text-[11px]">
              <thead>
                <tr className="border-b border-gridline bg-surface-page/60 text-ink-muted">
                  <th className="py-2 pl-4 pr-3 font-medium">seq</th>
                  <th className="py-2 pr-3 font-medium">run</th>
                  <th className="py-2 pr-3 font-medium">event type</th>
                  <th className="py-2 pr-3 font-medium">worker</th>
                  <th className="py-2 pr-3 font-medium">epoch</th>
                  <th className="py-2 pr-3 font-medium">step</th>
                  <th className="py-2 pr-4 font-medium">timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gridline">
                {rows.map((e) => (
                  <tr key={`${e.run_id}-${e.seq}`} className="hover:bg-surface-page/40 transition-colors">
                    <td className="figures-tabular py-2 pl-4 pr-3 text-ink-secondary">{e.seq}</td>
                    <td className="py-2 pr-3">
                      <Link to={`/runs/${e.run_id}`} className="text-strand-gold hover:underline">
                        run_{e.run_id}
                      </Link>
                    </td>
                    <td className="py-2 pr-3 font-semibold text-ink-primary">{e.type}</td>
                    <td className="py-2 pr-3 text-ink-secondary">{e.worker_id ?? "—"}</td>
                    <td className="figures-tabular py-2 pr-3 text-ink-secondary">{e.epoch}</td>
                    <td className="figures-tabular py-2 pr-3 text-ink-secondary">{e.step_index ?? "—"}</td>
                    <td className="py-2 pr-4 text-ink-muted whitespace-nowrap">{e.created_at}</td>
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
