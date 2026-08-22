/**
 * anchor-spec.md §13.3 — searchable across the raw event log for all runs,
 * filterable by type, worker, epoch, and time range. LEASE_RENEWED is
 * excluded by default, since it is the highest-volume, lowest-signal event.
 */
"use client";

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { usePolling } from "@/hooks/usePolling";
import { api } from "@/lib/api";
import type { EventType, RunEvent } from "@/lib/types";
import { ScrollText, Search, Filter } from "lucide-react";

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
  const [olderItems, setOlderItems] = useState<RunEvent[]>([]);
  const [olderCursor, setOlderCursor] = useState<string | null>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);

  // A new filter scopes a different cursor sequence entirely — discard the
  // previously loaded older pages rather than mixing two filters' history.
  useEffect(() => {
    setOlderItems([]);
    setOlderCursor(null);
  }, [workerFilter, selectedType, runId]);

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

  // Older pages are fetched once, on demand, via the cursor the last page
  // reported — never re-polled, so "load older" results stay put under the
  // live-refreshing head of the list rather than being clobbered by it.
  const loadOlder = () => {
    const cursor = olderItems.length > 0 ? olderCursor : (globalEvents.data?.next_cursor ?? null);
    if (!cursor) return;
    setLoadingOlder(true);
    api
      .listEvents({
        worker_id: workerFilter || undefined,
        type: selectedType ? [selectedType] : undefined,
        limit: 100,
        cursor,
      })
      .then((res) => {
        setOlderItems((prev) => [...prev, ...res.items]);
        setOlderCursor(res.next_cursor);
      })
      .finally(() => setLoadingOlder(false));
  };

  const rawItems: RunEvent[] = runId
    ? (scopedEvents.data?.items ?? [])
    : [...(globalEvents.data?.items ?? []), ...olderItems];
  const hasMore = !runId && (olderItems.length > 0 ? olderCursor !== null : globalEvents.data?.next_cursor != null);

  const rows = rawItems.filter((e) => {
    if (!showRenewals && e.type === "LEASE_RENEWED") return false;
    if (selectedType && e.type !== selectedType) return false;
    if (workerFilter && e.worker_id && !e.worker_id.includes(workerFilter)) return false;
    return true;
  });

  return (
    <div data-testid="logs-page" className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Event Audit Trail Logs</h1>
            <span className="rounded-full bg-strand-gold/10 px-2.5 py-0.5 font-mono text-[10px] text-strand-gold border border-strand-gold/30">
              {rows.length} EVENTS
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono">
            Immutable append-only audit stream across all workflows and workers
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-white/[0.08] bg-black/40 p-4 backdrop-blur-2xl">
        <input
          value={runId}
          onChange={(e) => setRunId(e.target.value.trim())}
          placeholder="filter by run id (e.g. 1)"
          className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 font-mono text-xs text-white placeholder:text-zinc-500 focus:border-strand-gold focus:outline-none w-48 transition-all"
        />

        <input
          value={workerFilter}
          onChange={(e) => setWorkerFilter(e.target.value.trim())}
          placeholder="filter by worker (e.g. worker-1)"
          className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 font-mono text-xs text-white placeholder:text-zinc-500 focus:border-strand-gold focus:outline-none w-48 transition-all"
        />

        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="rounded-xl border border-white/[0.08] bg-zinc-900 px-3 py-1.5 font-mono text-xs text-white focus:border-strand-gold focus:outline-none"
        >
          <option value="">all event types</option>
          {ALL_EVENT_TYPES.filter((t) => t !== "LEASE_RENEWED" || showRenewals).map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-xs font-mono text-zinc-400 cursor-pointer select-none ml-2">
          <input
            type="checkbox"
            checked={showRenewals}
            onChange={(e) => setShowRenewals(e.target.checked)}
            className="rounded border-white/[0.1] accent-strand-gold"
          />
          <span>show lease renewals</span>
        </label>
      </div>

      {rows.length === 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-12 text-center text-sm font-mono text-zinc-500 backdrop-blur-2xl">
          no events found matching criteria
        </div>
      )}

      {rows.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-[11px]">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.02] text-zinc-400 uppercase tracking-wider">
                  <th className="py-3 pl-4 pr-3 font-medium">seq</th>
                  <th className="py-3 pr-3 font-medium">run</th>
                  <th className="py-3 pr-3 font-medium">event type</th>
                  <th className="py-3 pr-3 font-medium">worker</th>
                  <th className="py-3 pr-3 font-medium">epoch</th>
                  <th className="py-3 pr-3 font-medium">step</th>
                  <th className="py-3 pr-4 font-medium">timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {rows.map((e) => (
                  <tr key={`${e.run_id}-${e.seq}`} className="hover:bg-white/[0.02] transition-colors">
                    <td className="figures-tabular py-2.5 pl-4 pr-3 text-zinc-500">{e.seq}</td>
                    <td className="py-2.5 pr-3 font-bold">
                      <Link to={`/runs/${e.run_id}`} className="text-strand-gold hover:underline">
                        run_{e.run_id}
                      </Link>
                    </td>
                    <td className="py-2.5 pr-3 font-semibold text-white">{e.type}</td>
                    <td className="py-2.5 pr-3 text-zinc-300">{e.worker_id ?? "—"}</td>
                    <td className="figures-tabular py-2.5 pr-3 text-zinc-400">{e.epoch}</td>
                    <td className="figures-tabular py-2.5 pr-3 text-zinc-400">{e.step_index ?? "—"}</td>
                    <td className="py-2.5 pr-4 text-zinc-500 whitespace-nowrap">{e.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!runId && hasMore && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={loadOlder}
            disabled={loadingOlder}
            className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-2 text-xs font-mono text-zinc-300 hover:text-strand-gold hover:border-strand-gold/30 transition-all disabled:opacity-50"
          >
            {loadingOlder ? "loading…" : "load older events"}
          </button>
        </div>
      )}
    </div>
  );
}
