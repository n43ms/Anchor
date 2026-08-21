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
  const { timeline, refresh } = useRunStream(runId);
  const events = usePolling(() => (runId ? api.getRunEvents(runId) : Promise.resolve({ run_id: 0, items: [], next_after_seq: null })), 4_000, Boolean(runId));
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [resolved, setResolved] = useState<string | null>(null);

  if (!timeline) {
    return (
      <div className="space-y-4" data-testid="needs-review-detail">
        <p className="text-xs font-mono text-zinc-500 uppercase tracking-widest">loading run details…</p>
      </div>
    );
  }

  const resolve = (resolution: "mark_executed" | "mark_not_executed" | "retry") => {
    setResolveError(null);
    if (!runId) return;
    api
      .resolveRun(runId, resolution)
      .then(() => {
        setResolved(resolution);
        refresh();
      })
      .catch((err: unknown) => setResolveError(err instanceof ApiRequestError ? err.message : "resolve failed"));
  };

  const nr = timeline.needs_review;

  return (
    <div data-testid="needs-review-detail" className="space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
          <Link to="/needs-review" className="hover:text-strand-gold transition-colors">needs review</Link>
          <span>/</span>
          <span className="font-mono text-white">{timeline.display_id ?? `run_${timeline.id}`}</span>
        </div>
        <Link
          to={`/runs/${timeline.id}`}
          className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-xs font-mono text-zinc-300 hover:text-strand-gold hover:border-strand-gold/30 transition-all"
        >
          view run timeline ↗
        </Link>
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <h1 className="font-ui text-base font-bold text-white">
          {timeline.display_id ?? `run_${timeline.id}`} · {timeline.agent_type}
        </h1>
        <p className="mt-1 text-xs text-zinc-400 font-mono">
          Run halted at step {timeline.step_count} due to a worker crash during an unconfirmed side-effect window.
        </p>

        {nr ? (
          <div className="mt-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 backdrop-blur-xl">
            <div className="space-y-1 text-xs font-mono text-zinc-300">
              <div>
                step: <strong className="text-white">{nr.step_index}</strong> · tool:{" "}
                <strong className="text-white">{nr.tool_name}</strong>
              </div>
              <div>declared policy: <span className="font-medium text-amber-300">{nr.declared_policy}</span></div>
              <div className="text-zinc-500">idempotency key: {nr.idempotency_key}</div>
            </div>

            <div className="mt-4">
              <div className="text-xs font-semibold text-white mb-2">Select operator resolution:</div>
              <div className="flex flex-wrap gap-2">
                {nr.available_resolutions.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => resolve(r)}
                    disabled={resolved !== null}
                    className="rounded-xl border border-amber-500/40 bg-amber-500/15 px-3.5 py-1.5 text-xs font-mono font-medium text-amber-300 transition-colors hover:bg-amber-500/25 disabled:opacity-40"
                  >
                    {r.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>

            {resolveError && <p className="mt-3 text-xs font-mono text-rose-400">{resolveError}</p>}
            {resolved && (
              <p className="mt-3 text-xs font-mono text-emerald-400">
                resolution recorded: <strong>{resolved.replace(/_/g, " ")}</strong>. Run is now eligible for worker reclamation.
              </p>
            )}
          </div>
        ) : (
          <div className="mt-4 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-xs font-mono text-zinc-500">
            this run is not currently in the uncertainty window
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <h2 className="mb-3 font-ui text-xs font-bold uppercase tracking-wider text-white">full event log</h2>
        <RawEventLog events={events.data?.items ?? []} />
      </div>
    </div>
  );
}
