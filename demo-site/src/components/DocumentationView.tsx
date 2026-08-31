"use client";

import React, { useState, useEffect } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Code2,
  Cpu,
  Layers,
  ShieldCheck,
  Terminal,
  Zap,
  Check,
  Copy,
  ExternalLink,
  HelpCircle,
  AlertTriangle,
  ArrowLeft,
  Settings,
  Server,
  FileText,
  Lock,
  Sparkles,
  RefreshCw,
  Activity,
  Flame,
  Eye,
  Sliders,
  CheckCircle2,
  Play,
  RotateCcw,
  BarChart3,
  Wrench,
  Database,
  GitBranch,
  Globe,
  Radio,
  LayoutDashboard,
  PieChart,
  SlidersHorizontal,
} from "lucide-react";

interface DocSection {
  id: string;
  title: string;
  category: string;
}

const SECTIONS: DocSection[] = [
  // 1. Getting Started
  { id: "overview", title: "Why Anchor?", category: "1. Getting Started" },
  { id: "quickstart", title: "5-Minute Quickstart & Installation", category: "1. Getting Started" },
  { id: "invariants", title: "The 5 Formal Guarantees (I1 – I5)", category: "1. Getting Started" },

  // 2. Python SDK Reference
  { id: "sdk-tool", title: "Defining Durable Agent Tools (@anchor.tool)", category: "2. Python SDK Reference" },
  { id: "sdk-agent", title: "Writing Durable Workflows (@anchor.agent)", category: "2. Python SDK Reference" },
  { id: "sdk-actions", title: "Workflow Actions (ToolCall, ModelCall, Done) & Execution", category: "2. Python SDK Reference" },

  // 3. Operator Console Manual (Positioned immediately below Python SDK Reference)
  { id: "console-tour", title: "Operator Console Overview & Interface Guide", category: "3. Operator Console Manual" },
  { id: "console-timeline", title: "Run Detail & Timeline Visualizer (Execution Thread)", category: "3. Operator Console Manual" },
  { id: "console-needs-review", title: "Needs Review Queue & Manual Resolution", category: "3. Operator Console Manual" },
  { id: "console-chaos", title: "Chaos Harness & Fault Injection Testing", category: "3. Operator Console Manual" },
  { id: "console-fleet", title: "Fleet Matrix, Deployments & Capacity Tuning", category: "3. Operator Console Manual" },

  // 4. Engine Internals
  { id: "determinism-replay", title: "Deterministic Replay & State Reconstruction", category: "4. Engine Internals" },
  { id: "two-phase-journal", title: "Two-Phase Journaling & Idempotency Derivation", category: "4. Engine Internals" },

  // 5. API & Integration Reference
  { id: "api-reference", title: "REST API Reference & Endpoint Specifications", category: "5. Integrator Reference" },
  { id: "websocket-protocol", title: "WebSocket Live Streaming Protocol", category: "5. Integrator Reference" },
  { id: "sqlstate-errors", title: "System SQLSTATE Error Reference (AN001 – AN004)", category: "5. Integrator Reference" },

  // 6. DevOps & Operations Manual
  { id: "env-guide", title: "Configuration & Step Timeouts", category: "6. DevOps & Operations" },
  { id: "cli-reference", title: "CLI Command Reference (anchor config)", category: "6. DevOps & Operations" },
  { id: "deployment-runbook", title: "Production Deployment & Rolling Migrations", category: "6. DevOps & Operations" },
  { id: "observability-logging", title: "Observability Metrics & Structured Logging", category: "6. DevOps & Operations" },
];

export function DocumentationView({ onClose }: { onClose: () => void }) {
  const [activeSection, setActiveSection] = useState("overview");
  const [osTab, setOsTab] = useState<"mac" | "win">("win");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // Active scroll tracking for left sidebar navigation
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { rootMargin: "-15% 0px -70% 0px", threshold: 0.1 }
    );

    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="h-screen w-screen bg-[#07070a] text-zinc-200 font-sans flex flex-col overflow-hidden selection:bg-amber-500/20 selection:text-amber-300">
      {/* Signature High-Contrast Vibrant Gold Header Bar */}
      <header className="shrink-0 z-50 flex items-center justify-between border-b border-amber-500/30 bg-black/90 px-6 py-3.5 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={onClose}
            className="flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3.5 py-1.5 text-xs font-mono text-amber-300 font-bold hover:bg-amber-500/20 hover:border-amber-400 transition-all cursor-pointer shadow-sm"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Main Site</span>
          </button>
          <div className="h-4 w-px bg-amber-500/30" />
          <div className="flex items-center gap-2.5 font-mono text-xs">
            <span className="font-extrabold text-amber-400 tracking-wider uppercase text-sm">ANCHOR RUNTIME ENGINE</span>
            <span className="text-zinc-500">•</span>
            <span className="text-zinc-300 font-semibold">User Manual & Developer Guide</span>
            <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-0.5 text-[10px] text-amber-400 font-mono font-bold">
              v1.6.0-prod
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <a
            href="https://github.com/n43ms/Anchor"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-zinc-300 hover:text-white hover:border-amber-500/40 transition-all font-semibold"
          >
            <Code2 className="h-3.5 w-3.5 text-amber-400" />
            <span>GitHub Repository</span>
            <ExternalLink className="h-3 w-3 text-zinc-500" />
          </a>
        </div>
      </header>

      {/* Main Container - Fixed Left Sidebar & Independent Scrolling Right Main */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden max-w-[1600px] w-full mx-auto">
        {/* Mobile Section Navigation Bar (< 768px) */}
        <div className="md:hidden flex overflow-x-auto custom-scrollbar bg-black/90 border-b border-amber-500/20 px-3 py-2 gap-1.5 shrink-0 z-20">
          {SECTIONS.map((sec) => (
            <button
              key={sec.id}
              type="button"
              onClick={() => scrollToSection(sec.id)}
              className="px-3 py-1 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs font-mono whitespace-nowrap shrink-0 hover:bg-amber-500/20 transition-colors"
            >
              {sec.title}
            </button>
          ))}
        </div>

        {/* Permanently Fixed Left Sidebar Navigation */}
        <aside className="w-80 shrink-0 border-r border-amber-500/15 p-5 space-y-6 h-full overflow-y-auto custom-scrollbar bg-[#07070a] hidden md:block">
          <div>
            <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-amber-400 mb-3 px-2">
              Documentation Index
            </div>
            <nav className="space-y-4">
              {Array.from(new Set(SECTIONS.map((s) => s.category))).map((category) => (
                <div key={category} className="space-y-1">
                  <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-400/80 px-2 pt-1">
                    {category}
                  </div>
                  {SECTIONS.filter((s) => s.category === category).map((section) => (
                    <button
                      key={section.id}
                      type="button"
                      onClick={() => scrollToSection(section.id)}
                      className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-2 ${
                        activeSection === section.id
                          ? "bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 shadow-sm"
                          : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${activeSection === section.id ? "bg-amber-400" : "bg-zinc-700"}`} />
                      <span className="truncate">{section.title}</span>
                    </button>
                  ))}
                </div>
              ))}
            </nav>
          </div>
        </aside>

        {/* Independent Right Scrollable Content */}
        <main className="flex-1 p-6 md:p-12 space-y-16 max-w-4xl min-w-0 h-full overflow-y-auto overflow-x-hidden custom-scrollbar">
          
          {/* SECTION 1: Overview */}
          <section id="overview" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Sparkles className="h-3.5 w-3.5 text-zinc-400" />
              <span>Getting Started</span>
            </div>
            <h1 className="text-2xl font-bold text-white font-mono tracking-tight">
              Why Anchor?
            </h1>
            <p className="text-sm text-zinc-300 leading-relaxed font-sans">
              Modern AI applications build multi-step agent workflows that execute API calls, query databases, generate text, and execute financial transactions. 
              However, traditional stateless worker loops are non-durable. When a worker process experiences an Out-Of-Memory (OOM) kill, container restart, 
              or network outage, all intermediate reasoning states are lost.
            </p>
            <p className="text-sm text-zinc-300 leading-relaxed font-sans">
              Generic queue managers attempt process retries that restart the agent from step 0, double-billing expensive LLM tokens and duplicating critical external side-effects 
              (such as charging customer credit cards twice or sending duplicate emails).
            </p>
            <p className="text-sm text-zinc-300 leading-relaxed font-sans">
              <strong>Anchor</strong> is a Durable Execution Runtime for AI agents. It ensures that when a worker process crashes, 
              a new worker picks up the run from its exact last verified step without repeating completed side-effects, losing state, or re-billing completed model calls.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs pt-2">
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-emerald-400 font-bold">Zero Duplicate Side-Effects</div>
                <p className="text-zinc-400 text-[11px] font-sans">Guarantees that external tools (payments, emails, DB writes) execute exactly once per workflow step.</p>
              </div>
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-sky-400 font-bold">Automatic State Reconstruction</div>
                <p className="text-zinc-400 text-[11px] font-sans">Event log replay instantly populates cached completions without re-querying model providers.</p>
              </div>
            </div>
          </section>

          {/* SECTION 2: Quickstart */}
          <section id="quickstart" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Terminal className="h-3.5 w-3.5 text-zinc-400" />
              <span>Getting Started</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              5-Minute Quickstart & Installation
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Install Anchor runtime and initialize local workspace infrastructure:
            </p>

            {/* OS Selection Tabs */}
            <div className="flex items-center gap-2 border-b border-white/10 pb-2 font-mono text-xs">
              <button
                type="button"
                onClick={() => setOsTab("win")}
                className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer font-bold ${
                  osTab === "win"
                    ? "bg-white/15 text-white border border-white/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Windows (PowerShell)
              </button>
              <button
                type="button"
                onClick={() => setOsTab("mac")}
                className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer font-bold ${
                  osTab === "mac"
                    ? "bg-white/15 text-white border border-white/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                macOS / Linux (Bash / Zsh)
              </button>
            </div>

            {/* Step 1 */}
            <div className="space-y-2 font-mono text-xs">
              <div className="text-zinc-200 font-bold uppercase text-[11px]">Step 1: Install Anchor Package</div>
              <div className="relative rounded-xl border border-white/15 bg-[#090a0d] p-4 text-zinc-200">
                <button
                  type="button"
                  onClick={() => copyToClipboard("pip install anchor-runtime", "qs-1")}
                  className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
                >
                  {copiedCode === "qs-1" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <div className="font-mono text-xs leading-relaxed">
                  <span className="text-purple-400">pip</span> install <span className="text-zinc-100 font-bold">anchor-runtime</span>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="space-y-2 font-mono text-xs">
              <div className="text-zinc-200 font-bold uppercase text-[11px]">Step 2: Initialize Infrastructure</div>
              <div className="relative rounded-xl border border-white/15 bg-[#090a0d] p-4 text-zinc-200">
                <button
                  type="button"
                  onClick={() =>
                    copyToClipboard(
                      osTab === "win" ? "python -m anchor.cli init" : "anchor init",
                      "qs-2"
                    )
                  }
                  className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
                >
                  {copiedCode === "qs-2" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <div className="font-mono text-xs leading-relaxed">
                  {osTab === "win" ? (
                    <>
                      <span className="text-purple-400">python</span> -m anchor.cli <span className="text-emerald-400 font-bold">init</span>
                    </>
                  ) : (
                    <>
                      <span className="text-purple-400">anchor</span> <span className="text-emerald-400 font-bold">init</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="space-y-2 font-mono text-xs">
              <div className="text-zinc-200 font-bold uppercase text-[11px]">Step 3: Start Local Environment</div>
              <div className="relative rounded-xl border border-white/15 bg-[#090a0d] p-4 text-zinc-200">
                <button
                  type="button"
                  onClick={() =>
                    copyToClipboard(
                      osTab === "win" ? "python -m anchor.cli dev" : "anchor dev",
                      "qs-3"
                    )
                  }
                  className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
                >
                  {copiedCode === "qs-3" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <div className="font-mono text-xs leading-relaxed">
                  {osTab === "win" ? (
                    <>
                      <span className="text-purple-400">python</span> -m anchor.cli <span className="text-emerald-400 font-bold">dev</span>
                    </>
                  ) : (
                    <>
                      <span className="text-purple-400">anchor</span> <span className="text-emerald-400 font-bold">dev</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Step 4 */}
            <div className="space-y-2 font-mono text-xs">
              <div className="text-zinc-200 font-bold uppercase text-[11px]">Step 4: Run Agent Script</div>
              <div className="relative rounded-xl border border-white/15 bg-[#090a0d] p-4 text-zinc-200">
                <button
                  type="button"
                  onClick={() => copyToClipboard("python app.py", "qs-4")}
                  className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
                >
                  {copiedCode === "qs-4" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <div className="font-mono text-xs leading-relaxed">
                  <span className="text-purple-400">python</span> app.py
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 3: Invariants */}
          <section id="invariants" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <ShieldCheck className="h-3.5 w-3.5 text-zinc-400" />
              <span>Getting Started</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              The 5 Formal Guarantees (I1 – I5)
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Anchor enforces five core correctness guarantees during workflow execution and recovery:
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-white font-bold text-xs">1. Log Contiguity & Sequence Monotonicity (I1)</div>
                <p className="text-zinc-300 text-xs font-sans">Event sequence numbers form a strictly continuous, 1-indexed sequence with zero gaps or duplicate sequence keys.</p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-white font-bold text-xs">2. Single-Writer Epoch Fencing (I2)</div>
                <p className="text-zinc-300 text-xs font-sans">Database triggers reject writes from stale or timing-out worker processes holding an outdated epoch ID.</p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-white font-bold text-xs">3. Two-Phase Atomic Journaling (I3)</div>
                <p className="text-zinc-300 text-xs font-sans">Side-effecting tools record an intent record before execution and a result record upon completion to prevent duplicate execution.</p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-white font-bold text-xs">4. Deterministic Replay & State Reconstruction (I4)</div>
                <p className="text-zinc-300 text-xs font-sans">Worker recovery replays recorded event logs to reconstruct in-memory state up to the last verified step.</p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-white font-bold text-xs">5. Terminal Reachability & Lease Release (I5)</div>
                <p className="text-zinc-300 text-xs font-sans">Completed, failed, or cancelled workflows release worker ownership leases unconditionally.</p>
              </div>
            </div>
          </section>

          {/* SECTION 4: Defining Durable Agent Tools */}
          <section id="sdk-tool" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <ShieldCheck className="h-3.5 w-3.5 text-zinc-400" />
              <span>Python SDK Reference</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Defining Durable Agent Tools (@anchor.tool)
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Every external function invoked by an agent (APIs, databases, payment gateways, emails) is declared with the <code>@anchor.tool</code> decorator. 
              The decorator defines the tool's crash safety policy:
            </p>

            <div className="rounded-xl border border-white/15 bg-[#090a0d] p-4 sm:p-5 font-mono text-xs text-zinc-200 space-y-1.5 overflow-x-auto">
              <div className="text-zinc-500"># 1. Read-Only / Idempotent Tool (Safe to retry automatically)</div>
              <div><span className="text-purple-400">@anchor.tool</span>(safety=<span className="text-emerald-300">"retry_safe"</span>, naturally_idempotent=<span className="text-purple-400">True</span>)</div>
              <div><span className="text-purple-400">def</span> <span className="text-yellow-200">fetch_customer</span>(customer_id: <span className="text-sky-300">str</span>) -&gt; <span className="text-sky-300">dict</span>:</div>
              <div className="pl-4"><span className="text-purple-400">return</span> &#123;<span className="text-emerald-300">"id"</span>: customer_id, <span className="text-emerald-300">"email"</span>: <span className="text-emerald-300">"aditya@anchor.dev"</span>, <span className="text-emerald-300">"tier"</span>: <span className="text-emerald-300">"VIP"</span>&#125;</div>

              <div className="pt-3 text-zinc-500"># 2. Side-Effecting Tool (Requires manual review if process crashes mid-execution)</div>
              <div><span className="text-purple-400">@anchor.tool</span>(safety=<span className="text-emerald-300">"unsafe"</span>)</div>
              <div><span className="text-purple-400">def</span> <span className="text-yellow-200">send_welcome_email</span>(email: <span className="text-sky-300">str</span>, tier: <span className="text-sky-300">str</span>) -&gt; <span className="text-sky-300">dict</span>:</div>
              <div className="pl-4"><span className="text-purple-400">return</span> &#123;<span className="text-emerald-300">"status"</span>: <span className="text-emerald-300">"sent"</span>, <span className="text-emerald-300">"to"</span>: email, <span className="text-emerald-300">"tier"</span>: tier&#125;</div>
            </div>

            <div className="overflow-hidden rounded-xl border border-white/10 bg-black/60 font-mono text-xs">
              <table className="w-full text-left">
                <thead className="bg-white/5 text-zinc-300 uppercase tracking-wider text-[10px] border-b border-white/10">
                  <tr>
                    <th className="p-3">Safety Policy</th>
                    <th className="p-3">When to Use</th>
                    <th className="p-3">Recovery Behavior</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 text-zinc-300">
                  <tr>
                    <td className="p-3 font-bold text-emerald-400">retry_safe</td>
                    <td className="p-3">Read-only queries, search APIs, or APIs accepting idempotency keys.</td>
                    <td className="p-3">Worker automatically re-executes function upon recovery.</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-sky-400">reconcilable</td>
                    <td className="p-3">Tools with an out-of-band status query callback (`reconcile_fn`).</td>
                    <td className="p-3">Executes status check before deciding whether to re-run.</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-rose-400">unsafe</td>
                    <td className="p-3">Irreversible actions (emails, payments, external API mutations).</td>
                    <td className="p-3">Halts run into Needs Review queue for operator confirmation.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* SECTION 5: Writing Durable Workflows */}
          <section id="sdk-agent" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Layers className="h-3.5 w-3.5 text-zinc-400" />
              <span>Python SDK Reference</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Writing Durable Workflows (@anchor.agent)
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Agent workflows are written as standard Python generator functions decorated with <code>@anchor.agent</code>. 
              Each <code>yield</code> expression pauses execution, allowing the runtime to journal step results and resume seamlessly across worker restarts:
            </p>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The decorated step function is named <code>decide_next_step(ctx: anchor.StepContext)</code>, serving as the canonical entrypoint function called by the Anchor worker loop on each step iteration to evaluate yielded workflow actions.
            </p>

            {/* Canonical yield snippet matching landing page exactly */}
            <div className="relative rounded-xl border border-white/15 bg-[#090a0d] p-4 sm:p-5 font-mono text-xs text-zinc-200 space-y-1.5 overflow-x-auto">
              <button
                type="button"
                onClick={() =>
                  copyToClipboard(
                    `import anchor, json

@anchor.tool(safety="retry_safe", naturally_idempotent=True)
def fetch_customer(customer_id: str) -> dict:
    return {"id": customer_id, "email": "aditya@anchor.dev", "tier": "VIP"}

@anchor.tool(safety="unsafe")
def send_welcome_email(email: str, tier: str) -> dict:
    return {"status": "sent", "to": email, "tier": tier}

@anchor.agent(name="onboarding_agent")
def decide_next_step(ctx: anchor.StepContext):
    customer = yield anchor.ToolCall("fetch_customer", {"customer_id": ctx.input["customer_id"]})
    email_res = yield anchor.ToolCall("send_welcome_email", {"email": customer["email"], "tier": customer["tier"]})
    yield anchor.Done({"status": "completed", "customer": customer, "email": email_res})

if __name__ == "__main__":
    result = anchor.run("onboarding_agent", input={"customer_id": "cust_99"})
    print(json.dumps(result, indent=2))`,
                    "sdk-agent-copy"
                  )
                }
                className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
              >
                {copiedCode === "sdk-agent-copy" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>

              <div><span className="text-purple-400 font-bold">import</span> <span className="text-white">anchor</span>, <span className="text-white">json</span></div>
              <br />
              <div className="text-zinc-500 italic"># 1. Custom Tool 0: Fetch Customer Data (Retry-Safe)</div>
              <div><span className="text-amber-400 font-bold">@anchor.tool</span>(safety=<span className="text-emerald-400">"retry_safe"</span>, naturally_idempotent=<span className="text-rose-400 font-bold">True</span>)</div>
              <div><span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">fetch_customer</span>(customer_id: <span className="text-cyan-300">str</span>) -&gt; <span className="text-cyan-300">dict</span>:</div>
              <div className="pl-4"><span className="text-purple-400 font-bold">return</span> &#123;<span className="text-emerald-400">"id"</span>: customer_id, <span className="text-emerald-400">"email"</span>: <span className="text-emerald-400">"aditya@anchor.dev"</span>, <span className="text-emerald-400">"tier"</span>: <span className="text-emerald-400">"VIP"</span>&#125;</div>
              <br />
              <div className="text-zinc-500 italic"># 2. Custom Tool 1: Dispatch Email Notification (Unsafe Side-Effect)</div>
              <div><span className="text-amber-400 font-bold">@anchor.tool</span>(safety=<span className="text-emerald-400">"unsafe"</span>)</div>
              <div><span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">send_welcome_email</span>(email: <span className="text-cyan-300">str</span>, tier: <span className="text-cyan-300">str</span>) -&gt; <span className="text-cyan-300">dict</span>:</div>
              <div className="pl-4"><span className="text-purple-400 font-bold">return</span> &#123;<span className="text-emerald-400">"status"</span>: <span className="text-emerald-400">"sent"</span>, <span className="text-emerald-400">"to"</span>: email, <span className="text-emerald-400">"tier"</span>: tier&#125;</div>
              <br />
              <div className="text-zinc-500 italic"># 3. Multi-Tool Durable Agent Workflow</div>
              <div><span className="text-amber-400 font-bold">@anchor.agent</span>(name=<span className="text-emerald-400">"onboarding_agent"</span>)</div>
              <div><span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">decide_next_step</span>(ctx: anchor.StepContext):</div>
              <div className="pl-4">customer = <span className="text-purple-400 font-bold">yield</span> <span className="text-white font-bold">anchor.ToolCall</span>(<span className="text-emerald-400">"fetch_customer"</span>, &#123;<span className="text-emerald-400">"customer_id"</span>: ctx.input[<span className="text-emerald-400">"customer_id"</span>]&#125;)</div>
              <div className="pl-4">email_res = <span className="text-purple-400 font-bold">yield</span> <span className="text-white font-bold">anchor.ToolCall</span>(<span className="text-emerald-400">"send_welcome_email"</span>, &#123;<span className="text-emerald-400">"email"</span>: customer[<span className="text-emerald-400">"email"</span>], <span className="text-emerald-400">"tier"</span>: customer[<span className="text-emerald-400">"tier"</span>]&#125;)</div>
              <div className="pl-4"><span className="text-purple-400 font-bold">yield</span> <span className="text-white font-bold">anchor.Done</span>(&#123;<span className="text-emerald-400">"status"</span>: <span className="text-emerald-400">"completed"</span>, <span className="text-emerald-400">"customer"</span>: customer, <span className="text-emerald-400">"email"</span>: email_res&#125;)</div>
              <br />
              <div className="text-zinc-500 italic"># 4. Trigger & Submit to Cluster</div>
              <div><span className="text-purple-400 font-bold">if</span> <span className="text-rose-400">__name__</span> == <span className="text-emerald-400">"__main__"</span>:</div>
              <div className="pl-4">result = anchor.run(<span className="text-emerald-400">"onboarding_agent"</span>, input=&#123;<span className="text-emerald-400">"customer_id"</span>: <span className="text-emerald-400 font-bold">"cust_99"</span>&#125;)</div>
              <div className="pl-4"><span className="text-blue-400">print</span>(json.dumps(result, indent=<span className="text-amber-400">2</span>))</div>
            </div>

            <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-2 font-mono text-xs">
              <div className="text-white font-bold text-xs">Replay-Safe Context Helpers (ctx: anchor.StepContext):</div>
              <p className="text-zinc-300 text-xs font-sans">
                The <code>ctx</code> object provides workflow inputs via <code>ctx.input</code> and replay-safe non-deterministic generators. 
                Never use raw <code>datetime.now()</code> or <code>uuid.uuid4()</code> directly inside workflow generators—always use <code>ctx</code> helpers so values are recorded into the journal and returned verbatim on replay:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
                <div className="p-3 rounded-lg border border-white/10 bg-white/5 space-y-1">
                  <code className="text-emerald-400 font-bold">ctx.now()</code>
                  <p className="text-zinc-400 text-[11px] font-sans">Journals ISO timestamp string. Returns exact original timestamp on replay.</p>
                </div>
                <div className="p-3 rounded-lg border border-white/10 bg-white/5 space-y-1">
                  <code className="text-sky-400 font-bold">ctx.random()</code>
                  <p className="text-zinc-400 text-[11px] font-sans">Journals random float. Returns exact generated float on replay.</p>
                </div>
                <div className="p-3 rounded-lg border border-white/10 bg-white/5 space-y-1">
                  <code className="text-purple-400 font-bold">ctx.new_id()</code>
                  <p className="text-zinc-400 text-[11px] font-sans">Journals UUID v4 string. Returns exact generated UUID on replay.</p>
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 6: Workflow Actions & Execution */}
          <section id="sdk-actions" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Zap className="h-3.5 w-3.5 text-zinc-400" />
              <span>Python SDK Reference</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Workflow Actions (ToolCall, ModelCall, Done) & Execution
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Agent generator functions yield structured action objects to instruct the runtime engine on what step to perform next. Below is a practical guide on how and when to use each action type:
            </p>

            <div className="space-y-4 font-mono text-xs">
              {/* ToolCall */}
              <div className="p-5 rounded-xl border border-white/10 bg-black/60 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="text-amber-400 font-bold flex items-center gap-2 text-sm">
                    <Wrench className="h-4 w-4" />
                    <span>anchor.ToolCall(name: str, args: dict, timeout_ms: int = None)</span>
                  </div>
                  <span className="rounded bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] text-amber-300 font-bold">Tool Execution</span>
                </div>
                <div className="text-zinc-300 text-xs font-sans space-y-1.5 leading-relaxed">
                  <div><strong>When to Use:</strong> Yield <code>anchor.ToolCall</code> whenever your workflow needs to execute a side-effecting function, query an external REST API, or mutate a database.</div>
                  <div><strong>How it Works:</strong> The runtime checks the tool journal for completed results. If never attempted, it writes Phase 1 Intent, executes the tool function, journals Phase 2 Result, and resumes your generator with the return value.</div>
                </div>
                <div className="p-3 rounded-lg border border-white/10 bg-[#090a0d] text-emerald-300">
                  customer = yield anchor.ToolCall("fetch_customer", &#123;"customer_id": "cust_99"&#125;, timeout_ms=30_000)
                </div>
              </div>

              {/* ModelCall */}
              <div className="p-5 rounded-xl border border-white/10 bg-black/60 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="text-sky-400 font-bold flex items-center gap-2 text-sm">
                    <Cpu className="h-4 w-4" />
                    <span>anchor.ModelCall(messages: list, model: str = None, timeout_ms: int = None)</span>
                  </div>
                  <span className="rounded bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[10px] text-sky-300 font-bold">LLM Reasoning</span>
                </div>
                <div className="text-zinc-300 text-xs font-sans space-y-1.5 leading-relaxed">
                  <div><strong>When to Use:</strong> Yield <code>anchor.ModelCall</code> when your agent needs LLM reasoning, text generation, or multi-turn conversational responses.</div>
                  <div><strong>How it Works:</strong> Dispatches the prompt messages to the configured LLM provider. The completion is automatically journaled into the event log so subsequent process restarts return the cached LLM completion instantly without re-billing tokens.</div>
                </div>
                <div className="p-3 rounded-lg border border-white/10 bg-[#090a0d] text-sky-300">
                  summary = yield anchor.ModelCall([&#123;"role": "user", "content": "Summarize user report"&#125;])
                </div>
              </div>

              {/* Done */}
              <div className="p-5 rounded-xl border border-white/10 bg-black/60 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="text-purple-400 font-bold flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>anchor.Done(output: dict)</span>
                  </div>
                  <span className="rounded bg-purple-500/10 border border-purple-500/30 px-2 py-0.5 text-[10px] text-purple-300 font-bold">Workflow Terminal Completion</span>
                </div>
                <div className="text-zinc-300 text-xs font-sans space-y-1.5 leading-relaxed">
                  <div><strong>When to Use:</strong> Yield <code>anchor.Done</code> at the final step of your agent generator function to signal successful workflow completion.</div>
                  <div><strong>How it Works:</strong> Transitions run status to <code>completed</code>, persists the final JSON output payload into database storage, and releases all worker leases unconditionally.</div>
                </div>
                <div className="p-3 rounded-lg border border-white/10 bg-[#090a0d] text-purple-300">
                  yield anchor.Done(&#123;"status": "completed", "customer_id": "cust_99"&#125;)
                </div>
              </div>

              {/* anchor.run */}
              <div className="p-5 rounded-xl border border-white/10 bg-black/60 space-y-2.5">
                <div className="text-white font-bold flex items-center gap-2 text-sm">
                  <Play className="h-4 w-4 text-emerald-400" />
                  <span>anchor.run(agent_name: str, input: dict)</span>
                </div>
                <div className="text-zinc-300 text-xs font-sans space-y-1.5 leading-relaxed">
                  <div><strong>When to Use:</strong> Use <code>anchor.run</code> in your main application script, REST handlers, or CLI commands to submit a workflow for execution.</div>
                  <div><strong>How it Works:</strong> Submits the run payload to the cluster API Gateway (`http://localhost:8000/api/runs`), which enqueues it for worker fleet execution.</div>
                </div>
                <div className="p-3 rounded-lg border border-white/10 bg-[#090a0d] text-zinc-200">
                  result = anchor.run("onboarding_agent", input=&#123;"customer_id": "cust_99"&#125;)
                </div>
              </div>
            </div>
          </section>

          {/* ========================================================================= */}
          {/* OPERATOR CONSOLE MANUAL (POSITIONED IMMEDIATELY BELOW PYTHON SDK REFERENCE) */}
          {/* ========================================================================= */}

          {/* SECTION 7: Operator Console Overview */}
          <section id="console-tour" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Eye className="h-3.5 w-3.5 text-zinc-400" />
              <span>Operator Console Manual</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Operator Console Overview & Interface Guide
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The Operator Console provides complete visibility into running agent workflows, cluster throughput, worker capacity, and manual intervention controls across 11 functional tabs:
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-emerald-400 font-bold flex items-center gap-2">
                  <LayoutDashboard className="h-4 w-4" />
                  <span>1. Dashboard / Overview</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Real-time cluster throughput metrics, total active workers, active runs, and the duplicate side-effect verification counter.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-sky-400 font-bold flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  <span>2. All Runs</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Filterable run ledger displaying active and historical executions, owning worker indicators, and step counts.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-purple-400 font-bold flex items-center gap-2">
                  <GitBranch className="h-4 w-4" />
                  <span>3. Run Detail (Timeline Visualizer)</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Step execution timeline showing thread continuity, worker handoff dividers, ghosted replay step fills, and raw event logs.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-amber-400 font-bold flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  <span>4. Needs Review Queue</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Human-in-the-loop queue for runs halted during unsafe tool execution following worker crashes. Allows manual resolution (Mark Executed with custom JSON, Mark Not Executed, Retry).
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-emerald-400 font-bold flex items-center gap-2">
                  <Cpu className="h-4 w-4" />
                  <span>5. Fleet Matrix</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Worker capacity matrix, heartbeat age, lease renewal status, and process shutdown controls (Graceful vs SIGKILL).
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-sky-400 font-bold flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  <span>6. Deployments</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Fleet breakdown by code version string to audit rolling updates and detect tool definition discrepancies across workers.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-purple-400 font-bold flex items-center gap-2">
                  <Wrench className="h-4 w-4" />
                  <span>7. Tool Registry</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Central inventory of declared tools showing safety policies (`retry_safe`, `reconcilable`, `unsafe`) and status check callbacks.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-amber-400 font-bold flex items-center gap-2">
                  <Code2 className="h-4 w-4" />
                  <span>8. Authoring Sandbox</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  In-browser code draft sandbox with AST linting that flags unjournaled `datetime.now()` or `uuid.uuid4()` calls.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-emerald-400 font-bold flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  <span>9. Metrics</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Cluster throughput, recovery latency percentiles (p50/p95/p99), replay overhead, and worker fencing rates.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-sky-400 font-bold flex items-center gap-2">
                  <Terminal className="h-4 w-4" />
                  <span>10. Logs Explorer</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Fleet-wide audit log query engine supporting event type filters and sequence keyset pagination (`after_seq`).
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1">
                <div className="text-purple-400 font-bold flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  <span>11. Settings / Environment</span>
                </div>
                <p className="text-zinc-300 text-xs font-sans">
                  Live cluster configuration inspector featuring profile switching (Demo vs Production) and timeout adjustments.
                </p>
              </div>
            </div>
          </section>

          {/* SECTION 8: Timeline Visualizer */}
          <section id="console-timeline" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Activity className="h-3.5 w-3.5 text-zinc-400" />
              <span>Operator Console Manual</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Run Detail & Timeline Visualizer (Execution Thread)
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The Run Detail view visualizes the execution trajectory of a workflow run. The timeline features an execution thread connecting step markers, worker process handoffs, and replay step markers:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-2">
                <strong className="text-white flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-400 shadow-sm" />
                  <span>Amber / Gold Markers (ToolCall)</span>
                </strong>
                <p className="text-zinc-300 text-xs font-sans">
                  Highlight external side-effects and tool intent/result steps executed by worker processes.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-2">
                <strong className="text-white flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-sky-400 shadow-sm" />
                  <span>Blue / Cyan Markers (ModelCall)</span>
                </strong>
                <p className="text-zinc-300 text-xs font-sans">
                  Highlight LLM completion and multi-turn model reasoning steps.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-2">
                <strong className="text-sky-400">Handoff Dividers:</strong>
                <p className="text-zinc-300 text-xs font-sans">
                  Vertical divider lines rendered when an owning worker process lease lapses and a new worker reclaims the run under a bumped epoch ID.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-2">
                <strong className="text-emerald-400">Ghosted Replay Steps:</strong>
                <p className="text-zinc-300 text-xs font-sans">
                  Step markers rendered with dashed outlines and lower opacity, indicating completed steps reconstructed from historical journal records without re-executing external code.
                </p>
              </div>
            </div>
          </section>

          {/* SECTION 9: Needs Review Queue */}
          <section id="console-needs-review" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <AlertTriangle className="h-3.5 w-3.5 text-zinc-400" />
              <span>Operator Console Manual</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Needs Review Queue & Manual Resolution
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              If a worker process crashes mid-execution during an <code>unsafe</code> tool step, Anchor transitions the run to <code>needs_review</code> status. 
              The run pauses safely in the Needs Review Queue to prevent duplicate side-effects until an operator resolves it:
            </p>

            <div className="p-5 rounded-xl border border-white/10 bg-black/60 font-mono text-xs space-y-3">
              <div className="text-white font-bold text-sm">Operator Resolution Options:</div>
              <div className="space-y-2.5 text-zinc-300 text-xs font-sans">
                <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5">
                  <strong className="text-emerald-400">1. Mark Executed (Custom Output JSON):</strong> Use when you confirm out-of-band that the external action did take place. 
                  Provide the custom JSON output payload in the console textarea. Anchor records this result into <code>tool_journal</code> with resolution <code>operator_marked_executed</code> and advances the workflow to the next step.
                </div>
                <div className="p-3 rounded-lg border border-sky-500/30 bg-sky-500/5">
                  <strong className="text-sky-400">2. Mark Not Executed:</strong> Use when you confirm that the external side-effect did not occur. Anchor clears the pending intent record, allowing a healthy worker process to safely execute the tool call.
                </div>
                <div className="p-3 rounded-lg border border-purple-500/30 bg-purple-500/5">
                  <strong className="text-purple-400">3. Retry:</strong> Use to force an immediate re-execution attempt under a newly bumped epoch ID.
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 10: Chaos Harness */}
          <section id="console-chaos" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Flame className="h-3.5 w-3.5 text-zinc-400" />
              <span>Operator Console Manual</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Chaos Harness & Fault Injection Testing
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              <strong>Why use the Chaos Harness?</strong> The Chaos Harness provides interactive fault injection controls to validate and prove system crash-resilience before deploying agent fleets to production.
            </p>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Operators can trigger ungraceful process terminations (SIGKILL 137) on live worker threads during active runs. This allows you to verify that Anchor detects worker death, waits for lease expiration, reclaims the run onto another worker node, and resumes execution from the exact step without double-charging tokens or repeating side-effects.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs pt-1">
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-rose-400 font-bold flex items-center gap-1.5">
                  <Flame className="h-4 w-4" />
                  <span>SIGKILL 137 Process Kill</span>
                </div>
                <p className="text-zinc-400 text-[11px] font-sans">Simulates sudden container OOMs or hardware node failures without graceful cleanup.</p>
              </div>
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-emerald-400 font-bold flex items-center gap-1.5">
                  <Activity className="h-4 w-4" />
                  <span>Live Thread Telemetry</span>
                </div>
                <p className="text-zinc-400 text-[11px] font-sans">Monitors active worker execution threads, lease renewal heartbeats, and reclaim events in real-time.</p>
              </div>
            </div>
          </section>

          {/* SECTION 11: Fleet Matrix */}
          <section id="console-fleet" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Cpu className="h-3.5 w-3.5 text-zinc-400" />
              <span>Operator Console Manual</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Fleet Matrix, Deployments & Capacity Tuning
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The Fleet Matrix tab displays active worker processes, lease renewal heartbeats, and available concurrency capacity across the cluster.
            </p>

            <div className="p-4 rounded-xl border border-white/10 bg-black/60 font-mono text-xs space-y-3">
              <div className="text-white font-bold text-xs">Worker Capacity Arithmetic & Tuning:</div>
              <p className="text-zinc-300 text-xs font-sans">
                Total cluster execution capacity is governed by the sum of individual worker concurrency limits:
              </p>
              <div className="p-3 rounded-lg border border-white/10 bg-white/5 text-emerald-300 font-bold text-center">
                C_total = ∑_(i=1)^N c_i
              </div>
              <p className="text-zinc-400 text-[11px] font-sans">
                Where <code>N</code> is the active healthy worker count and <code>c_i</code> is each worker's max concurrency limit (default 10).
              </p>

              <div className="border-t border-white/10 pt-3 space-y-2 text-zinc-300 text-xs font-sans">
                <div className="font-bold text-white">How to Adjust Worker Capacity:</div>
                <div>• <strong>CLI Command:</strong> <code>anchor config set worker_concurrency 15</code></div>
                <div>• <strong>Environment Variable:</strong> Set <code>ANCHOR_WORKER_CONCURRENCY=10</code> in <code>.env</code> or Docker Compose file.</div>
              </div>
            </div>
          </section>

          {/* SECTION 12: Engine Internals - Determinism Replay */}
          <section id="determinism-replay" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <GitBranch className="h-3.5 w-3.5 text-zinc-400" />
              <span>Engine Internals</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Deterministic Replay & State Reconstruction
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              When a worker process claims an interrupted run, it reads recorded events from sequence 1 to N to reconstruct in-memory state. 
              Non-deterministic function returns (ISO timestamps, random numbers, UUIDs) are read from journal records during replay to maintain deterministic execution paths.
            </p>
          </section>

          {/* SECTION 13: Engine Internals - Two Phase Journal */}
          <section id="two-phase-journal" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Database className="h-3.5 w-3.5 text-zinc-400" />
              <span>Engine Internals</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Two-Phase Journaling & Idempotency Derivation
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Anchor computes a deterministic idempotency key for every tool execution based on the run ID, step index, tool name, and canonical argument hash:
            </p>
            <div className="p-3.5 rounded-xl border border-white/15 bg-[#090a0d] font-mono text-xs text-emerald-300">
              idempotency_key = sha256(f"&#123;run_id&#125;:&#123;step_index&#125;:&#123;tool_name&#125;:&#123;args_hash&#125;")
            </div>
          </section>

          {/* SECTION 14: REST API Reference */}
          <section id="api-reference" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Globe className="h-3.5 w-3.5 text-zinc-400" />
              <span>Integrator Reference</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              REST API Reference & Endpoint Specifications
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Anchor provides a REST API for run submission, status monitoring, event log queries, cancellations, and manual resolutions:
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-emerald-400 font-bold">1. Submit a Run: POST /api/runs</div>
                <div className="text-zinc-400">Request: &#123; "agent_type": "onboarding_agent", "input": &#123; "customer_id": "cust_99" &#125; &#125;</div>
                <div className="text-zinc-300">Response (201 Created): &#123; "id": 102, "status": "pending", "created_at": "..." &#125;</div>
              </div>

              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-sky-400 font-bold">2. Fetch Run Detail: GET /api/runs/&#123;id&#125;</div>
                <div className="text-zinc-300">Response (200 OK): &#123; "id": 102, "status": "running", "epoch": 2, "owner_worker_id": "worker-a#1" &#125;</div>
              </div>

              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-purple-400 font-bold">3. Keyset Event Stream: GET /api/runs/&#123;id&#125;/events?after_seq=N</div>
                <div className="text-zinc-300">Response (200 OK): &#123; "items": [ &#123; "seq": N+1, "type": "TOOL_RESULT", ... &#125; ] &#125;</div>
              </div>

              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-rose-400 font-bold">4. Cancel Run: POST /api/runs/&#123;id&#125;/cancel</div>
                <div className="text-zinc-300">Response (200 OK): &#123; "id": 102, "status": "cancelled", "finished_at": "..." &#125;</div>
              </div>

              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-amber-400 font-bold">5. Manual Resolution: POST /api/runs/&#123;id&#125;/resolve</div>
                <div className="text-zinc-300">Request: &#123; "resolution": "executed", "result": &#123; "status": "success" &#125; &#125;</div>
              </div>
            </div>
          </section>

          {/* SECTION 15: WebSocket Protocol */}
          <section id="websocket-protocol" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Radio className="h-3.5 w-3.5 text-zinc-400" />
              <span>Integrator Reference</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              WebSocket Live Streaming Protocol
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Anchor streams real-time run and fleet telemetry over WebSockets via <code>/ws/runs/&#123;run_id&#125;</code> and <code>/ws/fleet</code>. 
              The lifecycle sequence is:
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-emerald-400 font-bold">1. Handshake (hello):</div>
                <div className="text-zinc-300 text-[11px]">Server sends connection confirmation and protocol version.</div>
                <code className="text-emerald-300 text-[11px] block">&#123; "type": "hello", "version": "1.6.0-prod" &#125;</code>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-sky-400 font-bold">2. Initial Snapshot (snapshot):</div>
                <div className="text-zinc-300 text-[11px]">Streams historical events (`seq=1..N`) upon initial connection.</div>
                <code className="text-sky-300 text-[11px] block">&#123; "type": "snapshot", "run_id": 102, "events": [...] &#125;</code>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-purple-400 font-bold">3. Live Stream (event):</div>
                <div className="text-zinc-300 text-[11px]">Emitted in real-time as workers commit step results.</div>
                <code className="text-purple-300 text-[11px] block">&#123; "type": "event", "seq": 5, "event_type": "TOOL_RESULT", "payload": &#123;...&#125; &#125;</code>
              </div>

              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-1.5">
                <div className="text-amber-400 font-bold">4. Reconnection (`after_seq`):</div>
                <div className="text-zinc-300 text-[11px]">Pass `?after_seq=4` on reconnect to resume streaming from sequence 5 without receiving duplicate events.</div>
                <code className="text-amber-300 text-[11px] block">ws://localhost:8000/ws/runs/102?after_seq=4</code>
              </div>
            </div>
          </section>

          {/* SECTION 16: System SQLSTATE Errors */}
          <section id="sqlstate-errors" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Lock className="h-3.5 w-3.5 text-zinc-400" />
              <span>Integrator Reference</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              System SQLSTATE Error Reference (AN001 – AN004)
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Anchor returns specific SQLSTATE exception codes when database triggers block invalid write attempts:
            </p>

            <div className="overflow-hidden rounded-xl border border-white/10 bg-black/60 font-mono text-xs">
              <table className="w-full text-left">
                <thead className="bg-white/5 text-zinc-300 uppercase tracking-wider text-[10px] border-b border-white/10">
                  <tr>
                    <th className="p-3">Error Code</th>
                    <th className="p-3">Error Name</th>
                    <th className="p-3">Trigger Condition</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 text-zinc-300">
                  <tr>
                    <td className="p-3 font-bold text-rose-400">AN001</td>
                    <td className="p-3 font-bold text-white">Lease Fenced</td>
                    <td className="p-3">Rejected when a timing-out worker process attempts to write with an outdated epoch ID.</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-amber-400">AN002</td>
                    <td className="p-3 font-bold text-white">Configuration Error</td>
                    <td className="p-3">Raised when cluster configuration settings violate safety validation rules.</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-sky-400">AN003</td>
                    <td className="p-3 font-bold text-white">Immutable Record Error</td>
                    <td className="p-3">Raised when an UPDATE or DELETE operation is attempted on append-only event logs.</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-purple-400">AN004</td>
                    <td className="p-3 font-bold text-white">Result Overwrite Error</td>
                    <td className="p-3">Raised if an UPDATE attempts to overwrite an already finalized tool result record.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* SECTION 17: Environment Settings */}
          <section id="env-guide" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Settings className="h-3.5 w-3.5 text-zinc-400" />
              <span>DevOps & Operations</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Configuration & Step Timeouts
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Step timeouts default to 600,000 ms (10 minutes). Runtime settings follow a 3-way precedence order:
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-lg border border-white/10 bg-black/60">
                <strong className="text-white">1. Decorator Override:</strong> <code>@anchor.tool(timeout_ms=600_000)</code> specified directly in Python code.
              </div>
              <div className="p-3 rounded-lg border border-white/10 bg-black/60">
                <strong className="text-white">2. Environment / Live Cluster Config:</strong> <code>ANCHOR_STEP_TIMEOUT_MS=600000</code> in <code>.env</code> or via CLI/Console UI.
              </div>
              <div className="p-3 rounded-lg border border-white/10 bg-black/60">
                <strong className="text-white">3. System Default Baseline:</strong> 600,000 ms (10 minutes) system default.
              </div>
            </div>
          </section>

          {/* SECTION 18: CLI Reference */}
          <section id="cli-reference" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Terminal className="h-3.5 w-3.5 text-zinc-400" />
              <span>DevOps & Operations</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              CLI Command Reference (anchor config)
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The <code>anchor</code> CLI binary provides commands to inspect and update cluster runtime settings:
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-white font-bold">Query Parameter:</div>
                <div className="pl-4"><span className="text-purple-400">anchor</span> config <span className="text-emerald-400">get</span> step_timeout_ms</div>
              </div>

              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-white font-bold">Update Parameter (supports 10m, 300s, 600000 units):</div>
                <div className="pl-4"><span className="text-purple-400">anchor</span> config <span className="text-emerald-400">set</span> step_timeout_ms 10m</div>
              </div>
            </div>
          </section>

          {/* SECTION 19: Production Deployment Runbook */}
          <section id="deployment-runbook" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <Server className="h-3.5 w-3.5 text-zinc-400" />
              <span>DevOps & Operations</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Production Deployment & Rolling Migrations
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Steps for deploying worker fleets via Docker and executing zero-downtime database migrations:
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-white font-bold">1. Worker Environment Variables:</div>
                <div className="text-zinc-400 space-y-1 text-[11px]">
                  <div><code>ANCHOR_API_URL=http://anchor-api:8000</code></div>
                  <div><code>DATABASE_URL=postgresql://anchor:secret@postgres:5432/anchordb</code></div>
                  <div><code>REDIS_URL=redis://redis:6379/0</code></div>
                  <div><code>ANCHOR_STEP_TIMEOUT_MS=600000</code></div>
                  <div><code>ANCHOR_LEASE_DURATION_MS=20000</code></div>
                  <div><code>ANCHOR_RENEWAL_INTERVAL_MS=5000</code></div>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-white font-bold">2. Zero-Downtime Migration Sequence:</div>
                <div className="text-zinc-300 text-xs font-sans space-y-1">
                  <div>1. Apply backward-compatible database schema migrations before updating worker images: <code>alembic upgrade head</code>.</div>
                  <div>2. Perform rolling container updates to deploy new worker versions.</div>
                  <div>3. Tool registry checks version declarations automatically to prevent tool definition mismatches.</div>
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 20: External Observability & Structured JSON Logs */}
          <section id="observability-logging" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs font-semibold text-zinc-300">
              <PieChart className="h-3.5 w-3.5 text-zinc-400" />
              <span>DevOps & Operations</span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono tracking-tight">
              Observability Metrics & Structured Logging
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Anchor exports cluster metrics to Prometheus and outputs structured JSON logs for log ingestion services:
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl border border-white/10 bg-black/60 space-y-2">
                <div className="text-white font-bold">Prometheus Metrics:</div>
                <div className="text-zinc-300 text-xs font-sans space-y-1">
                  <div>• <code>anchor_step_throughput_total</code>: Counter tracking completed steps.</div>
                  <div>• <code>anchor_recovery_latency_ms</code>: Recovery duration latency histogram.</div>
                  <div>• <code>anchor_fencing_violations_total</code>: Fenced write attempt count (`AN001`).</div>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-white/15 bg-[#090a0d] space-y-2 text-zinc-200">
                <div className="text-white font-bold">Structured JSON Log Schema:</div>
                <pre className="p-3.5 rounded-lg border border-white/10 bg-black/60 text-[11px] font-mono text-emerald-300 overflow-x-auto">
{`{
  "timestamp": "2026-08-31T12:00:00Z",
  "level": "INFO",
  "logger": "anchor.worker.loop",
  "run_id": 102,
  "seq": 4,
  "epoch": 2,
  "worker_id": "worker-a#1",
  "agent_type": "onboarding_agent",
  "event_type": "TOOL_RESULT",
  "step_index": 2,
  "idempotency_key": "a8f3...b901",
  "latency_ms": 142.5,
  "message": "Tool fetch_customer executed successfully"
}`}
                </pre>
              </div>
            </div>
          </section>

        </main>
      </div>
    </div>
  );
}
