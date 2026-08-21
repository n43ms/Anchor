import { useParams, Link } from "react-router-dom";
import { useState } from "react";
import { useRunStream } from "@/hooks/useRunStream";
import { usePolling } from "@/hooks/usePolling";
import { RunDetail } from "@/components/run/RunDetail";
import { TimelineTrack } from "@/components/run/TimelineTrack";
import { RawEventLog } from "@/components/run/RawEventLog";
import { api, ApiRequestError } from "@/lib/api";

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id ?? "";
  const { timeline, connected, stale } = useRunStream(runId);
  const events = usePolling(() => (runId ? api.getRunEvents(runId) : Promise.resolve({ run_id: 0, items: [], next_after_seq: null })), 4_000, Boolean(runId));
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [showRawEvents, setShowRawEvents] = useState(false);

  const handleKill = (workerId: string) => {
    setActionError(null);
    setActionSuccess(null);
    api.killWorker(workerId).then(() => {
      setActionSuccess(`Kill command issued to ${workerId}`);
    }).catch((err: unknown) => {
      setActionError(err instanceof ApiRequestError ? err.message : "kill request failed");
    });
  };

  const handleCancel = () => {
    if (!runId) return;
    setActionError(null);
    setActionSuccess(null);
    api.cancelRun(runId).then(() => {
      setActionSuccess("Cancellation requested");
    }).catch((err: unknown) => {
      setActionError(err instanceof ApiRequestError ? err.message : "cancel request failed");
    });
  };

  const handleResolve = (resolution: "mark_executed" | "mark_not_executed" | "retry") => {
    if (!runId) return;
    setActionError(null);
    setActionSuccess(null);
    api.resolveRun(runId, resolution).then(() => {
      setActionSuccess(`Resolution recorded: ${resolution.replace("_", " ")}`);
    }).catch((err: unknown) => {
      setActionError(err instanceof ApiRequestError ? err.message : "resolution failed");
    });
  };

  if (!timeline) {
    return (
      <div className="space-y-4" data-testid="run-detail-page">
        <p className="text-sm text-ink-muted" data-testid="run-detail-loading">loading run timeline…</p>
      </div>
    );
  }

  const isTerminal = ["completed", "failed", "cancelled"].includes(timeline.status);
  const isNeedsReview = timeline.status === "needs_review";

  return (
    <div data-testid="run-detail-page" className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-ink-muted">
          <Link to="/runs" className="hover:text-strand-gold transition-colors">runs</Link>
          <span>/</span>
          <span className="font-data text-ink-primary font-bold">{timeline.display_id ?? `run_${timeline.id}`}</span>
          <span className="ml-2 inline-flex items-center gap-1.5 rounded-full border border-gridline bg-surface-panel px-2 py-0.5 text-[10px] text-ink-secondary font-medium">
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-status-good animate-pulse" : "bg-status-warning"}`} />
            {connected ? "live stream" : "polling fallback"}
          </span>
        </div>
        {!isTerminal && (
          <button
            type="button"
            onClick={handleCancel}
            className="rounded border border-status-critical/30 bg-surface-panel px-3 py-1 text-xs text-status-critical hover:bg-status-critical/15 hover:border-status-critical transition-all shadow-sm"
          >
            cancel run
          </button>
        )}
      </div>

      {!connected && (
        <div className="rounded-md border border-status-warning/40 bg-status-warning/10 p-3 text-xs text-status-warning flex items-center gap-2" data-testid="run-detail-connection-warning">
          <span className="h-2 w-2 rounded-full bg-status-warning animate-ping" />
          <span>{stale ? "connection stale — showing last known state from store" : "connecting live stream…"}</span>
        </div>
      )}

      {actionError && (
        <div className="rounded-md border border-status-critical bg-status-critical/10 p-3 text-xs text-status-critical">
          {actionError}
        </div>
      )}

      {actionSuccess && (
        <div className="rounded-md border border-status-good bg-status-good/10 p-3 text-xs text-status-good">
          {actionSuccess}
        </div>
      )}

      {isNeedsReview && timeline.needs_review && (
        <div className="rounded-lg border border-status-warning bg-status-warning/10 p-4">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-ui text-sm font-bold text-ink-primary">Action Required: Ambiguous Step Execution</h3>
              <p className="mt-1 text-xs text-ink-secondary">
                Worker crashed during uncertain tool call <span className="font-data font-semibold">{timeline.needs_review.tool_name}</span> at step {timeline.needs_review.step_index}.
              </p>
              <p className="mt-1 font-data text-xs text-ink-muted">idempotency key: {timeline.needs_review.idempotency_key}</p>
            </div>
            <div className="flex gap-2">
              {timeline.needs_review.available_resolutions.map((res) => (
                <button
                  key={res}
                  type="button"
                  onClick={() => handleResolve(res)}
                  className="rounded border border-status-warning bg-surface-panel px-3 py-1 text-xs font-medium text-ink-primary hover:bg-status-warning/20 transition-colors"
                >
                  {res.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <RunDetail run={timeline} onKill={handleKill} />

      <div className="rounded-lg border border-gridline bg-surface-panel p-5">
        <h2 className="mb-3 font-ui text-sm font-bold text-ink-primary">execution timeline track</h2>
        <TimelineTrack segments={timeline.segments} fencingEvents={timeline.fencing_events} />
      </div>

      <div className="rounded-lg border border-gridline bg-surface-panel p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-ui text-sm font-bold text-ink-primary">raw event log ({events.data?.items.length ?? 0} events)</h2>
          <button
            type="button"
            onClick={() => setShowRawEvents((prev) => !prev)}
            className="rounded border border-gridline px-2.5 py-1 text-xs text-ink-secondary hover:text-ink-primary"
          >
            {showRawEvents ? "collapse" : "expand"}
          </button>
        </div>
        {showRawEvents && <RawEventLog events={events.data?.items ?? []} />}
      </div>
    </div>
  );
}
