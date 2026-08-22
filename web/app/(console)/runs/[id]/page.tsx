import { useParams, Link } from "react-router-dom";
import { useState, useMemo } from "react";
import { useRunStream } from "@/hooks/useRunStream";
import { usePolling } from "@/hooks/usePolling";
import { RunDetail } from "@/components/run/RunDetail";
import { TimelineTrack } from "@/components/run/TimelineTrack";
import { RawEventLog } from "@/components/run/RawEventLog";
import { api, ApiRequestError } from "@/lib/api";
import {
  ArrowLeft,
  Radio,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Search,
  Bot,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Globe,
} from "lucide-react";

interface SearchResultItem {
  title?: string;
  url?: string;
  snippet?: string;
}

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id ?? "";
  const { timeline, connected, stale, refresh } = useRunStream(runId);
  const events = usePolling(
    () =>
      runId
        ? api.getRunEvents(runId)
        : Promise.resolve({ run_id: 0, items: [], next_after_seq: null }),
    3_000,
    Boolean(runId)
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [showOutput, setShowOutput] = useState(true);
  const [showTranscripts, setShowTranscripts] = useState(true);
  const [showRawEvents, setShowRawEvents] = useState(false);
  const [copied, setCopied] = useState(false);

  const completedEvent = useMemo(
    () => events.data?.items.find((e) => e.type === "RUN_COMPLETED"),
    [events.data?.items]
  );

  const runOutput = useMemo(() => {
    if (!completedEvent?.payload) return null;
    const payload = completedEvent.payload as Record<string, unknown>;
    return (payload.output as Record<string, unknown>) ?? payload;
  }, [completedEvent]);

  const stepActivities = useMemo(() => {
    if (!events.data?.items) return [];
    const items = events.data.items;
    const steps: Array<{
      step_index: number;
      type: "llm" | "tool";
      title: string;
      rawContent: string;
      model?: string;
      meta?: string;
      searchResults?: SearchResultItem[];
    }> = [];

    for (const ev of items) {
      const p = ev.payload as Record<string, unknown>;
      if (ev.type === "LLM_CALLED") {
        steps.push({
          step_index: Number(p.step_index ?? 0),
          type: "llm",
          title: `Step ${p.step_index}: Model Generation`,
          model: String(p.model ?? "gemini-2.5-flash"),
          rawContent: String(p.response ?? ""),
          meta: `${Number(p.latency_ms ?? 0).toFixed(0)}ms inference`,
        });
      } else if (ev.type === "TOOL_RESULT") {
        const res = (p.result as Record<string, unknown>) ?? p;
        let searchResults: SearchResultItem[] = [];

        if (res && typeof res === "object") {
          const resultsArr = (res as Record<string, unknown>).results;
          if (Array.isArray(resultsArr)) {
            searchResults = resultsArr as SearchResultItem[];
          }
        }

        steps.push({
          step_index: Number(p.step_index ?? 0),
          type: "tool",
          title: `Step ${p.step_index}: Tool Call (${p.tool_name ?? "tool"})`,
          rawContent: JSON.stringify(res, null, 2),
          meta: `Key: ${String(p.idempotency_key ?? "").slice(0, 12)}…`,
          searchResults,
        });
      }
    }
    return steps;
  }, [events.data?.items]);

  const allRetrievedSources = useMemo(() => {
    const sources: SearchResultItem[] = [];
    for (const s of stepActivities) {
      if (s.searchResults && s.searchResults.length > 0) {
        sources.push(...s.searchResults);
      }
    }
    return sources;
  }, [stepActivities]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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

      {/* DEDICATED AGENT OUTPUT & RESULTS CARD */}
      {runOutput && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.04] p-5 space-y-4 backdrop-blur-2xl">
          <div className="flex items-center justify-between border-b border-emerald-500/20 pb-3">
            <button
              type="button"
              onClick={() => setShowOutput((prev) => !prev)}
              className="flex items-center gap-2 text-left hover:opacity-85 transition-opacity"
            >
              <Sparkles className="h-4 w-4 text-emerald-400 shrink-0" />
              <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-emerald-300">
                Agent Output & Synthesis
              </h2>
              <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-mono text-emerald-400 border border-emerald-500/30">
                COMPLETED
              </span>
              {showOutput ? (
                <ChevronUp className="h-4 w-4 text-emerald-400/70 ml-1" />
              ) : (
                <ChevronDown className="h-4 w-4 text-emerald-400/70 ml-1" />
              )}
            </button>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowOutput((prev) => !prev)}
                className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-mono text-emerald-300 hover:bg-emerald-500/20 transition-all"
              >
                {showOutput ? "collapse" : "expand"}
              </button>
              <button
                type="button"
                onClick={() => handleCopy(JSON.stringify(runOutput, null, 2))}
                className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-mono text-emerald-300 hover:bg-emerald-500/20 transition-all"
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                <span>{copied ? "copied" : "copy output"}</span>
              </button>
            </div>
          </div>

          {showOutput && (
            <div className="space-y-4 pt-1">
            {/* Generated Synthesis Text */}
            {typeof runOutput.summary === "string" && (
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono text-emerald-400/80 uppercase tracking-wider">
                  Generated Synthesis
                </span>
                <div className="rounded-xl border border-white/[0.08] bg-black/60 p-4 font-mono text-xs leading-relaxed text-zinc-100 whitespace-pre-wrap shadow-inner">
                  {runOutput.summary}
                </div>
              </div>
            )}

            {/* Retrieved Tool Sources (e.g. Wikipedia Search Results) */}
            {allRetrievedSources.length > 0 && (
              <div className="space-y-2 pt-1">
                <span className="text-[10px] font-mono text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Globe className="h-3 w-3 text-indigo-400" />
                  Retrieved Research Sources ({allRetrievedSources.length})
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {allRetrievedSources.map((item, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-3 space-y-1.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-mono text-xs font-bold text-indigo-200 line-clamp-1">
                          {item.title || "Search Result"}
                        </span>
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-400 hover:text-indigo-200 transition-colors shrink-0"
                          >
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                      {item.snippet && (
                        <p className="text-[11px] font-mono text-zinc-400 line-clamp-2 leading-relaxed">
                          {item.snippet}
                        </p>
                      )}
                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] font-mono text-indigo-400/80 hover:underline truncate block"
                        >
                          {item.url}
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Key Metadata Attributes */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono pt-1">
              {Object.entries(runOutput)
                .filter(([k]) => k !== "summary")
                .map(([k, v]) => (
                  <div
                    key={k}
                    className="rounded-xl border border-white/[0.06] bg-black/40 p-2.5 space-y-0.5"
                  >
                    <span className="text-[10px] text-zinc-400 uppercase tracking-wider">
                      {k.replace(/_/g, " ")}
                    </span>
                    <p className="font-bold text-white truncate">
                      {typeof v === "object" ? JSON.stringify(v) : String(v)}
                    </p>
                  </div>
                ))}
            </div>
          </div>
          )}
        </div>
      )}

      {/* TOGGLEABLE STEP TRANSCRIPTS & TOOL SIDE EFFECTS DROPDOWN */}
      {stepActivities.length > 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-3 backdrop-blur-2xl">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setShowTranscripts((prev) => !prev)}
              className="flex items-center gap-2.5 text-left hover:opacity-80 transition-opacity"
            >
              <Bot className="h-4 w-4 text-strand-gold shrink-0" />
              <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">
                Step Transcripts & Tool Side Effects ({stepActivities.length})
              </h2>
              {showTranscripts ? (
                <ChevronUp className="h-4 w-4 text-zinc-400" />
              ) : (
                <ChevronDown className="h-4 w-4 text-zinc-400" />
              )}
            </button>
            <button
              type="button"
              onClick={() => setShowTranscripts((prev) => !prev)}
              className="rounded-lg border border-white/[0.08] bg-white/[0.02] px-3 py-1 font-mono text-xs text-zinc-400 hover:text-white transition-colors"
            >
              {showTranscripts ? "collapse" : "expand"}
            </button>
          </div>

          {showTranscripts && (
            <div className="space-y-3 pt-2">
              {stepActivities.map((act, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-white/[0.06] bg-black/50 p-4 space-y-2.5 font-mono text-xs"
                >
                  <div className="flex items-center justify-between text-[11px] text-zinc-400 border-b border-white/[0.04] pb-2">
                    <div className="flex items-center gap-2">
                      {act.type === "llm" ? (
                        <Sparkles className="h-3.5 w-3.5 text-strand-gold" />
                      ) : (
                        <Search className="h-3.5 w-3.5 text-indigo-400" />
                      )}
                      <span className="font-bold text-zinc-200">{act.title}</span>
                      {act.model && (
                        <span className="rounded bg-white/[0.06] px-1.5 py-0.5 text-[9px] text-zinc-300 border border-white/[0.08]">
                          {act.model}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {act.meta && (
                        <span className="text-[10px] text-zinc-400">{act.meta}</span>
                      )}
                      <button
                        type="button"
                        onClick={() => handleCopy(act.rawContent)}
                        className="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
                        title="Copy content"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                    </div>
                  </div>

                  {/* Render Visual Search Results if Available */}
                  {act.searchResults && act.searchResults.length > 0 ? (
                    <div className="space-y-2">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {act.searchResults.map((r, rIdx) => (
                          <div
                            key={rIdx}
                            className="rounded-lg border border-white/[0.06] bg-black/40 p-2.5 space-y-1"
                          >
                            <div className="flex items-start justify-between gap-1">
                              <span className="font-bold text-indigo-300 text-[11px] truncate">
                                {r.title || "Result"}
                              </span>
                              {r.url && (
                                <a
                                  href={r.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-indigo-400 hover:text-indigo-200 transition-colors"
                                >
                                  <ExternalLink className="h-2.5 w-2.5" />
                                </a>
                              )}
                            </div>
                            {r.snippet && (
                              <p className="text-[10px] text-zinc-400 line-clamp-2">
                                {r.snippet}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="max-h-60 overflow-y-auto rounded-lg bg-black/40 p-3 font-mono text-[11px] leading-relaxed text-zinc-300 whitespace-pre-wrap border border-white/[0.03]">
                      {act.rawContent}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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

      {/* Raw Event Stream Log */}
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
