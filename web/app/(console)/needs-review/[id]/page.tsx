/**
 * anchor-spec.md §13.3 — full log, failing step highlighted, the specific
 * ambiguous tool call with its available reconciliation options and a
 * resolution action.
 */
"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useRunStream } from "@/hooks/useRunStream";
import { RawEventLog } from "@/components/run/RawEventLog";
import { api, ApiRequestError } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

export default function NeedsReviewDetailPage() {
  const params = useParams<{ id: string }>();
  const { timeline } = useRunStream(params.id);
  const events = usePolling(() => api.getRunEvents(params.id), 5_000);
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [resolved, setResolved] = useState(false);

  if (!timeline) return <p className="text-sm text-ink-muted">loading…</p>;

  const resolve = (resolution: "mark_executed" | "mark_not_executed" | "retry") => {
    setResolveError(null);
    api
      .resolveRun(params.id, resolution)
      .then(() => setResolved(true))
      .catch((err: unknown) => setResolveError(err instanceof ApiRequestError ? err.message : "resolve failed"));
  };

  const nr = timeline.needs_review;

  return (
    <div data-testid="needs-review-detail">
      <h1 className="mb-2 font-ui text-base text-ink-primary">{timeline.display_id ?? `run_${timeline.id}`}</h1>

      {nr ? (
        <div className="mb-4 rounded-md border border-status-warning bg-status-warning/10 p-4">
          <p className="text-sm text-ink-primary">
            step {nr.step_index} · <span className="font-data">{nr.tool_name}</span> · declared policy: {nr.declared_policy}
          </p>
          <p className="mt-1 font-data text-xs text-ink-secondary">key: {nr.idempotency_key}</p>
          <div className="mt-3 flex gap-2">
            {nr.available_resolutions.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => resolve(r)}
                disabled={resolved}
                className="rounded border border-gridline px-3 py-1.5 text-xs text-ink-primary transition-colors duration-fast hover:border-status-warning disabled:opacity-40"
              >
                {r.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          {resolveError && <p className="mt-2 text-xs text-status-critical">{resolveError}</p>}
          {resolved && <p className="mt-2 text-xs text-status-good">resolution recorded</p>}
        </div>
      ) : (
        <p className="mb-4 text-sm text-ink-muted">this run is not currently in the uncertainty window</p>
      )}

      <h2 className="mb-2 text-sm text-ink-secondary">full log</h2>
      <RawEventLog events={events.data?.items ?? []} />
    </div>
  );
}
