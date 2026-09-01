"use client";

import React from "react";
import {
  ArrowLeft,
  Video,
  Play,
  AlertTriangle,
  Flame,
  ShieldCheck,
  Code2,
  BookOpen,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

interface DemosViewProps {
  onClose: () => void;
  onOpenDocs?: () => void;
}

interface DemoItem {
  id: string;
  title: string;
  category: string;
  badge: string;
  badgeType: "emerald" | "amber" | "rose" | "cyan";
  videoUrl?: string;
  imageUrl?: string;
  summary: string;
  keyFeatures: string[];
  codeSnippet?: string;
}

const DEMO_ITEMS: DemoItem[] = [
  {
    id: "completed-run",
    title: "01. End-to-End Multi-Step LLM Workflow",
    category: "Workflow Execution",
    badge: "200 OK SUCCESS",
    badgeType: "emerald",
    videoUrl: "/videos/demo_completed_run.mp4",
    summary:
      "Demonstration of an end-to-end execution of `langchain_executive_market_agent`. Shows parallel market intelligence lookup, competitive risk calculation, Gemini 2.5 Flash LLM synthesis, and email delivery with two-phase tool journaling.",
    keyFeatures: [
      "Atomic Two-Phase Tool Journaling (INTENT / RESULT)",
      "Gemini 2.5 Flash LLM Synthesis",
      "Linear Generator Yield Syntax (@anchor.agent)",
      "Zero Duplicate API Executions",
    ],
    codeSnippet: `@anchor.agent(name="executive_market_agent")
def run_agent(ctx: anchor.StepContext):
    signals = yield anchor.ToolCall("fetch_tech_market_signals", {"topic": "AI Agents"})
    metrics = yield anchor.ToolCall("compute_risk_metrics", {"domain": "AI Agents"})
    report  = yield anchor.ModelCall(model="gemini-2.5-flash", messages=[...])
    yield anchor.ToolCall("dispatch_resend_email", {"recipient": "user@example.com", "body": report})
    yield anchor.Done({"status": "completed"})`,
  },
  {
    id: "simulated-kill",
    title: "02. Worker Process Interrupt & Auto-Reclaim",
    category: "Crash Recovery",
    badge: "SUB-SECOND RECLAIM",
    badgeType: "amber",
    videoUrl: "/videos/demo_simulated_kill.mp4",
    summary:
      "Demonstrates an unplanned worker process crash mid-workflow. Shows Anchor's worker lease expiration detection, monotonic epoch fencing (Epoch 1 → Epoch 2), and sub-second lease reclamation by a secondary worker replica without lost state.",
    keyFeatures: [
      "Monotonic Epoch Fencing (AN001)",
      "Worker Claim Lease Expiration (<300ms)",
      "Zero Lost LLM Reasoning State",
      "Automatic Re-execution & Reclaim",
    ],
    codeSnippet: `# Worker #1 (PID 4812) interrupted by container crash mid-execution
# Worker #2 (PID 9104) detects lease expiry and reclaims run:
# [EPOCH SWAP] worker-a#1 process crash → worker-b#1 (epoch 1 → 2)
# Replaying completed step #0, step #1 (side-effects skipped)
# Resuming LLM execution at step #2 cleanly`,
  },
  {
    id: "unsafe-pause",
    title: "03. Unsafe Tool Pause & NeedsReview Queue",
    category: "Unsafe Tool Safety",
    badge: "NEEDS REVIEW HALTED",
    badgeType: "amber",
    videoUrl: "/videos/demo_pauses_for_unsafe.mp4",
    summary:
      "Demonstrates the `@anchor.tool(safety=\"unsafe\")` protection protocol. When a worker process crashes mid-execution of an unsafe tool call, Anchor halts the run in `needs_review` status. Human operators can resolve the halt via `mark_executed` (which accepts a custom JSON payload result override) or `mark_not_executed` (which authorizes the runner to retry execution from the failing step).",
    keyFeatures: [
      "Uncertainty Window Protection",
      "mark_executed: Accepts Custom JSON Payload Result Override",
      "mark_not_executed: Authorizes Runner Re-execution & Retries",
      "Zero Duplicate Side-Effects on Unsafe Actions",
    ],
    codeSnippet: `# Operator Resolution Options on POST /api/runs/{id}/resolve
# 1. mark_executed (supplies custom JSON result payload):
POST /api/runs/102/resolve {"resolution": "mark_executed", "output": {"status": "sent", "message_id": "msg_98a31f"}}

# 2. mark_not_executed (authorizes runner to safely retry from step 2):
POST /api/runs/102/resolve {"resolution": "mark_not_executed"}`,
  },
  {
    id: "chaos-run",
    title: "04. Live Adversarial Fault Injection Harness",
    category: "Chaos Testing",
    badge: "ADVERSARIAL FAULT INJECTION • 0 VIOLATIONS",
    badgeType: "rose",
    videoUrl: "/videos/demo_chaos.mp4",
    summary:
      "Live recording of the Chaos Engine injecting random process terminations across parallel worker replicas. Demonstrates real-time lease swaps, lease fencing, and 100% deterministic workflow completion.",
    keyFeatures: [
      "Adversarial Process Termination Engine",
      "Multi-Worker Replica Load Balancing",
      "Continuous Heartbeat Lease Monitor",
      "100% Deterministic Completion Rate",
    ],
  },
  {
    id: "benchmark-proof",
    title: "05. Invariant Verification Log Proof",
    category: "Benchmarks",
    badge: "5 / 5 INVARIANTS HELD",
    badgeType: "cyan",
    imageUrl: "/videos/demo_chaos_invariants_held.png",
    summary:
      "Benchmark log evidence proving all 5 core engine invariants held under adversarial load: 0 Duplicate Side-Effects, 0 Stranded Runs, Monotonic Epoch Fencing (`AN001`), Sub-Second Crash Recovery, and 100% Deterministic Completion.",
    keyFeatures: [
      "Invariant I1: At-Most-Once Tool Execution",
      "Invariant I2: Monotonic Epoch Fencing Tokens",
      "Invariant I3: No Stranded Active Runs",
      "Invariant I4: Sub-Second Lease Reclamation",
      "Invariant I5: Deterministic Audit Log Journaling",
    ],
  },
];

const getAssetUrl = (path: string) => {
  const base = (import.meta as any).env?.BASE_URL || "/";
  const cleanBase = base.endsWith("/") ? base : base + "/";
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return cleanBase + cleanPath;
};

export const DemosView: React.FC<DemosViewProps> = ({ onClose, onOpenDocs }) => {
  return (
    <div className="h-screen w-full bg-[#07070a] text-zinc-200 font-sans flex flex-col overflow-hidden selection:bg-amber-500/20 selection:text-amber-300">
      {/* High-Contrast Signature Gold Header Bar */}
      <header className="shrink-0 z-50 flex items-center justify-between border-b border-amber-500/30 bg-black/90 px-4 md:px-6 py-2.5 md:py-3.5 backdrop-blur-md">
        <div className="flex items-center gap-2.5 md:gap-4">
          <button
            type="button"
            onClick={onClose}
            className="flex items-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-mono text-amber-300 font-bold hover:bg-amber-500/20 hover:border-amber-400 transition-all cursor-pointer shadow-sm"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Return to Main Site</span>
            <span className="sm:hidden">Exit</span>
          </button>
          <div className="h-4 w-px bg-amber-500/30 hidden sm:block" />
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="font-extrabold text-amber-400 tracking-wider uppercase text-xs sm:text-sm flex items-center gap-1.5">
              <Video className="h-4 w-4 text-amber-400" />
              <span>ANCHOR VIDEO DEMOS</span>
            </span>
            <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[9px] text-amber-400 font-mono font-bold">
              v1.6.0
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          {onOpenDocs && (
            <button
              type="button"
              onClick={onOpenDocs}
              className="flex items-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-amber-300 font-bold hover:bg-amber-500/20 transition-all text-xs cursor-pointer"
            >
              <BookOpen className="h-3.5 w-3.5 text-amber-400" />
              <span className="hidden sm:inline">Documentation</span>
            </button>
          )}

          <a
            href="https://github.com/n43ms/Anchor"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-2.5 py-1.5 text-zinc-300 hover:text-white hover:border-amber-500/40 transition-all font-semibold text-xs"
          >
            <Code2 className="h-3.5 w-3.5 text-amber-400" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
        </div>
      </header>

      {/* Main Container - Standalone Full Width Layout */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Hero Banner (Compact) */}
          <div className="rounded-xl border border-amber-500/30 bg-black/80 p-3.5 sm:p-4 space-y-1.5 relative overflow-hidden backdrop-blur-xl shadow-xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-amber-500/40 bg-amber-500/20 px-2 py-0.5 text-[9.5px] font-mono font-bold text-amber-300 flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-amber-400" />
                <span>EMPIRICAL BENCHMARK RECORDINGS</span>
              </span>
              <span className="rounded-full border border-emerald-500/40 bg-emerald-500/20 px-2 py-0.5 text-[9.5px] font-mono font-bold text-emerald-300">
                5 / 5 INVARIANTS PROVED
              </span>
            </div>

            <h1 className="text-xs sm:text-sm font-bold text-white font-mono tracking-tight">
              See Anchor's Crash Recovery & Epoch Fencing in Action
            </h1>
            <p className="text-[11px] text-zinc-400 font-sans leading-normal">
              Explore recorded video demonstrations of multi-step agent execution, unplanned worker process crashes, unsafe tool pauses, and chaos harness runs.
            </p>
          </div>

          {/* Cards Stack */}
          <div className="space-y-8">
            {DEMO_ITEMS.map((item) => (
              <div
                key={item.id}
                id={item.id}
                className="rounded-2xl border border-white/10 bg-black/60 p-5 md:p-6 space-y-4 hover:border-amber-500/40 transition-all shadow-xl backdrop-blur-xl"
              >
                {/* Card Title Header (Single Line Clean Heading) */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
                  <div>
                    <span className="text-[9.5px] font-mono font-bold text-amber-400 uppercase tracking-widest block mb-0.5">
                      {item.category}
                    </span>
                    <h2 className="text-xs sm:text-sm md:text-base font-bold text-white font-mono flex items-center gap-2">
                      <span>{item.title}</span>
                    </h2>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10.5px] font-mono font-bold border ${
                      item.badgeType === "emerald"
                        ? "border-emerald-500/40 bg-emerald-500/20 text-emerald-300"
                        : item.badgeType === "amber"
                        ? "border-amber-500/40 bg-amber-500/20 text-amber-300"
                        : item.badgeType === "rose"
                        ? "border-rose-500/40 bg-rose-500/20 text-rose-300"
                        : "border-cyan-500/40 bg-cyan-500/20 text-cyan-300"
                    }`}
                  >
                    {item.badge}
                  </span>
                </div>

                {/* Media Container: Zoomed Full-Viewport Video or Reverted Image Size */}
                {item.videoUrl && (
                  <div className="rounded-xl overflow-hidden border border-amber-500/30 bg-black shadow-2xl">
                    <video
                      controls
                      playsInline
                      preload="metadata"
                      className="w-full aspect-video rounded-xl object-cover scale-105 bg-black"
                    >
                      <source src={getAssetUrl(item.videoUrl)} type="video/mp4" />
                      Your browser does not support the video element.
                    </video>
                  </div>
                )}

                {item.imageUrl && (
                  <div className="rounded-xl overflow-hidden border border-emerald-500/40 bg-black shadow-2xl">
                    <img
                      src={getAssetUrl(item.imageUrl)}
                      alt={item.title}
                      className="w-full max-h-[440px] object-contain bg-black"
                    />
                  </div>
                )}

                {/* Description & Key Features */}
                <div className={`grid grid-cols-1 ${item.codeSnippet ? "lg:grid-cols-2" : "grid-cols-1"} gap-6 pt-2`}>
                  <div className="space-y-3">
                    <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                      Technical Overview
                    </h3>
                    <p className="text-xs text-zinc-300 font-sans leading-relaxed">
                      {item.summary}
                    </p>

                    <div className="space-y-1.5 pt-2">
                      <h4 className="text-[11px] font-mono font-bold text-amber-400 uppercase">
                        Guarantees & Highlights
                      </h4>
                      <ul className="space-y-1 text-xs text-zinc-300 font-mono">
                        {item.keyFeatures.map((feat) => (
                          <li key={feat} className="flex items-center gap-2">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                            <span>{feat}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Code / Log Snippet */}
                  {item.codeSnippet && (
                    <div className="space-y-2">
                      <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center justify-between">
                        <span>Code / Log Trace</span>
                        <span className="text-[10px] text-zinc-500">Python / Shell</span>
                      </h3>
                      <pre className="rounded-xl border border-white/10 bg-black/90 p-4 font-mono text-[11px] text-amber-300 overflow-x-auto custom-scrollbar leading-relaxed">
                        {item.codeSnippet}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
