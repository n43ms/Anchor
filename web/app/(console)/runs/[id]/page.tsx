import { useParams, Link } from "react-router-dom";
import { useState } from "react";
import { useRunStream } from "@/hooks/useRunStream";
import { usePolling } from "@/hooks/usePolling";
import { RunDetail } from "@/components/run/RunDetail";
import { TimelineTrack } from "@/components/run/TimelineTrack";
import { RawEventLog } from "@/components/run/RawEventLog";
import { api, ApiRequestError } from "@/lib/api";
import { ArrowLeft, Radio, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id ?? "";
  const { timeline, connected, stale, refresh } = useRunStream(runId);
  const events = usePolling(
    () =>
      runId
        ? api.getRunEvents(runId)
        : Promise.resolve({ run_id: 0, items: [], next_after_seq: null }),
    4_000,
    Boolean(runId)
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [showRawEvents, setShowRawEvents] = useState(false);

  const handleKill = (workerId: string) => {
    setActionError(null);
    setActionSuccess(null);
    api
      .killWorker(workerId)
      .then(() => {
        setActionSuccess(`Kill command issued to ${workerId}`);
      })
      .catch((err: unknown) => {
        setActionError(
          err instanceof ApiRequestError ? err.message : "kill request failed"
        );
      });
  };

  const handleCancel = () => {
    if (!runId) return;
    setActionError(null);
    setActionSuccess(null);
    api
      .cancelRun(runId)
      .then(() => {
        setActionSuccess("Cancellation requested");
        refresh();
      })
      .catch((err: unknown) => {
        setActionError(
          err instanceof ApiRequestError ? err.message : "cancel request failed"
        );
      });
  };

  const handleResolve = (
    resolution: "mark_executed" | "mark_not_executed" | "retry"
  ) => {
    if (!runId) return;
    setActionError(null);
    setActionSuccess(null);
    api
      .resolveRun(runId, resolution)
      .then(() => {
        setActionSuccess(`Resolution recorded: ${resolution.replace("_", " ")}`);
        refresh();
      })
      .catch((err: unknown) => {
        setActionError(
          err instanceof ApiRequestError ? err.message : "resolution failed"
        );
      });
  };

  if (!timeline) {
    return (
      <div className="space-y-4 p-8 text-center" data-testid="run-detail-page">
        <p
          className="text-sm font-mono text-zinc-500 uppercase tracking-widest"
          data-testid="run-detail-loading"
        >
          loading run timeline…
        </p>
      </div>
    );
  }

  const isTerminal = ["completed", "failed", "cancelled"].includes(timeline.status);
  const isNeedsReview = timeline.status === "needs_review";

  return (
    <div data-testid="run-detail-page" className="space-y-6 pb-12">
      {/* Top Breadcrumb & Status Ribbon */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-4 backdrop-blur-2xl">
        <div className="flex items-center gap-2.5 text-xs font-mono text-zinc-400">
          <Link
            to="/runs"
            className="flex items-center gap-1 hover:text-strand-gold transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>runs</span>
          </Link>
          <span className="text-zinc-600">/</span>
          <span className="font-mono text-white font-bold">
            {timeline.display_id ?? `run_${timeline.id}`}
          </span>
          <span
            className={`ml-2 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-mono font-medium ${
              connected
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                : "border-amber-500/30 bg-amber-500/10 text-amber-400"
            }`}
          >
            <Radio className="h-2.5 w-2.5 animate-pulse" />
            {connected ? "LIVE STREAM" : "POLLING FALLBACK"}
          </span>
        </div>

        {!isTerminal && (
          <button
            type="button"
            onClick={handleCancel}
            className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-1.5 text-xs font-mono text-rose-400 hover:bg-rose-500/20 hover:border-rose-500/50 transition-all shadow-sm"
          >
            Cancel Run
          </button>
        )}
      </div>

      {!connected && (
        <div
          className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs font-mono text-amber-400 flex items-center gap-2.5 backdrop-blur-xl"
          data-testid="run-detail-connection-warning"
        >
          <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping shadow-glow-amber" />
          <span>
            {stale
              ? "connection stale — showing last known state from store"
              : "connecting live telemetry stream…"}
          </span>
        </div>
      )}

      {actionError && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs font-mono text-rose-400 flex items-center gap-2 backdrop-blur-xl">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {actionSuccess && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs font-mono text-emerald-400 flex items-center gap-2 backdrop-blur-xl">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {isNeedsReview && timeline.needs_review && (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-5 backdrop-blur-2xl space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <h3 className="font-ui text-sm font-bold text-white flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                Action Required: Ambiguous Step Execution
              </h3>
              <p className="mt-1 text-xs text-zinc-300 font-mono">
                Worker crashed during uncertain tool call{" "}
                <span className="font-bold text-strand-gold">
                  {timeline.needs_review.tool_name}
                </span>{" "}
                at step {timeline.needs_review.step_index}.
              </p>
              <p className="mt-1 font-mono text-xs text-zinc-500">
                idempotency key: {timeline.needs_review.idempotency_key}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {timeline.needs_review.available_resolutions.map((res) => (
                <button
                  key={res}
                  type="button"
                  onClick={() => handleResolve(res)}
                  className="rounded-xl border border-amber-500/40 bg-amber-500/20 px-3.5 py-1.5 text-xs font-mono font-medium text-amber-300 hover:bg-amber-500/30 transition-colors shadow-sm"
                >
                  {res.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Run Detail Card */}
      <RunDetail run={timeline} onKill={handleKill} />

      {/* Timeline Track Card */}
      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-3 backdrop-blur-2xl">
        <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">
          Execution Timeline Track & Fencing Tokens
        </h2>
        <TimelineTrack
          segments={timeline.segments}
          fencingEvents={timeline.fencing_events}
        />
      </div>

      {/* Raw Event Log Card */}
      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-3 backdrop-blur-2xl">
        <div className="flex items-center justify-between">
          <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">
            Raw Event Stream Log ({events.data?.items.length ?? 0} events)
          </h2>
          <button
            type="button"
            onClick={() => setShowRawEvents((prev) => !prev)}
            className="rounded-lg border border-white/[0.08] bg-white/[0.02] px-3 py-1 font-mono text-xs text-zinc-400 hover:text-white transition-colors"
          >
            {showRawEvents ? "collapse" : "expand"}
          </button>
        </div>
        {showRawEvents && <RawEventLog events={events.data?.items ?? []} />}
      </div>
    </div>
  );
}
