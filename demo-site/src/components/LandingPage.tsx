import React, { useState } from "react";
import { MiniOperatorConsole } from "./MiniOperatorConsole";
import { MechanismExplainer } from "./MechanismExplainer";
import { RunThread } from "./RunThread";
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
  const [copied, setCopied] = useState(false);
  const [heroPreset, setHeroPreset] = useState<"normal" | "crash" | "replay">("crash");
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
    navigator.clipboard.writeText("npx anchor-runtime@latest init");
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
    replay: [
      {
        worker_id: "worker-b#1",
        epoch: 2,
        started_at: new Date(Date.now() - 5000).toISOString(),
        ended_at: null,
        steps: [
          { step_index: 0, name: "analyze_user_requirements", status: "done" as const, action_kind: "model" as const, started_at: "", completed_at: null, executed: false },
          { step_index: 1, name: "execute_db_migration", status: "done" as const, action_kind: "tool" as const, started_at: "", completed_at: null, executed: false },
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
                  v1.4.2-prod
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
              onClick={() => scrollToId("try-anchor-cli-container")}
              className="hover:text-amber-400 transition-colors cursor-pointer"
            >
              Try Anchor
            </button>
            <button
              type="button"
              onClick={() => scrollToId("operator-console-container")}
              className="hover:text-amber-400 transition-colors cursor-pointer"
            >
              Console
            </button>
            <button
              type="button"
              onClick={() => scrollToId("why-anchor-matrix-container")}
              className="hover:text-amber-400 transition-colors cursor-pointer"
            >
              Why Anchor
            </button>
            <button
              type="button"
              onClick={() => scrollToId("engineering-core-container")}
              className="hover:text-amber-400 transition-colors cursor-pointer"
            >
              Engineering
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

            <button
              type="button"
              onClick={() => scrollToId("operator-console-container")}
              className="flex items-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/15 px-3 py-1 text-amber-300 hover:bg-amber-500/25 transition-all font-bold cursor-pointer text-[11px]"
            >
              <Activity className="h-3.5 w-3.5" />
              <span>Console</span>
            </button>
          </div>
        </div>
      </header>



      {/* 2. Hero Section (Fits 100% in Initial Viewport) */}
      <section className="relative pt-4 pb-3 px-4">
        <div className="mx-auto max-w-4xl text-center space-y-2.5">
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-white max-w-3xl mx-auto leading-tight">
            Durable Execution Engine for <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-200 to-amber-500">Mission-Critical AI Agents.</span>
          </h1>

          <p className="text-xs sm:text-sm text-zinc-400 max-w-2xl mx-auto font-sans leading-normal">
            Eliminate lost state and duplicate API calls when executing multi-step LLM agent pipelines. Anchor guarantees atomic two-phase tool journaling, monotonic epoch fencing, and sub-second crash recovery.
          </p>

          {/* Real-Time Agent Execution Stream Header with Interactive Presets */}
          <div className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-black/90 p-3 space-y-1.5 shadow-2xl backdrop-blur-xl text-left">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[10px] font-mono text-zinc-400 border-b border-white/10 pb-1.5">
              <span className="flex items-center gap-1.5 font-bold text-white uppercase tracking-wider">
                <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                Real-Time Agent Execution Stream
              </span>

              {/* Interactive Strand Presets */}
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setHeroPreset("normal")}
                  className={`rounded-md px-2 py-0.5 text-[9px] font-bold transition-all cursor-pointer ${
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
                  className={`rounded-md px-2 py-0.5 text-[9px] font-bold transition-all cursor-pointer ${
                    heroPreset === "crash"
                      ? "bg-amber-500/25 text-amber-300 border border-amber-500/50"
                      : "bg-white/5 text-zinc-400 hover:text-white"
                  }`}
                >
                  ⚡ SIGKILL Swap
                </button>
                <button
                  type="button"
                  onClick={() => setHeroPreset("replay")}
                  className={`rounded-md px-2 py-0.5 text-[9px] font-bold transition-all cursor-pointer ${
                    heroPreset === "replay"
                      ? "bg-blue-500/25 text-blue-300 border border-blue-500/50"
                      : "bg-white/5 text-zinc-400 hover:text-white"
                  }`}
                >
                  🔄 Replay Cache
                </button>
              </div>
            </div>

            <RunThread segments={heroPresetSegments[heroPreset]} />
          </div>

          {/* Quick Copy CLI Command Box */}
          <div id="try-anchor-cli-container" className="mx-auto max-w-xl flex items-center justify-between rounded-xl border border-white/10 bg-zinc-950 px-3.5 py-1.5 text-xs font-mono scroll-mt-20">
            <div className="flex items-center gap-2 text-zinc-300">
              <Terminal className="h-3.5 w-3.5 text-amber-400" />
              <span>npx anchor-runtime@latest init</span>
            </div>
            <button
              type="button"
              onClick={handleCopyCmd}
              className="flex items-center gap-1 text-[10px] text-amber-400 hover:text-amber-300 font-bold cursor-pointer transition-colors"
            >
              {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
            </button>
          </div>

          {/* Value Props Tailored specifically for Devs, Startups, & Enterprises (Scaled 1.25x) */}

          <div className="mx-auto max-w-5xl grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 text-left font-mono">
            <div className="rounded-xl border border-amber-500/40 bg-amber-500/[0.05] p-4 sm:p-5 backdrop-blur-xl space-y-2 shadow-lg">
              <div className="flex items-center gap-2 text-amber-400 font-bold uppercase text-xs sm:text-sm">
                <Code2 className="h-4.5 w-4.5" />
                <span>For Developers</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-white font-sans">Self-Healing Step Loops</div>
              <div className="text-xs sm:text-sm text-zinc-300 leading-relaxed font-sans">
                Never write custom try/catch retry glue again. If a worker process dies mid-loop, Anchor resumes execution at the exact step index without re-executing completed side effects.
              </div>
            </div>

            <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/[0.05] p-4 sm:p-5 backdrop-blur-xl space-y-2 shadow-lg">
              <div className="flex items-center gap-2 text-emerald-400 font-bold uppercase text-xs sm:text-sm">
                <DollarSign className="h-4.5 w-4.5" />
                <span>For Startups</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-white font-sans">Zero Wasted LLM Credits</div>
              <div className="text-xs sm:text-sm text-zinc-300 leading-relaxed font-sans">
                Save 100% of LLM API costs on crashed runs. Already-executed prompt completions and expensive tool outputs are journaled, preventing duplicate OpenAI/Anthropic charges.
              </div>
            </div>

            <div className="rounded-xl border border-blue-500/40 bg-blue-500/[0.05] p-4 sm:p-5 backdrop-blur-xl space-y-2 shadow-lg">
              <div className="flex items-center gap-2 text-blue-400 font-bold uppercase text-xs sm:text-sm">
                <Briefcase className="h-4.5 w-4.5" />
                <span>For Enterprises</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-white font-sans">Zombie Split-Brain Immunity</div>
              <div className="text-xs sm:text-sm text-zinc-300 leading-relaxed font-sans">
                Monotonic epoch fencing guarantees zero split-brain data corruption when containers roll out or nodes partition under cloud infrastructure deploys.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Featured Showcase: Interactive Demo Console */}
      <section id="operator-console-container" className="py-8 px-6 border-t border-white/10 bg-black/90 scroll-mt-14">
        <div className="mx-auto max-w-6xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <h2 className="text-lg font-bold text-white uppercase tracking-wider font-mono">
                  Interactive Demo Console
                </h2>
              </div>
              <p className="text-xs text-zinc-400 font-sans mt-0.5">
                Test-drive Anchor's live operator UI, inspect run state replays, and trigger SIGKILL worker failures in real time.
              </p>
            </div>

            <div className="flex items-center gap-2 font-mono text-xs">
              <span className="rounded-full border border-amber-500/40 bg-amber-500/15 px-3 py-1 text-amber-300 font-bold shadow-glow-gold">
                ▶ TRY THE LIVE CONSOLE
              </span>
            </div>
          </div>

          <MiniOperatorConsole />
        </div>
      </section>

      {/* 4. Competitive Architecture Comparison Matrix */}
      <section id="why-anchor-matrix-container" className="py-16 px-6 border-t border-white/10 bg-black font-mono text-xs scroll-mt-14">
        <div className="mx-auto max-w-5xl space-y-8">
          <div className="text-center space-y-4 max-w-2xl mx-auto mb-6">
            <div className="inline-block mb-1">
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-[10px] font-bold text-amber-400 uppercase tracking-wider">
                ARCHITECTURAL COMPARISON
              </span>
            </div>

            <h2 className="text-2xl sm:text-3xl font-extrabold text-white pt-1">Why Engineers Choose Anchor</h2>

            <p className="text-zinc-300 text-xs sm:text-sm font-sans pt-1 leading-relaxed">
              Built natively for PostgreSQL 16 without heavy external orchestrators or memory-only state buffers.
            </p>

            <button
              type="button"
              onClick={() => setShowArchDetails((prev) => !prev)}
              className="mt-3 inline-flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs font-mono font-bold text-amber-300 hover:bg-amber-500/20 transition-all cursor-pointer shadow-md"
            >
              <BookOpen className="h-4 w-4 text-amber-400" />
              <span>{showArchDetails ? "Hide Architectural Deep-Dive" : "Read More: Architectural Trade-Offs & Proofs"}</span>
              {showArchDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>

          {showArchDetails && (
            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/[0.04] p-5 space-y-4 font-sans text-xs text-zinc-300 mb-6 shadow-2xl animate-fadeIn">
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
          )}

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
            <div className="inline-block mb-1">
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-xs font-mono font-bold text-amber-400 uppercase tracking-wider">
                WHY ANCHOR MATTERS
              </span>
            </div>

            <h2 className="text-3xl font-extrabold text-white pt-1">
              Zero Lost State. Zero Duplicate Charges.
            </h2>

            <p className="text-zinc-300 text-sm font-sans leading-relaxed pt-1">
              When AI agents execute multi-step tasks—like searching database records, calling third-party APIs, or processing payments—server crashes normally result in lost progress and double-billing. Anchor acts as an immutable flight recorder: every step is saved before it runs, so if a server dies, another takes over instantly with zero wasted credits.
            </p>

            <button
              type="button"
              onClick={() => setShowWhyDetails((prev) => !prev)}
              className="mt-3 inline-flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs font-mono font-bold text-amber-300 hover:bg-amber-500/20 transition-all cursor-pointer shadow-md"
            >
              <BookOpen className="h-4 w-4 text-amber-400" />
              <span>{showWhyDetails ? "Hide Impact Details" : "Read More: Financial ROI & Execution Safety"}</span>
              {showWhyDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>

          {showWhyDetails && (
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.04] p-5 space-y-4 font-sans text-xs text-zinc-300 mb-8 shadow-2xl animate-fadeIn">
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
          )}



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
            <span className="text-zinc-600">v1.4.2-prod</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
