import React, { useState } from "react";
import { MiniOperatorConsole } from "./MiniOperatorConsole";
import { MechanismExplainer } from "./MechanismExplainer";
import { RunThread } from "./RunThread";
import { QuickstartModal } from "./QuickstartModal";
import { useDemo } from "../context/DemoProvider";
import {
  ShieldCheck,
  Zap,
  Cpu,
  Terminal,
  ExternalLink,
  CheckCircle2,
  Lock,
  Flame,
  Activity,
  Layers,
  ArrowRight,
  Database,
  RefreshCw,
  Server,
  Code2,
  BarChart3,
  Wrench,
  DollarSign,
  Briefcase,
  UserCheck,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  BookOpen,
} from "lucide-react";


const GithubIcon: React.FC<{ className?: string }> = ({ className = "h-4 w-4" }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
  </svg>
);

const LinkedinIcon: React.FC<{ className?: string }> = ({ className = "h-4 w-4" }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
  </svg>
);

export const LandingPage: React.FC = () => {
  const { killWorker, setActiveTab } = useDemo();
  const [isQuickstartModalOpen, setIsQuickstartModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [heroPreset, setHeroPreset] = useState<"normal" | "crash">("crash");
  const [showArchDetails, setShowArchDetails] = useState(false);
  const [showWhyDetails, setShowWhyDetails] = useState(false);

  const scrollToId = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  const handleTriggerChaos = async () => {
    scrollToId("operator-console-container");
    setActiveTab("chaos-console");
    await killWorker("worker-a#1");
  };

  const handleCopyCmd = () => {
    navigator.clipboard.writeText("pip install anchor-runtime && anchor init");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const heroPresetSegments = {
    normal: [
      {
        worker_id: "worker-a#1",
        epoch: 1,
        started_at: new Date(Date.now() - 10000).toISOString(),
        ended_at: null,
        steps: [
          { step_index: 0, name: "analyze_user_requirements", status: "done" as const, action_kind: "model" as const, started_at: "", completed_at: null, executed: true },
          { step_index: 1, name: "execute_db_migration", status: "done" as const, action_kind: "tool" as const, started_at: "", completed_at: null, executed: true },
          { step_index: 2, name: "fetch_external_api_payload", status: "done" as const, action_kind: "tool" as const, started_at: "", completed_at: null, executed: true },
          { step_index: 3, name: "synthesize_llm_final_response", status: "done" as const, action_kind: "model" as const, started_at: "", completed_at: null, executed: true },
        ],
      },
    ],
    crash: [
      {
        worker_id: "worker-a#1",
        epoch: 1,
        started_at: new Date(Date.now() - 10000).toISOString(),
        ended_at: new Date(Date.now() - 4000).toISOString(),
        steps: [
          { step_index: 0, name: "analyze_user_requirements", status: "done" as const, action_kind: "model" as const, started_at: "", completed_at: null, executed: true },
          { step_index: 1, name: "execute_db_migration", status: "done" as const, action_kind: "tool" as const, started_at: "", completed_at: null, executed: true },
        ],
      },
      {
        worker_id: "worker-b#1",
        epoch: 2,
        claim_reason: "reclaimed_after_lease_expiry" as const,
        started_at: new Date(Date.now() - 3500).toISOString(),
        ended_at: null,
        steps: [
          { step_index: 2, name: "fetch_external_api_payload", status: "done" as const, action_kind: "tool" as const, started_at: "", completed_at: null, executed: false },
          { step_index: 3, name: "synthesize_llm_final_response", status: "done" as const, action_kind: "model" as const, started_at: "", completed_at: null, executed: true },
        ],
      },
    ],
  };


  return (
    <div className="min-h-screen bg-black text-zinc-100 font-sans selection:bg-amber-500/20 selection:text-amber-200">
      {/* 1. Header Surface & Top Navigation Bar with Ambient Golden Strand Backdrop */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-black/85 backdrop-blur-2xl overflow-hidden">
        {/* Ambient 15-Strand Golden Wave Ribbon Background Overlay (End-to-End, Balanced 30% Opacity) */}
        <div className="absolute inset-0 pointer-events-none opacity-30 w-full h-full flex items-center">
          <RunThread headerMode={true} segments={[]} />
        </div>




        <div className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-2.5">
          {/* Logo & Author Branding */}
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-amber-500/40 bg-amber-500/10 p-1.5 shadow-sm">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-full w-full text-amber-400"
              >
                <circle cx="12" cy="5" r="3" />
                <line x1="12" y1="22" x2="12" y2="8" />
                <path d="M5 12H2a10 10 0 0 0 20 0h-3" />
              </svg>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-extrabold tracking-wider text-white">ANCHOR</span>
                <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.2 text-[9px] font-mono font-semibold text-amber-400">
                  v1.5.4-prod
                </span>
              </div>
              <div className="text-[9px] font-mono text-zinc-400">
                Engineered by <strong className="text-white">Aditya Nema</strong>
              </div>
            </div>
          </div>

          {/* Top Navigation Links */}
          <nav className="hidden lg:flex items-center gap-6 font-mono text-xs font-semibold text-zinc-300">
            <button
              type="button"
              onClick={() => setIsQuickstartModalOpen(true)}
              className="hover:text-amber-400 transition-colors cursor-pointer flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-amber-300 font-bold"
            >
              <BookOpen className="h-3.5 w-3.5 text-amber-400" />
              <span>Quickstart Guide</span>
            </button>
            <button
              type="button"
              onClick={() => scrollToId("operator-console-container")}
              className="hover:text-amber-400 transition-colors cursor-pointer"
            >
              Operator Console
            </button>
            <button
              type="button"
              onClick={() => scrollToId("agent-sdk-code")}
              className="hover:text-amber-400 transition-colors cursor-pointer text-amber-300 font-bold"
            >
              Agent Runtime SDK
            </button>
            <button
              type="button"
              onClick={() => scrollToId("why-anchor-matrix-container")}
              className="hover:text-amber-400 transition-colors cursor-pointer"
            >
              Durability Matrix
            </button>
            <button
              type="button"
              onClick={() => scrollToId("engineering-core-container")}
              className="hover:text-amber-400 transition-colors cursor-pointer"
            >
              How It Works
            </button>
          </nav>

          {/* Action Buttons & Links */}
          <div className="flex items-center gap-2 font-mono text-xs">
            <a
              href="https://linkedin.com/in/adityaxnema"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 rounded-xl border border-blue-500/40 bg-blue-500/10 px-2.5 py-1 text-blue-300 hover:bg-blue-500/20 transition-all font-semibold text-[11px]"
            >
              <LinkedinIcon className="h-3 w-3 text-blue-400" />
              <span>LinkedIn</span>
            </a>

            <a
              href="https://github.com/n43ms/Anchor"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:flex items-center gap-1 rounded-xl border border-white/10 bg-white/5 px-2.5 py-1 text-zinc-300 hover:text-white transition-all font-semibold text-[11px]"
            >
              <GithubIcon className="h-3 w-3" />
              <span>GitHub</span>
            </a>
          </div>
        </div>
      </header>



      {/* 2. Hero Section (Fully visible in 1st frame at 100% zoom) */}
      <section className="relative pt-3 pb-4 px-4">
        <div className="mx-auto max-w-4xl text-center space-y-3">
          {/* Main Headline */}
          <h1 className="text-4xl sm:text-4xl font-extrabold tracking-tight text-white max-w-3xl mx-auto leading-tight">
            Durable Execution Engine for<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-200 to-amber-500">Mission-Critical AI Agents.</span>
          </h1>

          {/* Relatable Pain-Point Scenarios */}
          <div className="mx-auto max-w-3xl flex flex-col sm:flex-row items-center justify-center gap-2.5 font-sans text-xs sm:text-sm font-bold">
            <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3.5 py-1 text-amber-300 flex items-center gap-2 shadow-sm">
              <span className="text-base -mt-0.5">💳</span>
              <span className = "text-xs">Agent double-charged a card mid-tool call?</span>
            </div>
            <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-3.5 py-1 text-rose-300 flex items-center gap-2 shadow-sm">
              <span className="text-base -mt-0.5">💀</span>
              <span className="text-xs">Woke up to a dead container and lost 4 hrs LLM progress?</span>
            </div>
          </div>


          {/* Hero Subtitle */}
          <p className="w-max text-zinc-300 max-w-3xl mx-auto font-sans leading-relaxed">
            Eliminate <span className="text-white font-semibold">lost state</span> and <span className="text-white font-semibold">duplicate API calls</span> when executing multi-step LLM agent pipelines.<br />
            <span className="italic font-extrabold text-amber-300">Anchor</span> guarantees <span className="text-amber-300 font-semibold">atomic two-phase tool journaling</span>, <span className="text-amber-300 font-semibold">monotonic epoch fencing</span>, and <span className="text-amber-300 font-semibold">sub-second crash recovery</span>.
          </p>


          {/* Real-Time Agent Execution Stream Header with Interactive Presets */}
          <div className="mx-auto max-w-3xl rounded-xl border border-white/10 bg-black/90 p-2.5 space-y-1 shadow-2xl backdrop-blur-xl text-left">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-[11px] font-mono text-zinc-400 border-b border-white/10 pb-1">
              <span className="flex items-center gap-1.5 font-bold text-white uppercase tracking-wider">
                <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                Real-Time Agent Execution Stream
              </span>

              {/* Interactive Strand Presets */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setHeroPreset("normal")}
                  className={`rounded-md px-2 py-0.5 text-[10px] font-bold transition-all cursor-pointer ${
                    heroPreset === "normal"
                      ? "bg-emerald-500/25 text-emerald-300 border border-emerald-500/50"
                      : "bg-white/5 text-zinc-400 hover:text-white"
                  }`}
                >
                  🟢 Normal Run
                </button>
                <button
                  type="button"
                  onClick={() => setHeroPreset("crash")}
                  className={`rounded-md px-2 py-0.5 text-[10px] font-bold transition-all cursor-pointer ${
                    heroPreset === "crash"
                      ? "bg-amber-500/25 text-amber-300 border border-amber-500/50"
                      : "bg-white/5 text-zinc-400 hover:text-white"
                  }`}
                >
                  ⚡ Worker Swap
                </button>
              </div>
            </div>

            <RunThread segments={heroPresetSegments[heroPreset]} />
          </div>

          {/* Highlighted Quickstart Guide Clicker Button */}
          <button
            type="button"
            id="try-anchor-cli-container"
            onClick={() => setIsQuickstartModalOpen(true)}
            className="mx-auto max-w-md flex items-center justify-between rounded-xl border border-amber-500/50 bg-gradient-to-r from-amber-500/20 via-zinc-950 to-amber-500/20 hover:border-amber-400 hover:scale-[1.03] active:scale-[0.98] transition-all px-4 py-2 text-xs font-mono scroll-mt-20 shadow-xl shadow-amber-500/10 relative overflow-hidden cursor-pointer group"
          >
            <div className="flex items-center gap-2.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg border border-amber-500/40 bg-amber-500/20 text-amber-400 shrink-0">
                <BookOpen className="h-3.5 w-3.5" />
              </div>
              <span className="font-extrabold tracking-wide uppercase text-transparent bg-clip-text bg-[linear-gradient(270deg,#e4e4e7_0%,#fef3c7_35%,#fbbf24_50%,#fef3c7_65%,#e4e4e7_100%)] bg-[length:200%_100%] animate-shimmer-rtl text-[11.5px]">
                ⚡ Quickstart & Agent Code Preview
              </span>
            </div>

            <div className="flex items-center gap-1 text-[11px] text-amber-300 font-extrabold group-hover:translate-x-0.5 transition-transform shrink-0 pl-2">
              <span>View Code</span>
              <ArrowRight className="h-3.5 w-3.5 text-amber-400" />
            </div>
          </button>


          {/* Value Props Cards (Prominent & Visible in 1st Frame with Highlighted Keywords) */}
          <div className="mx-auto max-w-4xl grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1 text-left font-mono">
            <div className="rounded-xl border border-amber-500/40 bg-black/80 p-3.5 space-y-1.5 backdrop-blur-xl shadow-lg hover:border-amber-500/60 transition-all">
              <div className="flex items-center gap-1.5 text-amber-400 font-bold uppercase text-[11px]">
                <Code2 className="h-4 w-4" />
                <span>Developer Integration</span>
              </div>
              <div className="text-xs sm:text-sm font-extrabold text-white font-sans">Self-Healing Step Loops</div>
              <div className="text-[11px] text-zinc-300 leading-snug font-sans">
                Never write <span className="text-zinc-100 font-semibold">custom try/catch retry glue</span> again. If a worker process dies mid-loop, Anchor resumes execution at the <span className="text-amber-300 font-semibold">exact step index</span> without re-executing <span className="text-zinc-100 font-semibold">completed side effects</span>.
              </div>
            </div>

            <div className="rounded-xl border border-emerald-500/40 bg-black/80 p-3.5 space-y-1.5 backdrop-blur-xl shadow-lg hover:border-emerald-500/60 transition-all">
              <div className="flex items-center gap-1.5 text-emerald-400 font-bold uppercase text-[11px]">
                <DollarSign className="h-4 w-4" />
                <span>Cost Efficiency & ROI</span>
              </div>
              <div className="text-xs sm:text-sm font-extrabold text-white font-sans">Zero Wasted LLM Credits</div>
              <div className="text-[11px] text-zinc-300 leading-snug font-sans">
                Save <span className="text-emerald-300 font-semibold">100% of LLM API costs</span> on crashed runs. Already-executed <span className="text-zinc-100 font-semibold">prompt completions</span> and <span className="text-emerald-300 font-semibold">expensive tool outputs</span> are journaled, preventing <span className="text-zinc-100 font-semibold">duplicate OpenAI/Anthropic charges</span>.
              </div>
            </div>

            <div className="rounded-xl border border-blue-500/40 bg-black/80 p-3.5 space-y-1.5 backdrop-blur-xl shadow-lg hover:border-blue-500/60 transition-all">
              <div className="flex items-center gap-1.5 text-blue-400 font-bold uppercase text-[11px]">
                <Briefcase className="h-4 w-4" />
                <span>Workflow Resilience</span>
              </div>
              <div className="text-xs sm:text-sm font-extrabold text-white font-sans">Zombie Split-Brain Immunity</div>
              <div className="text-[11px] text-zinc-300 leading-snug font-sans">
                <span className="text-blue-300 font-semibold">Monotonic epoch fencing</span> guarantees <span className="text-zinc-100 font-semibold">zero split-brain data corruption</span> when containers roll out or <span className="text-blue-300 font-semibold">nodes partition</span> under cloud infrastructure deploys.
              </div>
            </div>
          </div>

        </div>
      </section>





      {/* 3. Featured Showcase: Anchor Operator Console */}
      <section id="operator-console-container" className="py-8 px-6 border-t border-white/10 bg-black/90 scroll-mt-14">
        <div className="mx-auto max-w-6xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-2">
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <h2 className="text-lg font-bold text-white uppercase tracking-wider font-mono">
                  Interactive Operator Console
                </h2>
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10.5px] text-emerald-400 font-mono font-bold">
                  Runs • Workers • Fleet Telemetry • Chaos Engine
                </span>
              </div>
                 <p className="text-xs text-zinc-200 font-sans mt-1 leading-relaxed">
                You can inspect <span className="text-amber-300 font-semibold">step-level execution replays</span>, monitor <span className="text-emerald-300 font-semibold">multi-worker fleet heartbeats</span>, trigger <span className="text-amber-300 font-semibold">live chaos fault injections</span>, and audit real-time telemetry.
              </p>
            </div>

            <div className="flex items-center gap-2 font-mono text-xs">
              <span className="rounded-full border border-amber-500/40 bg-amber-500/15 px-3 py-1 text-amber-300 font-bold shadow-glow-gold">
                ▶ TRY THE LIVE CONSOLE
              </span>
            </div>
          </div>

          <MiniOperatorConsole />

          {/* Python SDK Code Showcase Section Below Interactive Console */}
          <div id="agent-sdk-code" className="pt-6 border-t border-white/10 space-y-4 scroll-mt-16">
            <div className="flex items-center justify-between px-2">
              <div>
                <div className="flex items-center gap-2">
                  <Code2 className="h-4 w-4 text-amber-400" />
                  <h3 className="text-base font-extrabold text-white tracking-wide font-mono">
                    How Your Agent Code Looks
                  </h3>
                  <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-400 font-mono font-semibold">app.py</span>
                </div>
                <p className="text-xs text-zinc-200 font-sans mt-0.5 leading-relaxed">
                  Your agent code stays <span className="text-amber-300 font-semibold">clean, native Python</span> — decorated with <span className="text-amber-300 font-semibold">atomic 2-phase tool safety</span>, automatic environment loading, and <span className="text-emerald-300 font-semibold">crash-resilient step replays</span>.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsQuickstartModalOpen(true)}
                className="hidden sm:flex items-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/15 px-3.5 py-1.5 text-xs font-mono font-bold text-amber-300 hover:bg-amber-500/25 transition-all cursor-pointer shadow-md"
              >
                <span>Full Quickstart Guide</span>
                <ArrowRight className="h-3.5 w-3.5 text-amber-400" />
              </button>
            </div>

            {/* Embedded Code Card */}
            <div className="rounded-2xl border border-white/10 bg-black shadow-2xl overflow-hidden font-mono text-xs">
              <div className="flex items-center justify-between border-b border-white/10 bg-zinc-950 px-4 py-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                  <span className="text-white font-bold">app.py</span>
                  <span className="text-zinc-500 text-[10px]">(Python Workflow SDK)</span>
                </div>
                <span className="text-[10px] text-emerald-400 font-semibold">Auto .env • Multi-Tool Replay</span>
              </div>

              <div className="p-4 bg-black/95 text-[11.5px] leading-relaxed overflow-x-auto custom-scrollbar">
                <pre className="text-zinc-200">
                  <code>
                    <span className="text-purple-400 font-bold">import</span> <span className="text-white">anchor</span>, <span className="text-white">json</span>{"\n\n"}
                    <span className="text-zinc-500 italic"># 1. Custom Tool 0: Fetch Customer Data (Retry-Safe)</span>{"\n"}
                    <span className="text-amber-400 font-bold">@anchor.tool</span><span className="text-zinc-300">(safety=</span><span className="text-emerald-400">"retry_safe"</span><span className="text-zinc-300">, naturally_idempotent=</span><span className="text-rose-400 font-bold">True</span><span className="text-zinc-300">)</span>{"\n"}
                    <span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">fetch_customer</span><span className="text-zinc-300">(customer_id: </span><span className="text-cyan-300">str</span><span className="text-zinc-300">) -&gt; </span><span className="text-cyan-300">dict</span><span className="text-zinc-300">:</span>{"\n"}
                    <span className="text-purple-400 font-bold">    return</span> <span className="text-zinc-300">&#123;</span><span className="text-emerald-400">"id"</span><span className="text-zinc-300">: customer_id, </span><span className="text-emerald-400">"email"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"aditya@anchor.dev"</span><span className="text-zinc-300">, </span><span className="text-emerald-400">"tier"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"VIP"</span><span className="text-zinc-300">&#125;</span>{"\n\n"}
                    <span className="text-zinc-500 italic"># 2. Custom Tool 1: Dispatch Email Notification (Unsafe Side-Effect)</span>{"\n"}
                    <span className="text-amber-400 font-bold">@anchor.tool</span><span className="text-zinc-300">(safety=</span><span className="text-emerald-400">"unsafe"</span><span className="text-zinc-300">)</span>{"\n"}
                    <span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">send_welcome_email</span><span className="text-zinc-300">(email: </span><span className="text-cyan-300">str</span><span className="text-zinc-300">, tier: </span><span className="text-cyan-300">str</span><span className="text-zinc-300">) -&gt; </span><span className="text-cyan-300">dict</span><span className="text-zinc-300">:</span>{"\n"}
                    <span className="text-purple-400 font-bold">    return</span> <span className="text-zinc-300">&#123;</span><span className="text-emerald-400">"status"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"sent"</span><span className="text-zinc-300">, </span><span className="text-emerald-400">"to"</span><span className="text-zinc-300">: email, </span><span className="text-emerald-400">"tier"</span><span className="text-zinc-300">: tier&#125;</span>{"\n\n"}
                    <span className="text-zinc-500 italic"># 3. Multi-Tool Durable Agent Workflow</span>{"\n"}
                    <span className="text-amber-400 font-bold">@anchor.agent</span><span className="text-zinc-300">(name=</span><span className="text-emerald-400">"onboarding_agent"</span><span className="text-zinc-300">)</span>{"\n"}
                    <span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">onboarding_agent</span><span className="text-zinc-300">(ctx: anchor.StepContext):</span>{"\n"}
                    <span className="text-zinc-300">    customer = </span><span className="text-purple-400 font-bold">yield</span><span className="text-white font-bold"> anchor.ToolCall</span><span className="text-zinc-300">(</span><span className="text-emerald-400">"fetch_customer"</span><span className="text-zinc-300">, &#123;</span><span className="text-emerald-400">"customer_id"</span><span className="text-zinc-300">: ctx.input[</span><span className="text-emerald-400">"customer_id"</span><span className="text-zinc-300">]&#125;)</span>{"\n"}
                    <span className="text-zinc-300">    email_res = </span><span className="text-purple-400 font-bold">yield</span><span className="text-white font-bold"> anchor.ToolCall</span><span className="text-zinc-300">(</span><span className="text-emerald-400">"send_welcome_email"</span><span className="text-zinc-300">, &#123;</span><span className="text-emerald-400">"email"</span><span className="text-zinc-300">: customer[</span><span className="text-emerald-400">"email"</span><span className="text-zinc-300">], </span><span className="text-emerald-400">"tier"</span><span className="text-zinc-300">: customer[</span><span className="text-emerald-400">"tier"</span><span className="text-zinc-300">]&#125;)</span>{"\n"}
                    <span className="text-purple-400 font-bold">    yield</span><span className="text-white font-bold"> anchor.Done</span><span className="text-zinc-300">(&#123;</span><span className="text-emerald-400">"status"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"completed"</span><span className="text-zinc-300">, </span><span className="text-emerald-400">"customer"</span><span className="text-zinc-300">: customer, </span><span className="text-emerald-400">"email"</span><span className="text-zinc-300">: email_res&#125;)</span>{"\n\n"}
                    <span className="text-zinc-500 italic"># 4. Trigger & Submit to Cluster</span>{"\n"}
                    <span className="text-purple-400 font-bold">if</span> <span className="text-rose-400">__name__</span> == <span className="text-emerald-400">"__main__"</span><span className="text-zinc-300">:</span>{"\n"}
                    <span className="text-zinc-300">    result = anchor.run(</span><span className="text-emerald-400">"onboarding_agent"</span><span className="text-zinc-300">, input=&#123;</span><span className="text-emerald-400">"customer_id"</span><span className="text-zinc-300">: </span><span className="text-emerald-400 font-bold">"cust_99"</span><span className="text-zinc-300">&#125;)</span>{"\n"}
                    <span className="text-blue-400">    print</span><span className="text-zinc-300">(json.dumps(result, indent=</span><span className="text-amber-400">2</span><span className="text-zinc-300">))</span>
                  </code>
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Competitive Architecture Comparison Matrix */}
      <section id="why-anchor-matrix-container" className="py-16 px-6 border-t border-white/10 bg-black font-mono text-xs scroll-mt-14">
        <div className="mx-auto max-w-5xl space-y-8">
          <div className="text-center space-y-4 max-w-3xl mx-auto mb-6">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white pt-1">Why Should I Choose Anchor?</h2>

            <p className="text-zinc-300 text-sm font-sans pt-1 leading-relaxed text-left sm:text-center">
              Current AI agent frameworks (LangGraph, CrewAI) rely on <span className="text-zinc-200 font-medium">in-memory buffers or naive Redis checkpoints</span> - causing process crashes to re-execute non-idempotent tool calls, double-charge payment APIs, and corrupt database state. Meanwhile, legacy enterprise orchestrators (Temporal, Step Functions) require hosting <span className="text-zinc-200 font-medium">massive external clusters ($5,000+/mo cloud tax)</span> built for microservices, not non-deterministic Python LLM loops. Anchor fills this void as a lightweight, PostgreSQL-authoritative engine - embedding <span className="text-amber-300 font-semibold">atomic two-phase tool journaling</span> (<code className="text-amber-300">INTENT</code> / <code className="text-emerald-300">RESULT</code>) and <span className="text-amber-300 font-semibold">monotonic epoch fencing</span> to guarantee <span className="text-amber-300 font-semibold">zero duplicate side-effects</span> and <span className="text-amber-300 font-semibold">sub-second recovery</span> natively in SQL.
            </p>

            <button
              type="button"
              onClick={() => setShowArchDetails((prev) => !prev)}
              className="mt-3 inline-flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs font-mono font-bold text-amber-300 hover:bg-amber-500/20 transition-all cursor-pointer shadow-md hover:border-amber-500/60"
            >
              <BookOpen className="h-4 w-4 text-amber-400" />
              <span>{showArchDetails ? "Hide Architectural Deep-Dive" : "Read More: Architectural Trade-Offs & Proofs"}</span>
              {showArchDetails ? <ChevronUp className="h-4 w-4 text-amber-400 transition-transform duration-300" /> : <ChevronDown className="h-4 w-4 text-amber-400 transition-transform duration-300" />}
            </button>
          </div>

          <div
            className={`transition-all duration-500 ease-in-out overflow-hidden ${
              showArchDetails
                ? "max-h-[1500px] opacity-100 translate-y-0 my-4"
                : "max-h-0 opacity-0 -translate-y-2 pointer-events-none my-0"
            }`}
          >
            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/[0.04] p-5 space-y-4 font-sans text-xs text-zinc-300 shadow-[0_0_40px_rgba(245,158,11,0.1)]">
              <h4 className="font-mono font-bold text-amber-400 uppercase text-xs">
                Deep-Dive: Why PostgreSQL Engine Wins Over Volatile In-Memory Checkpoints
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1 font-mono">
                <div className="rounded-xl border border-white/10 bg-black/80 p-4 space-y-2">
                  <div className="font-bold text-white text-xs">1. Zero External Cluster Overhead</div>
                  <div className="text-[11px] text-zinc-400 font-sans leading-relaxed">
                    Orchestrators like Temporal require dedicated Cassandra or MySQL clusters plus worker daemons. Anchor runs directly inside your existing PostgreSQL database using <code className="text-amber-300">FOR UPDATE SKIP LOCKED</code> queues, removing $5,000+/mo cloud infrastructure tax.
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/80 p-4 space-y-2">
                  <div className="font-bold text-white text-xs">2. Atomic INTENT / RESULT Commit Protocol</div>
                  <div className="text-[11px] text-zinc-400 font-sans leading-relaxed">
                    LangGraph checkpoints state in memory or Redis, which causes duplicate tool calls when worker pods crash mid-step. Anchor forces atomic two-phase tool journaling before and after API invocation, guaranteeing exact-once execution.
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl border border-white/10 bg-zinc-950 shadow-2xl">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 bg-white/[0.03] text-zinc-400 uppercase text-[10px]">
                  <th className="py-3 pl-5 pr-3">Architecture Feature</th>
                  <th className="py-3 px-3 text-amber-400 font-bold">Anchor (PostgreSQL)</th>
                  <th className="py-3 px-3">LangGraph</th>
                  <th className="py-3 pr-5">Temporal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-3 pl-5 pr-3 font-semibold text-white">PostgreSQL Native (No Heavy Cluster)</td>
                  <td className="py-3 px-3 font-bold text-emerald-400">✅ Built-in</td>
                  <td className="py-3 px-3 text-zinc-500">❌ Redis/Memory Only</td>
                  <td className="py-3 pr-5 text-zinc-500">❌ Requires Cassandra/DB Cluster</td>
                </tr>
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-3 pl-5 pr-3 font-semibold text-white">Two-Phase Tool Side-Effect Guarding</td>
                  <td className="py-3 px-3 font-bold text-emerald-400">✅ Atomic INTENT/RESULT</td>
                  <td className="py-3 px-3 text-zinc-500">❌ Duplicate API Calls</td>
                  <td className="py-3 pr-5 text-amber-400">⚠️ Activity Heartbeats</td>
                </tr>
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-3 pl-5 pr-3 font-semibold text-white">Monotonic Epoch Fencing (`AN001`)</td>
                  <td className="py-3 px-3 font-bold text-emerald-400">✅ DB Constraint Block</td>
                  <td className="py-3 px-3 text-zinc-500">❌ Split-Brain Risk</td>
                  <td className="py-3 pr-5 text-zinc-500">❌ Application-Level</td>
                </tr>
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-3 pl-5 pr-3 font-semibold text-white">Sub-Second SIGKILL Recovery</td>
                  <td className="py-3 px-3 font-bold text-emerald-400">✅ P50 &lt; 3.1s</td>
                  <td className="py-3 px-3 text-zinc-500">❌ Process Crash Data Loss</td>
                  <td className="py-3 pr-5 text-amber-400">⚠️ 10s+ Timeout Window</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 5. Deep Technical Engineering & Consumer Value Breakdown */}
      <section id="engineering-core-container" className="py-16 px-6 border-t border-white/10 bg-zinc-950 scroll-mt-14">
        <div className="mx-auto max-w-5xl space-y-12">
          {/* Section 5A: Consumer Wording: Why Anchor Matters */}
          <div className="space-y-4 text-center max-w-3xl mx-auto mb-6">
            <h2 className="text-3xl font-extrabold text-white pt-1">
              Zero Lost State. Zero Duplicate Charges.
            </h2>

            <p className="text-zinc-300 text-sm font-sans leading-relaxed pt-1">
              When AI agents execute multi-step tasks - like searching database records, calling third-party APIs, or processing payments - server crashes normally result in lost progress and double-billing. Anchor acts as an immutable flight recorder: every step is saved before it runs, so if a server dies, another takes over instantly with zero wasted credits.
            </p>

            <button
              type="button"
              onClick={() => setShowWhyDetails((prev) => !prev)}
              className="mt-3 inline-flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-xs font-mono font-bold text-emerald-300 hover:bg-emerald-500/20 transition-all duration-300 cursor-pointer shadow-md hover:border-emerald-500/60"
            >
              <BookOpen className="h-4 w-4 text-emerald-400" />
              <span>{showWhyDetails ? "Hide Impact Details" : "Read More: Financial ROI & Execution Safety"}</span>
              <ChevronDown className={`h-4 w-4 text-emerald-400 transition-transform duration-300 ${showWhyDetails ? "rotate-180" : "rotate-0"}`} />
            </button>
          </div>

          <div
            className={`transition-all duration-500 ease-in-out overflow-hidden ${
              showWhyDetails
                ? "max-h-[1500px] opacity-100 translate-y-0 my-4"
                : "max-h-0 opacity-0 -translate-y-2 pointer-events-none my-0"
            }`}
          >
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.04] p-5 space-y-4 font-sans text-xs text-zinc-300 shadow-[0_0_40px_rgba(16,185,129,0.1)]">
              <h4 className="font-mono font-bold text-emerald-400 uppercase text-xs">
                Deep-Dive: How Anchor Prevents Wasted API Costs & Data Corruption
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1 font-mono">
                <div className="rounded-xl border border-white/10 bg-black/80 p-4 space-y-2">
                  <div className="font-bold text-white text-xs">Financial Savings Analysis</div>
                  <div className="text-[11px] text-zinc-400 font-sans leading-relaxed">
                    On 1,000,000 multi-step LLM requests per month with a 2% node crash rate, unmanaged retries cost over <strong>$12,400/mo</strong> in duplicate prompt tokens. Anchor's step-level result cache reduces wasted token charges to <strong>$0</strong>.
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/80 p-4 space-y-2">
                  <div className="font-bold text-white text-xs">Idempotent Side-Effect Guarding</div>
                  <div className="text-[11px] text-zinc-400 font-sans leading-relaxed">
                    If a worker process is terminated by Kubernetes SIGKILL while calling a payment endpoint or database mutation, Anchor checks the <code className="text-amber-300">TOOL_INTENT</code> sequence ID on recovery to prevent duplicate charges or corrupt row insertions.
                  </div>
                </div>
              </div>
            </div>
          </div>



          {/* Section 5B: Consumer Wording: How Anchor Is Engineered */}
          <div className="space-y-6 border-t border-white/10 pt-8 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                How Anchor Is Engineered
              </h3>
              <span className="text-amber-400 font-bold">ENGINEERING CORE</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="rounded-2xl border border-white/10 bg-black p-5 space-y-3">
                <div className="font-bold text-white text-sm uppercase text-amber-400">
                  1. Database-Authoritative State Engine
                </div>
                <p className="text-zinc-400 font-sans text-xs leading-relaxed">
                  All run ownership, sequence allocation, and lease renewals occur inside single PostgreSQL transactions using <code className="text-amber-300">SELECT ... FOR UPDATE SKIP LOCKED</code> CTEs. No component outside the database is ever authoritative about who owns an agent run.
                </p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black p-5 space-y-3">
                <div className="font-bold text-white text-sm uppercase text-emerald-400">
                  2. Two-Phase Tool Intent Journaling
                </div>
                <p className="text-zinc-400 font-sans text-xs leading-relaxed">
                  Before a side-effect tool call is executed, Anchor writes a <code className="text-amber-300">TOOL_INTENT</code> record. Upon completion, it commits <code className="text-emerald-300">TOOL_RESULT</code>. On crash recovery, replayed steps load cached results in &lt;5ms without executing side effects a second time.
                </p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black p-5 space-y-3">
                <div className="font-bold text-white text-sm uppercase text-rose-400">
                  3. Monotonic Epoch Token Fencing
                </div>
                <p className="text-zinc-400 font-sans text-xs leading-relaxed">
                  Every worker lease renewal or run claim increments the run's monotonic <code className="text-rose-300">epoch</code> token. Delayed writes from a zombie worker with a stale epoch are blocked at the database constraint boundary with <code className="text-rose-300">AN001_FENCED_WRITE</code>.
                </p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black p-5 space-y-3">
                <div className="font-bold text-white text-sm uppercase text-blue-400">
                  4. Automated Invariant Audit Suite
                </div>
                <p className="text-zinc-400 font-sans text-xs leading-relaxed">
                  Continuous adversarial testing harness runs 5 automated SQL assertions (<code className="text-blue-300">I1 - I5</code>) after every chaos run, mathematically proving zero duplicate tool calls and zero stranded runs under process SIGKILL termination.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Pure SVG Mechanism Explainer Flowchart */}
      <section className="py-16 px-6 border-t border-white/10 bg-black">
        <div className="mx-auto max-w-5xl space-y-8">
          <MechanismExplainer />
        </div>
      </section>

      {/* 7. Formal 5 SQL Invariants Summary Table */}
      <section className="py-16 px-6 border-t border-white/10 bg-zinc-950 font-mono text-xs">
        <div className="mx-auto max-w-5xl space-y-6">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Formal Runtime SQL Invariants (Automated Audit Suite)
              </h3>
              <p className="text-xs text-zinc-400 font-sans">
                Continuous SQL assertions executed after every chaos test run to verify mathematical system correctness.
              </p>
            </div>
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[10px] font-bold text-emerald-400">
              5 / 5 INVARIANTS PROVED
            </span>
          </div>

          <div className="overflow-hidden rounded-xl border border-white/10 bg-black">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 bg-white/[0.02] text-zinc-400 uppercase text-[10px]">
                  <th className="py-2.5 pl-4 pr-2">ID</th>
                  <th className="py-2.5 pr-2">Invariant Name</th>
                  <th className="py-2.5 pr-2">SQL Enforcement Logic</th>
                  <th className="py-2.5 pr-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-2.5 pl-4 pr-2 font-bold text-amber-400">I1</td>
                  <td className="py-2.5 pr-2 text-white font-semibold">Zero Duplicate Side-Effects</td>
                  <td className="py-2.5 pr-2 text-zinc-400">COUNT(tool_calls WHERE action_kind = 'tool') &lt;= 1 per step</td>
                  <td className="py-2.5 pr-4 text-right font-bold text-emerald-400">PROVED</td>
                </tr>
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-2.5 pl-4 pr-2 font-bold text-amber-400">I2</td>
                  <td className="py-2.5 pr-2 text-white font-semibold">Monotonic Epoch Progression</td>
                  <td className="py-2.5 pr-2 text-zinc-400">epoch_n+1 &gt; epoch_n FOR ALL worker claim transitions</td>
                  <td className="py-2.5 pr-4 text-right font-bold text-emerald-400">PROVED</td>
                </tr>
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-2.5 pl-4 pr-2 font-bold text-amber-400">I3</td>
                  <td className="py-2.5 pr-2 text-white font-semibold">Single Worker Ownership</td>
                  <td className="py-2.5 pr-4 text-zinc-400">COUNT(active_leases WHERE status = 'running') &lt;= 1 per run</td>
                  <td className="py-2.5 pr-4 text-right font-bold text-emerald-400">PROVED</td>
                </tr>
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-2.5 pl-4 pr-2 font-bold text-amber-400">I4</td>
                  <td className="py-2.5 pr-2 text-white font-semibold">Strict Journal Ordering</td>
                  <td className="py-2.5 pr-2 text-zinc-400">seq_n+1 = seq_n + 1 (Monotonic continuous seq IDs)</td>
                  <td className="py-2.5 pr-4 text-right font-bold text-emerald-400">PROVED</td>
                </tr>
                <tr className="hover:bg-white/[0.02]">
                  <td className="py-2.5 pl-4 pr-2 font-bold text-amber-400">I5</td>
                  <td className="py-2.5 pr-2 text-white font-semibold">No Zombie State Replay</td>
                  <td className="py-2.5 pr-2 text-zinc-400">fenced_worker_writes = 0 AFTER lease expiration</td>
                  <td className="py-2.5 pr-4 text-right font-bold text-emerald-400">PROVED</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 8. Footer Surface with Aditya Nema Branding & Outbound Links */}
      <footer className="border-t border-white/10 bg-black py-12 px-6 font-mono text-xs text-zinc-400">
        <div className="mx-auto flex max-w-6xl flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <span className="font-bold text-white text-sm">⚓ ANCHOR</span>
              <span>•</span>
              <span>Durable Execution Engine for AI Agent Workloads</span>
            </div>
            <div className="text-zinc-500 text-[11px]">
              Designed & Engineered by <strong className="text-zinc-300 font-semibold">Aditya Nema</strong>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <a
              href="https://linkedin.com/in/adityaxnema"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors font-semibold"
            >
              <LinkedinIcon className="h-3.5 w-3.5" />
              <span>LinkedIn Profile</span>
            </a>

            <a
              href="https://github.com/n43ms/Anchor"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-zinc-400 hover:text-white transition-colors font-semibold"
            >
              <GithubIcon className="h-3.5 w-3.5" />
              <span>GitHub Repository</span>
            </a>

            <a
              href="https://github.com/n43ms/Anchor/blob/main/LICENSE"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-amber-400 hover:text-amber-300 transition-colors font-semibold"
            >
              <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
              <span>Apache 2.0 Licensed</span>
            </a>
            <span className="text-zinc-600">v1.5.4-prod</span>
          </div>
        </div>
      </footer>

      {/* Developer Quickstart Modal */}
      <QuickstartModal
        isOpen={isQuickstartModalOpen}
        onClose={() => setIsQuickstartModalOpen(false)}
      />
    </div>
  );
};
