/**
 * anchor-spec.md §13.3 — full log, failing step highlighted, the specific
 * ambiguous tool call with its available reconciliation options and a
 * resolution action.
 */
import { useParams, Link } from "react-router-dom";
import { useState } from "react";
import { useRunStream } from "@/hooks/useRunStream";
import { RawEventLog } from "@/components/run/RawEventLog";
import { api, ApiRequestError } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

export default function NeedsReviewDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id ?? "";
  const { timeline } = useRunStream(runId);
  const events = usePolling(() => (runId ? api.getRunEvents(runId) : Promise.resolve({ run_id: 0, items: [], next_after_seq: null })), 4_000, Boolean(runId));
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [resolved, setResolved] = useState<string | null>(null);

  if (!timeline) {
    return (
      <div className="space-y-4" data-testid="needs-review-detail">
        <p className="text-sm text-ink-muted">loading run details…</p>
      </div>
    );
  }

  const resolve = (resolution: "mark_executed" | "mark_not_executed" | "retry") => {
    setResolveError(null);
    if (!runId) return;
    api
      .resolveRun(runId, resolution)
      .then(() => setResolved(resolution))
      .catch((err: unknown) => setResolveError(err instanceof ApiRequestError ? err.message : "resolve failed"));
  };

  const nr = timeline.needs_review;

  return (
    <div data-testid="needs-review-detail" className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-ink-muted">
          <Link to="/needs-review" className="hover:text-ink-primary transition-colors">needs review</Link>
          <span>/</span>
          <span className="font-data text-ink-primary">{timeline.display_id ?? `run_${timeline.id}`}</span>
        </div>
        <Link to={`/runs/${timeline.id}`} className="rounded border border-gridline bg-surface-panel px-2.5 py-1 text-xs text-ink-secondary hover:text-ink-primary">
          view run timeline ↗
        </Link>
      </div>

      <div className="rounded-lg border border-gridline bg-surface-panel p-5">
        <h1 className="font-ui text-base font-bold text-ink-primary">{timeline.display_id ?? `run_${timeline.id}`} · {timeline.agent_type}</h1>
        <p className="mt-1 text-xs text-ink-secondary">
          Run halted at step {timeline.step_count} due to a worker crash during an unconfirmed side-effect window.
        </p>

        {nr ? (
          <div className="mt-4 rounded-md border border-status-warning bg-status-warning/10 p-4">
            <div className="space-y-1 text-xs text-ink-secondary">
              <div>
                step: <strong className="font-data text-ink-primary">{nr.step_index}</strong> · tool:{" "}
                <strong className="font-data text-ink-primary">{nr.tool_name}</strong>
              </div>
              <div>declared policy: <span className="font-medium text-ink-primary">{nr.declared_policy}</span></div>
              <div className="font-data text-ink-muted">idempotency key: {nr.idempotency_key}</div>
            </div>

            <div className="mt-4">
              <div className="text-xs font-semibold text-ink-primary mb-2">Select Operator Resolution:</div>
              <div className="flex flex-wrap gap-2">
                {nr.available_resolutions.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => resolve(r)}
                    disabled={resolved !== null}
                    className="rounded border border-status-warning bg-surface-panel px-3 py-1.5 text-xs font-medium text-ink-primary transition-colors duration-fast hover:bg-status-warning/20 disabled:opacity-40"
                  >
                    {r.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>

            {resolveError && <p className="mt-3 text-xs text-status-critical">{resolveError}</p>}
            {resolved && (
              <p className="mt-3 text-xs text-status-good">
                resolution recorded: <strong>{resolved.replace(/_/g, " ")}</strong>. Run is now eligible for worker reclamation.
              </p>
            )}
          </div>
        ) : (
          <div className="mt-4 rounded-md border border-gridline bg-surface-page p-4 text-xs text-ink-muted">
            this run is not currently in the uncertainty window
          </div>
        )}
      </div>

      <div className="rounded-lg border border-gridline bg-surface-panel p-5">
        <h2 className="mb-3 font-ui text-sm font-bold text-ink-primary">full event log</h2>
        <RawEventLog events={events.data?.items ?? []} />
      </div>
    </div>
  );
}
