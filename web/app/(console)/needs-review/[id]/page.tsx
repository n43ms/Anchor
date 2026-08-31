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
import { getToolSpecificDefaultPayload } from "@/lib/payloads";

export default function NeedsReviewDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id ?? "";
  const { timeline, refresh } = useRunStream(runId);
  const events = usePolling(() => (runId ? api.getRunEvents(runId) : Promise.resolve({ run_id: 0, items: [], next_after_seq: null })), 4_000, Boolean(runId));
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [resolved, setResolved] = useState<string | null>(null);
  
  // Interactive Resolution Payload Form State
  const [activeResolutionType, setActiveResolutionType] = useState<"mark_executed" | "mark_not_executed" | "retry" | null>(null);
  const [customOutputJson, setCustomOutputJson] = useState<string>("");
  const [operatorNote, setOperatorNote] = useState<string>("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  if (!timeline) {
    return (
      <div className="space-y-4" data-testid="needs-review-detail">
        <p className="text-xs font-mono text-zinc-500 uppercase tracking-widest">loading run details…</p>
      </div>
    );
  }

  const handleSelectResolution = (resolution: "mark_executed" | "mark_not_executed" | "retry") => {
    setResolveError(null);
    setJsonError(null);
    if (resolution === "mark_executed") {
      setActiveResolutionType("mark_executed");
      const toolName = timeline?.needs_review?.tool_name || "tool";
      const stepIdx = timeline?.needs_review?.step_index || 0;
      setCustomOutputJson(getToolSpecificDefaultPayload(toolName, stepIdx));
    } else {
      // Execute non-custom-payload resolutions directly
      submitResolution(resolution, undefined, undefined);
    }
  };

  const submitResolution = (
    resolution: "mark_executed" | "mark_not_executed" | "retry",
    note?: string,
    resultPayload?: any
  ) => {
    setResolveError(null);
    if (!runId) return;
    api
      .resolveRun(runId, resolution, note, resultPayload)
      .then(() => {
        setResolved(resolution);
        setActiveResolutionType(null);
        refresh();
      })
      .catch((err: unknown) => setResolveError(err instanceof ApiRequestError ? err.message : "resolve failed"));
  };

  const handleConfirmMarkExecuted = () => {
    setJsonError(null);
    let parsed: any;
    try {
      parsed = JSON.parse(customOutputJson);
    } catch (err: any) {
      setJsonError(`Invalid JSON syntax: ${err.message}`);
      return;
    }

    submitResolution("mark_executed", operatorNote || undefined, parsed);
  };

  const nr = timeline.needs_review;

  return (
    <div data-testid="needs-review-detail" className="space-y-6 pb-12 font-mono">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <Link to="/needs-review" className="hover:text-strand-gold transition-colors">needs review</Link>
          <span>/</span>
          <span className="text-white">{timeline.display_id ?? `run_${timeline.id}`}</span>
        </div>
        <Link
          to={`/runs/${timeline.id}`}
          className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-xs text-zinc-300 hover:text-strand-gold hover:border-strand-gold/30 transition-all"
        >
          view run timeline ↗
        </Link>
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <h1 className="font-ui text-base font-bold text-white">
          {timeline.display_id ?? `run_${timeline.id}`} · {timeline.agent_type}
        </h1>
        <p className="mt-1 text-xs text-zinc-400">
          Run halted at step {timeline.step_count} due to a worker crash during an unconfirmed side-effect window.
        </p>

        {nr ? (
          <div className="mt-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 backdrop-blur-xl space-y-4">
            <div className="space-y-1 text-xs text-zinc-300">
              <div>
                step: <strong className="text-white">{nr.step_index}</strong> · tool:{" "}
                <strong className="text-white">{nr.tool_name}</strong>
              </div>
              <div>declared policy: <span className="font-medium text-amber-300">{nr.declared_policy}</span></div>
              <div className="text-zinc-500">idempotency key: {nr.idempotency_key}</div>
            </div>

            <div className="pt-2 border-t border-amber-500/20">
              <div className="text-xs font-semibold text-white mb-2">Select operator resolution:</div>
              <div className="flex flex-wrap gap-2">
                {nr.available_resolutions.map((r) => {
                  const isUnsafeRetry = r === "retry" && nr.declared_policy === "unsafe";
                  const isSelected = activeResolutionType === r;
                  return (
                    <button
                      key={r}
                      type="button"
                      onClick={() => handleSelectResolution(r)}
                      disabled={resolved !== null || isUnsafeRetry}
                      title={isUnsafeRetry ? "Direct retry is unavailable for unsafe tools. Select Mark Executed or Mark Not Executed." : undefined}
                      className={
                        isUnsafeRetry
                          ? "rounded-xl border border-zinc-700/60 bg-zinc-800/40 px-3.5 py-1.5 text-xs font-medium text-zinc-500 cursor-not-allowed opacity-50"
                          : isSelected
                          ? "rounded-xl border border-emerald-500/60 bg-emerald-500/25 px-3.5 py-1.5 text-xs font-bold text-emerald-300 shadow-sm"
                          : "rounded-xl border border-amber-500/40 bg-amber-500/15 px-3.5 py-1.5 text-xs font-medium text-amber-300 transition-colors hover:bg-amber-500/25 disabled:opacity-40"
                      }
                    >
                      {r.replace(/_/g, " ")} {isUnsafeRetry ? "(disabled)" : ""}
                    </button>
                  );
                })}
              </div>
              {nr.declared_policy === "unsafe" && (
                <p className="mt-2 text-[11px] text-amber-400/80">
                  ℹ️ Direct retry is disabled because tool &apos;{nr.tool_name}&apos; is declared &apos;unsafe&apos; without automatic reconciliation. Please select <strong>Mark Executed</strong> or <strong>Mark Not Executed</strong>.
                </p>
              )}
            </div>

            {/* Interactive JSON Output Payload Input Form for Mark Executed */}
            {activeResolutionType === "mark_executed" && resolved === null && (
              <div className="rounded-xl border border-emerald-500/40 bg-black/80 p-4 space-y-3 shadow-2xl">
                <div className="flex items-center justify-between border-b border-emerald-500/30 pb-2">
                  <div className="text-xs font-bold text-emerald-400">
                    Operator Input: Custom JSON Output Payload for POST /api/runs/{runId}/resolve
                  </div>
                  <button
                    type="button"
                    onClick={() => setActiveResolutionType(null)}
                    className="text-[10px] text-zinc-400 hover:text-white"
                  >
                    cancel
                  </button>
                </div>

                <p className="text-[11px] text-zinc-300">
                  Specify the output JSON payload to record into <code>tool_journal.result</code> for step {nr.step_index} ({nr.tool_name}).
                </p>

                <div className="space-y-1">
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider block">
                    Custom Output JSON Payload:
                  </label>
                  <textarea
                    rows={6}
                    value={customOutputJson}
                    onChange={(e) => setCustomOutputJson(e.target.value)}
                    className="w-full rounded-lg border border-emerald-500/30 bg-[#090a0d] p-3 text-xs text-emerald-300 focus:border-emerald-400 focus:outline-none custom-scrollbar font-mono"
                  />
                  {jsonError && <p className="text-xs text-rose-400 mt-1">{jsonError}</p>}
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider block">
                    Operator Note (Optional):
                  </label>
                  <input
                    type="text"
                    value={operatorNote}
                    onChange={(e) => setOperatorNote(e.target.value)}
                    placeholder="e.g. Verified transaction ID in Stripe Dashboard out-of-band"
                    className="w-full rounded-lg border border-white/10 bg-[#090a0d] p-2.5 text-xs text-zinc-200 focus:border-emerald-400 focus:outline-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setActiveResolutionType(null)}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-zinc-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmMarkExecuted}
                    className="rounded-lg border border-emerald-500/50 bg-emerald-500/20 px-4 py-1.5 text-xs font-bold text-emerald-300 hover:bg-emerald-500/30 transition-all shadow-md"
                  >
                    Submit Resolution Payload ↗
                  </button>
                </div>
              </div>
            )}

            {resolveError && <p className="mt-3 text-xs text-rose-400">{resolveError}</p>}
            {resolved && (
              <p className="mt-3 text-xs text-emerald-400">
                resolution recorded: <strong>{resolved.replace(/_/g, " ")}</strong>. Run is now eligible for worker reclamation.
              </p>
            )}
          </div>
        ) : (
          <div className="mt-4 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-xs text-zinc-500">
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
