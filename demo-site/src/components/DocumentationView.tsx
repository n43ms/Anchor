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
} from "lucide-react";

interface DocSection {
  id: string;
  title: string;
  category: string;
}

const SECTIONS: DocSection[] = [
  { id: "overview", title: "Executive Overview & System Invariants", category: "System Foundation" },
  { id: "quickstart", title: "5-Minute Quickstart", category: "System Foundation" },
  { id: "sdk-tool", title: "@anchor.tool Decorator & Safety Policies", category: "Python SDK Reference" },
  { id: "sdk-agent", title: "@anchor.agent Decorator & Generator Yield", category: "Python SDK Reference" },
  { id: "sdk-actions", title: "Action Types (ToolCall, ModelCall, Done) & anchor.run", category: "Python SDK Reference" },
  { id: "console-overview", title: "Operator Console UI: Navigation & Pages", category: "Operator Console & HITL" },
  { id: "console-needs-review", title: "NeedsReview Protocol: Retry vs Mark Executed vs Not Executed", category: "Operator Console & HITL" },
  { id: "console-chaos", title: "Chaos Harness & Failure Injection Deep Dive", category: "Operator Console & HITL" },
  { id: "console-fleet", title: "Fleet Matrix & Capacity Arithmetic", category: "Operator Console & HITL" },
  { id: "env-guide", title: "Environment Settings, 10m Timeout & Profiles", category: "Environment & Concurrency" },
  { id: "cli-reference", title: "CLI Reference (anchor config get/set)", category: "CLI & Infrastructure" },
  { id: "operations-chaos", title: "Operations, SIGKILL Bounds & Epoch Fencing", category: "System Architecture" },
];

export function DocumentationView({ onClose }: { onClose: () => void }) {
  const [activeSection, setActiveSection] = useState("quickstart");
  const [osTab, setOsTab] = useState<"mac" | "win">("win");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [openAccordions, setOpenAccordions] = useState<Record<string, boolean>>({});

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

  const toggleAccordion = (id: string) => {
    setOpenAccordions((prev) => ({ ...prev, [id]: !prev[id] }));
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
      {/* High-Contrast Vibrant Gold Header Bar */}
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
            <span className="text-zinc-300 font-semibold">Technical Architecture Specification & Developer Guide</span>
            <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-0.5 text-[10px] text-amber-400 font-mono font-bold">
              v1.5.9-prod
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
      <div className="flex-1 flex overflow-hidden max-w-[1600px] w-full mx-auto">
        {/* Permanently Fixed Left Sidebar Navigation */}
        <aside className="w-72 shrink-0 border-r border-amber-500/15 p-5 space-y-6 h-full overflow-y-auto custom-scrollbar bg-[#07070a] hidden md:block">
          <div>
            <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-amber-400 mb-3 px-2">
              Documentation Index
            </div>
            <nav className="space-y-4">
              {Array.from(new Set(SECTIONS.map((s) => s.category))).map((category) => (
                <div key={category} className="space-y-1">
                  <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-400/80 px-2">
                    {category}
                  </div>
                  {SECTIONS.filter((s) => s.category === category).map((section) => (
                    <button
                      key={section.id}
                      type="button"
                      onClick={() => scrollToSection(section.id)}
                      className={`w-full text-left px-2.5 py-1.5 rounded font-mono text-xs transition-all flex items-center justify-between cursor-pointer ${
                        activeSection === section.id
                          ? "bg-amber-500/15 text-amber-300 font-bold border-l-2 border-amber-400 pl-3"
                          : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                      }`}
                    >
                      <span className="truncate">{section.title}</span>
                    </button>
                  ))}
                </div>
              ))}
            </nav>
          </div>
        </aside>

        {/* Independent Right Scrollable Documentation Content */}
        <main className="flex-1 p-6 md:p-12 space-y-16 max-w-4xl min-w-0 h-full overflow-y-auto overflow-x-hidden custom-scrollbar">
          {/* Section 1: Overview */}
          <section id="overview" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Sparkles className="h-3.5 w-3.5 text-amber-400" />
              <span>System Foundation & Core Philosophy</span>
            </div>
            <h1 className="text-2xl font-bold text-zinc-100 font-mono tracking-tight">
              Executive Overview & System Invariants
            </h1>
            <p className="text-sm text-zinc-300 leading-relaxed font-sans">
              Modern enterprise software applications are rapidly transitioning from static, rule-based scripts to dynamic, 
              multi-step LLM (Large Language Model) agent fleets. Agents generate autonomous trajectories, query live HTTP APIs, 
              synthesize documents, issue multi-table database mutations, and execute financial transactions over the wire.
            </p>
            <p className="text-sm text-zinc-300 leading-relaxed font-sans">
              However, deploying LLM agents to production exposes a critical architectural vulnerability: <strong>traditional stateless agent loops are non-durable</strong>. 
              When a worker process experiences an Out-Of-Memory (OOM) kill, container restart, network partition, or API rate limit (HTTP 429), 
              all intermediate reasoning states and step results are destroyed. Generic queue systems (Celery, BullMQ) attempt process restarts 
              that force the agent to execute from Step 0, double-billing expensive LLM API tokens and duplicating critical external side-effects 
              (e.g. charging customer credit cards twice or sending duplicate emails).
            </p>
            <p className="text-sm text-zinc-300 leading-relaxed font-sans">
              <strong>Anchor</strong> is an enterprise-grade Durable Execution Runtime specifically engineered for AI agent fleets. 
              Anchor provides mathematical correctness guarantees that an agent workflow will resume from its exact last verified step 
              without repeating completed side-effects, without losing state, and without re-billing completed model completions.
            </p>

            {/* Collapsible Architecture Dropdown 1 */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion("arch-overview")}
                className="w-full px-4 py-3 flex items-center justify-between font-mono text-xs font-bold text-amber-300 hover:bg-amber-500/10 transition-colors text-left"
              >
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-amber-400" />
                  <span>The 5 Formal Correctness Invariants (I1 – I5) & Database Schemas</span>
                </div>
                {openAccordions["arch-overview"] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {openAccordions["arch-overview"] && (
                <div className="p-5 border-t border-amber-500/20 text-xs font-mono space-y-4 text-zinc-300 bg-black/70">
                  <div className="text-amber-300 font-bold text-sm">Mathematical Formulations & System Rules:</div>
                  <div className="space-y-3 text-zinc-300 text-xs font-sans leading-relaxed">
                    <div className="p-3.5 rounded-lg border border-amber-500/20 bg-black/60 font-mono">
                      <strong className="text-amber-400 text-xs">Invariant I1 (Log Contiguity & Sequence Monotonicity):</strong>
                      <div className="text-zinc-300 mt-1">Sequence numbers (<code className="text-amber-300">seq</code>) in <code className="text-amber-300">run_events</code> form a strictly monotonic 1-indexed sequence with zero gaps or duplicates.</div>
                      <code className="text-amber-200 text-[11px] block mt-1.5 font-bold">∀ i ∈ [1..N], seq(i) = i ∧ seq(i) &gt; seq(i-1)</code>
                    </div>
                    <div className="p-3.5 rounded-lg border border-amber-500/20 bg-black/60 font-mono">
                      <strong className="text-amber-400 text-xs">Invariant I2 (Single-Writer Epoch Fencing AN001):</strong>
                      <div className="text-zinc-300 mt-1">A PostgreSQL Phase-0 trigger (<code className="text-amber-300">run_events_epoch_gate</code>) unconditionally rejects writes from worker processes holding an epoch lower than the run's current epoch.</div>
                      <code className="text-amber-200 text-[11px] block mt-1.5 font-bold">IF NEW.epoch &lt; (SELECT epoch FROM runs WHERE id = NEW.run_id) THEN RAISE EXCEPTION 'AN001';</code>
                    </div>
                    <div className="p-3.5 rounded-lg border border-amber-500/20 bg-black/60 font-mono">
                      <strong className="text-amber-400 text-xs">Invariant I3 (Two-Phase Journaling AN004):</strong>
                      <div className="text-zinc-300 mt-1">Side-effecting tools record a Phase 1 Intent row before execution and a Phase 2 Result row upon completion.</div>
                      <code className="text-amber-200 text-[11px] block mt-1.5 font-bold">status = 'intent' (before call)  →  status = 'completed' (after call)</code>
                    </div>
                    <div className="p-3.5 rounded-lg border border-amber-500/20 bg-black/60 font-mono">
                      <strong className="text-amber-400 text-xs">Invariant I4 (Replay Determinism):</strong>
                      <div className="text-zinc-300 mt-1">Sequential event log replay reconstructs identical in-memory agent state up to the last completed step without executing completed side-effects.</div>
                    </div>
                    <div className="p-3.5 rounded-lg border border-amber-500/20 bg-black/60 font-mono">
                      <strong className="text-amber-400 text-xs">Invariant I5 (Terminal Reachability & Lease Safety):</strong>
                      <div className="text-zinc-300 mt-1">Terminal runs (<code className="text-amber-300">completed</code>, <code className="text-amber-300">failed</code>) release owner worker IDs and lease expirations unconditionally.</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Section 2: Quickstart */}
          <section id="quickstart" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Terminal className="h-3.5 w-3.5 text-amber-400" />
              <span>Developer Speed Run</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              5-Minute Quickstart
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Select your operating system environment below. Subcommands can be executed via the installed entrypoint binary (<code>anchor</code>) 
              or directly via Python module syntax (<code>python -m anchor.cli</code>):
            </p>

            {/* Vibrant Gold OS Tabs */}
            <div className="flex items-center gap-2 border-b border-amber-500/20 pb-2 font-mono text-xs">
              <button
                type="button"
                onClick={() => setOsTab("win")}
                className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer font-bold ${
                  osTab === "win"
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
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
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                macOS / Linux (Bash / Zsh)
              </button>
            </div>

            {/* Step 1 */}
            <div className="space-y-2 font-mono text-xs">
              <div className="text-amber-400 font-bold uppercase text-[11px]">Step 1: Install Anchor Runtime Package</div>
              <div className="relative rounded-xl border border-amber-500/25 bg-[#090a0d] p-4 sm:p-5 text-zinc-200">
                <button
                  type="button"
                  onClick={() => copyToClipboard("pip install anchor-runtime", "qs-1")}
                  className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
                >
                  {copiedCode === "qs-1" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <div className="font-mono text-xs leading-relaxed">
                  <span className="text-purple-400">pip</span> install <span className="text-amber-300 font-bold">anchor-runtime</span>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="space-y-2 font-mono text-xs">
              <div className="text-amber-400 font-bold uppercase text-[11px]">Step 2: Scaffold Project Workspace & Environment</div>
              <div className="relative rounded-xl border border-amber-500/25 bg-[#090a0d] p-4 sm:p-5 text-zinc-200">
                <button
                  type="button"
                  onClick={() => copyToClipboard(osTab === "win" ? "python -m anchor.cli init" : "anchor init", "qs-2")}
                  className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
                >
                  {copiedCode === "qs-2" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <div className="text-zinc-500 text-[11px] mb-2 font-sans">
                  {osTab === "win"
                    ? "# PowerShell: Scaffolds docker-compose.yml, .env template, and starter app.py"
                    : "# Bash: Scaffolds docker-compose.yml, .env template, and starter app.py"}
                </div>
                <div className="font-mono text-xs leading-relaxed">
                  {osTab === "win" ? (
                    <span><span className="text-cyan-400">python</span> -m anchor.cli <span className="text-amber-300 font-bold">init</span></span>
                  ) : (
                    <span><span className="text-cyan-400">anchor</span> <span className="text-amber-300 font-bold">init</span></span>
                  )}
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="space-y-2 font-mono text-xs">
              <div className="text-amber-400 font-bold uppercase text-[11px]">Step 3: Boot Worker Cluster & Console UI</div>
              <div className="relative rounded-xl border border-amber-500/25 bg-[#090a0d] p-4 sm:p-5 text-zinc-200">
                <button
                  type="button"
                  onClick={() => copyToClipboard(osTab === "win" ? "python -m anchor.cli dev" : "anchor dev", "qs-3")}
                  className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
                >
                  {copiedCode === "qs-3" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <div className="text-zinc-500 text-[11px] mb-2 font-sans">
                  {osTab === "win"
                    ? "# PowerShell: Boots PostgreSQL 16, Redis 7, API Gateway, 3 Worker nodes, and opens Console UI"
                    : "# Bash: Boots PostgreSQL 16, Redis 7, API Gateway, 3 Worker nodes, and opens Console UI"}
                </div>
                <div className="font-mono text-xs leading-relaxed">
                  {osTab === "win" ? (
                    <span><span className="text-cyan-400">python</span> -m anchor.cli <span className="text-amber-300 font-bold">dev</span></span>
                  ) : (
                    <span><span className="text-cyan-400">anchor</span> <span className="text-amber-300 font-bold">dev</span></span>
                  )}
                </div>
              </div>
            </div>

            {/* Step 4 */}
            <div className="space-y-2 font-mono text-xs">
              <div className="text-amber-400 font-bold uppercase text-[11px]">Step 4: Execute Agent Workflow Script</div>
              <div className="relative rounded-xl border border-amber-500/25 bg-[#090a0d] p-4 sm:p-5 text-zinc-200">
                <button
                  type="button"
                  onClick={() => copyToClipboard("python app.py", "qs-4")}
                  className="absolute top-3 right-3 p-1.5 rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white"
                >
                  {copiedCode === "qs-4" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
                <div className="text-zinc-500 text-[11px] mb-2 font-sans"># Submits workflow run and streams live step journal events</div>
                <div className="font-mono text-xs leading-relaxed">
                  <span className="text-cyan-400">python</span> app.py
                </div>
              </div>
            </div>

            {/* Collapsible Architecture Dropdown 2 */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion("arch-qs")}
                className="w-full px-4 py-3 flex items-center justify-between font-mono text-xs text-amber-300 hover:bg-amber-500/10 transition-colors text-left font-bold"
              >
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-amber-400" />
                  <span>Containerized Subsystems & Service Topology</span>
                </div>
                {openAccordions["arch-qs"] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {openAccordions["arch-qs"] && (
                <div className="p-5 border-t border-amber-500/20 text-xs font-mono space-y-3 text-zinc-300 bg-black/70">
                  <p className="text-xs font-sans leading-relaxed">
                    Executing <code className="text-amber-300 font-mono">anchor dev</code> coordinates 4 containerized subsystems connected via internal Docker bridge networking:
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-lg border border-amber-500/20 bg-black/60">
                      <div className="text-amber-300 font-bold">1. anchor-db (Port 5432)</div>
                      <p className="text-zinc-400 font-sans text-xs pt-1">PostgreSQL 16 server hosting `runs`, `run_events`, and `tool_journal` tables with transactional Phase-0 triggers.</p>
                    </div>
                    <div className="p-3 rounded-lg border border-amber-500/20 bg-black/60">
                      <div className="text-amber-300 font-bold">2. anchor-redis (Port 6379)</div>
                      <p className="text-zinc-400 font-sans text-xs pt-1">Redis 7 instance handling worker pub/sub heartbeat broadcasts and cluster-wide state invalidation.</p>
                    </div>
                    <div className="p-3 rounded-lg border border-amber-500/20 bg-black/60">
                      <div className="text-amber-300 font-bold">3. anchor-api (Port 8000)</div>
                      <p className="text-zinc-400 font-sans text-xs pt-1">FastAPI / Uvicorn API gateway serving run submission endpoints, SSE event streams, and Alembic schema migrations.</p>
                    </div>
                    <div className="p-3 rounded-lg border border-amber-500/20 bg-black/60">
                      <div className="text-amber-300 font-bold">4. anchor-worker (3 Nodes)</div>
                      <p className="text-zinc-400 font-sans text-xs pt-1">3 concurrent Python worker processes executing non-blocking claim event loops (`FOR UPDATE SKIP LOCKED`).</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Section 3: @anchor.tool */}
          <section id="sdk-tool" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Code2 className="h-3.5 w-3.5 text-amber-400" />
              <span>Python SDK Reference</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              @anchor.tool Decorator & Safety Policies
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The <code>@anchor.tool</code> decorator wraps any Python asynchronous function and assigns an explicit crash-safety policy. 
              Anchor enforces 3 distinct safety classifications to prevent duplicate external side-effects:
            </p>

            <div className="space-y-5 font-mono text-xs">
              {/* Category 1 */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">1. safety="retry_safe"</span>
                  <span className="rounded-md bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">Read-Only / Idempotent</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  For tools that are naturally idempotent (HTTP GET, database query) or accept provider idempotency keys. Safe to re-execute on worker crash recovery.
                </p>
                <div className="rounded-lg border border-amber-500/20 bg-black/70 p-4 font-mono text-xs space-y-1 text-zinc-200">
                  <div><span className="text-purple-400">@anchor.tool</span>(</div>
                  <div className="pl-4">safety=<span className="text-amber-300">"retry_safe"</span>,</div>
                  <div className="pl-4">naturally_idempotent=<span className="text-cyan-400">True</span>,</div>
                  <div className="pl-4">timeout_ms=<span className="text-amber-300">600_000</span></div>
                  <div>)</div>
                  <div><span className="text-purple-400">async def</span> <span className="text-blue-300">fetch_market_data</span>(symbol: <span className="text-cyan-400">str</span>) -&gt; <span className="text-cyan-400">dict</span>:</div>
                  <div className="pl-4 text-zinc-500">"""Fetches market tickers safely."""</div>
                  <div className="pl-4"><span className="text-purple-400">return await</span> http_client.<span className="text-blue-300">get</span>(<span className="text-amber-300">"/market/BTC"</span>)</div>
                </div>
              </div>

              {/* Category 2 */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">2. safety="reconcilable"</span>
                  <span className="rounded-md bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">Requires reconcile_fn</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  For side-effecting tools equipped with a user-supplied reconciliation callback. On recovery, Anchor executes <code>reconcile_fn</code> to inspect out-of-band state before retrying.
                </p>
                <div className="rounded-lg border border-amber-500/20 bg-black/70 p-4 font-mono text-xs space-y-1 text-zinc-200">
                  <div><span className="text-purple-400">@anchor.tool</span>(</div>
                  <div className="pl-4">safety=<span className="text-amber-300">"reconcilable"</span>,</div>
                  <div className="pl-4">reconcile_fn=verify_stripe_charge</div>
                  <div>)</div>
                  <div><span className="text-purple-400">async def</span> <span className="text-blue-300">execute_charge</span>(user_id: <span className="text-cyan-400">str</span>, amount: <span className="text-cyan-400">int</span>) -&gt; <span className="text-cyan-400">dict</span>:</div>
                  <div className="pl-4 text-zinc-500">"""Executes Stripe charge with reconciliation callback."""</div>
                  <div className="pl-4"><span className="text-purple-400">return await</span> stripe.charges.<span className="text-blue-300">create</span>(customer=user_id, amount=amount)</div>
                </div>
              </div>

              {/* Category 3 */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">3. safety="unsafe"</span>
                  <span className="rounded-md bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">Human-in-the-Loop Trap</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  For non-idempotent operations (sending emails, wire transfers). If an worker process dies mid-call, Anchor halts execution into <code>needs_review</code> status.
                </p>
                <div className="rounded-lg border border-amber-500/20 bg-black/70 p-4 font-mono text-xs space-y-1 text-zinc-200">
                  <div><span className="text-purple-400">@anchor.tool</span>(safety=<span className="text-amber-300">"unsafe"</span>)</div>
                  <div><span className="text-purple-400">async def</span> <span className="text-blue-300">dispatch_resend_email</span>(recipient: <span className="text-cyan-400">str</span>, body: <span className="text-cyan-400">str</span>) -&gt; <span className="text-cyan-400">dict</span>:</div>
                  <div className="pl-4 text-zinc-500">"""Dispatches non-idempotent executive email."""</div>
                  <div className="pl-4"><span className="text-purple-400">return await</span> resend.<span className="text-blue-300">send</span>(to=recipient, text=body)</div>
                </div>
              </div>
            </div>

            {/* Collapsible Architecture Dropdown 3 */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion("arch-tool")}
                className="w-full px-4 py-3 flex items-center justify-between font-mono text-xs text-amber-300 hover:bg-amber-500/10 transition-colors text-left font-bold"
              >
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-amber-400" />
                  <span>Two-Phase Write-Ahead Logging & Idempotency Key Framing</span>
                </div>
                {openAccordions["arch-tool"] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {openAccordions["arch-tool"] && (
                <div className="p-5 border-t border-amber-500/20 text-xs font-mono space-y-3 text-zinc-300 bg-black/70">
                  <p className="text-xs font-sans leading-relaxed">
                    Tool execution is governed by a two-phase transactional contract inside PostgreSQL <code className="text-amber-300 font-mono">tool_journal</code>:
                  </p>
                  <div className="p-4 rounded-lg bg-black/80 border border-amber-500/20 text-[11px] space-y-2">
                    <div className="text-amber-300 font-bold">Phase 1 (Intent Phase - Before Side Effect):</div>
                    <code className="text-amber-200 block">INSERT INTO tool_journal (run_id, step_index, idempotency_key, tool_name, args, status='intent')</code>
                    <div className="text-amber-300 font-bold pt-2">Phase 2 (Result Phase - After Side Effect):</div>
                    <code className="text-emerald-300 block">UPDATE tool_journal SET result = $result_json, status = 'completed' WHERE idempotency_key = $key AND result IS NULL</code>
                  </div>
                  <p className="text-xs font-sans leading-relaxed text-zinc-400">
                    The <code className="text-amber-300 font-mono">idempotency_key</code> is deterministically derived via SHA-256 hash over <code className="text-amber-300 font-mono">run_id + step_index + tool_name + args_hash</code>. 
                    Attempts to overwrite a completed result trigger error <code className="text-amber-300 font-mono">AN004</code> to maintain journal immutability.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* Section 4: @anchor.agent */}
          <section id="sdk-agent" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Layers className="h-3.5 w-3.5 text-amber-400" />
              <span>Python SDK Reference</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              @anchor.agent Decorator & Generator Yield Semantics
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Anchor agents are defined as Python generator functions. When an agent yields an action (<code>anchor.ToolCall</code>, <code>anchor.ModelCall</code>), 
              the Python generator pauses, Anchor commits the step result into PostgreSQL, and resumes the generator transparently.
            </p>

            <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 font-mono text-xs space-y-2.5 text-zinc-200">
              <div><span className="text-purple-400">@anchor.agent</span>(name=<span className="text-amber-300">"market_intelligence_agent"</span>)</div>
              <div><span className="text-purple-400">def</span> <span className="text-blue-300">decide_next_step</span>(ctx: anchor.StepContext):</div>
              <div className="pl-4">target_topic = ctx.input.<span className="text-blue-300">get</span>(<span className="text-amber-300">"topic"</span>)</div>

              <div className="pl-4 text-zinc-500 pt-2"># Step 0: Yield ToolCall to fetch market signals</div>
              <div className="pl-4">signals = <span className="text-purple-400">yield</span> anchor.<span className="text-blue-300">ToolCall</span>(</div>
              <div className="pl-8"><span className="text-amber-300">"fetch_market_data"</span>,</div>
              <div className="pl-8">{"{"}<span className="text-amber-300">"symbol"</span>: target_topic{"}"}</div>
              <div className="pl-4">)</div>

              <div className="pl-4 text-zinc-500 pt-2"># Step 1: Yield ModelCall for Gemini LLM synthesis</div>
              <div className="pl-4">llm_resp = <span className="text-purple-400">yield</span> anchor.<span className="text-blue-300">ModelCall</span>(</div>
              <div className="pl-8">model=<span className="text-amber-300">"gemini-2.5-flash"</span>,</div>
              <div className="pl-8">messages=[{"{"}<span className="text-amber-300">"role"</span>: <span className="text-amber-300">"user"</span>, <span className="text-amber-300">"content"</span>: <span className="text-amber-300">"Synthesize signals..."</span>{"}"}]</div>
              <div className="pl-4">)</div>

              <div className="pl-4 text-zinc-500 pt-2"># Step 2: Yield ToolCall to dispatch executive email</div>
              <div className="pl-4">delivery = <span className="text-purple-400">yield</span> anchor.<span className="text-blue-300">ToolCall</span>(</div>
              <div className="pl-8"><span className="text-amber-300">"dispatch_resend_email"</span>,</div>
              <div className="pl-8">{"{"}<span className="text-amber-300">"recipient"</span>: <span className="text-amber-300">"user@example.com"</span>, <span className="text-amber-300">"body"</span>: llm_resp.<span className="text-blue-300">get</span>(<span className="text-amber-300">"response"</span>){"}"}</div>
              <div className="pl-4">)</div>

              <div className="pl-4 text-zinc-500 pt-2"># Step 3: Yield Done to conclude run</div>
              <div className="pl-4"><span className="text-purple-400">yield</span> anchor.<span className="text-blue-300">Done</span>({"{"}<span className="text-amber-300">"status"</span>: <span className="text-amber-300">"completed"</span>, <span className="text-amber-300">"delivery"</span>: delivery{"}"})</div>
            </div>

            {/* Collapsible Architecture Dropdown 4 */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 overflow-hidden">
              <button
                type="button"
                onClick={() => toggleAccordion("arch-agent")}
                className="w-full px-4 py-3 flex items-center justify-between font-mono text-xs text-amber-300 hover:bg-amber-500/10 transition-colors text-left font-bold"
              >
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-amber-400" />
                  <span>Generator State Machine & Replay Checkpointing</span>
                </div>
                {openAccordions["arch-agent"] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {openAccordions["arch-agent"] && (
                <div className="p-5 border-t border-amber-500/20 text-xs font-mono space-y-3 text-zinc-300 bg-black/70">
                  <p className="text-xs font-sans leading-relaxed">
                    When a generator yields an Action, the worker engine intercepts the yield, serializes the <code className="text-amber-300 font-mono">StepContext</code> state into <code className="text-amber-300 font-mono">run_events</code>, and advances <code className="text-amber-300 font-mono">last_seq</code> atomically. 
                    On crash recovery, Anchor re-instantiates the generator function and fast-forwards completed steps by feeding cached results into generator <code className="text-amber-300 font-mono">.send(result)</code> without re-executing tools or LLM calls.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* Section 5: Action Types Deep Dive */}
          <section id="sdk-actions" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Zap className="h-3.5 w-3.5 text-amber-400" />
              <span>Python SDK Reference</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              Action Types (ToolCall, ModelCall, Done) & anchor.run Engine
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              When an agent function yields execution back to the Anchor runtime, it emits one of 3 strongly-typed Action classes defined in <code>anchor.core.determinism.actions</code>. 
              The worker engine intercepts the yielded Action, evaluates its safety contract, records a journal event in PostgreSQL, and yields the output back to the generator.
            </p>

            <div className="space-y-5 font-mono text-xs">
              {/* ToolCall */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">anchor.ToolCall(tool_name, args, timeout_ms=None)</span>
                  <span className="rounded-md bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">Tool Execution</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Yields execution of a registered tool with argument payload dict. Supports optional per-step timeout override (<code className="text-amber-300">timeout_ms</code>).
                </p>
                <div className="p-3.5 rounded-lg bg-black/70 border border-amber-500/20 font-mono text-xs space-y-1 text-zinc-200">
                  <div className="text-amber-300 font-bold">ToolCall Field Specifications:</div>
                  <div className="text-zinc-400">• <code className="text-cyan-400">tool_name</code>: Registered string matching `@anchor.tool` decorator name.</div>
                  <div className="text-zinc-400">• <code className="text-cyan-400">args</code>: Dictionary payload passed into tool function.</div>
                  <div className="text-zinc-400">• <code className="text-cyan-400">timeout_ms</code>: Optional step timeout override in ms (default: inherits 10m cluster setting).</div>
                </div>
              </div>

              {/* ModelCall */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">anchor.ModelCall(model, messages, temperature=0.7, max_tokens=None)</span>
                  <span className="rounded-md bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">LLM Synthesis</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Yields an LLM chat completion request to target model providers (Gemini, OpenAI, Anthropic). Anchor journals an <code className="text-amber-300">LLM_CALLED</code> event with prompt message inputs, response completions, token billing stats, and execution latency.
                </p>
              </div>

              {/* Done */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">anchor.Done(result)</span>
                  <span className="rounded-md bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">Terminal Conclude</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Concludes the workflow run. Sets <code className="text-amber-300">runs.status = 'completed'</code>, records <code className="text-amber-300">completed_at</code> timestamp, and releases database row locks and Redis worker leases unconditionally.
                </p>
              </div>
            </div>
          </section>

          {/* Section 6: Console UI Overview */}
          <section id="console-overview" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Eye className="h-3.5 w-3.5 text-amber-400" />
              <span>Operator Console & HITL</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              Operator Console UI: Page & Feature Navigation Guide
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The Web Operator Console (accessible at <code>http://localhost:3000</code>) provides real-time visibility, 
              3D trajectory rendering, fault monitoring, and human-in-the-loop governance over your entire worker cluster.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 space-y-2">
                <div className="font-bold text-amber-300 text-sm flex items-center gap-2">
                  <Activity className="h-4 w-4 text-amber-400" />
                  <span>Runs Thread</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Visualizes active and completed runs as interactive steps. Includes a Run Strand Canvas
                  rendering the monotonic sequence trajectory (`seq 1..N`), tool input payloads, LLM prompt messages, and worker handoff nodes.
                </p>
              </div>

              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 space-y-2">
                <div className="font-bold text-amber-300 text-sm flex items-center gap-2">
                  <HelpCircle className="h-4 w-4 text-amber-400" />
                  <span>NeedsReview Halted Inbox</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Dedicated operational triage inbox capturing runs halted in <code>needs_review</code> status due to interrupted <code>unsafe</code> side-effecting tool calls. 
                  Allows operators to resolve runs safely with zero risk of duplicate execution.
                </p>
              </div>

              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 space-y-2">
                <div className="font-bold text-amber-300 text-sm flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-amber-400" />
                  <span>Fleet Matrix & Capacity Bar</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Displays active worker processes connected to the database, per-worker capacity limits, global active run count, 
                  heartbeat age indicators, and total cluster capacity arithmetic (`worker_count × per_worker_concurrency`).
                </p>
              </div>

              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 space-y-2">
                <div className="font-bold text-amber-300 text-sm flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-amber-400" />
                  <span>Environment Settings Page</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Live cluster configuration manager supporting step timeout presets (`1m`, `5m`, `10m`, `30m`), lease duration ratios, 
                  concurrency ceilings, and one-click cluster settings updates via `PATCH /api/config`.
                </p>
              </div>
            </div>
          </section>

          {/* Section 7: NeedsReview Protocol Deep Dive */}
          <section id="console-needs-review" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
              <span>Operator Console & HITL</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              NeedsReview Protocol: Retry vs Mark Executed vs Not Executed
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              When an worker node process crashes or experiences a hard SIGKILL while executing an <code>unsafe</code> tool call (e.g. <code>dispatch_resend_email</code>), 
              the tool journal row remains in Phase 1 (Intent) with a <code>NULL</code> result. On recovery, Anchor refuses to guess whether the external action occurred. 
              It raises <code>NeedsReviewHalted</code>, sets run status to <code>needs_review</code>, clears worker ownership, and waits for operator resolution.
            </p>

            {/* Comprehensive Resolution Options */}
            <div className="space-y-4 font-mono text-xs">
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 space-y-2">
                <div className="font-bold text-amber-300 text-sm">1. Retry (Mark Not Executed)</div>
                <p className="text-zinc-300 font-sans text-sm leading-relaxed">
                  Use when the operator verifies out-of-band that the side-effect <strong>did NOT execute</strong> (e.g. email was not sent). 
                  Anchor clears the unresolved intent row, transitions run status back to <code>pending</code>, and worker processes re-execute the step cleanly from scratch.
                </p>
                <div className="p-3 rounded-lg bg-black/60 border border-amber-500/20 text-xs font-mono">
                  POST /api/runs/[id]/resolve  -&gt;  {"{"}"resolution": "not_executed"{"}"}
                </div>
              </div>

              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 space-y-2">
                <div className="font-bold text-emerald-400 text-sm">2. Mark Executed (Supply Custom Output)</div>
                <p className="text-zinc-300 font-sans text-sm leading-relaxed">
                  Use when the operator verifies out-of-band that the side-effect <strong>SUCCEEDED</strong> (e.g. email was delivered successfully). 
                  The operator provides the result dictionary payload. Anchor commits Phase 2 Result in `tool_journal`, appends `TOOL_COMPLETED` in `run_events`, 
                  and worker processes resume the agent from Step + 1 without re-executing the email tool.
                </p>
                <div className="p-3 rounded-lg bg-black/60 border border-emerald-500/20 text-xs font-mono">
                  POST /api/runs/[id]/resolve  -&gt;  {"{"}"resolution": "executed", "result": {"{"}"status": "delivered_via_operator"{"}"}{"}"}
                </div>
              </div>
            </div>
          </section>

          {/* Section 8: Chaos Harness */}
          <section id="console-chaos" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Flame className="h-3.5 w-3.5 text-amber-400" />
              <span>Operator Console & HITL</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              Chaos Harness & Failure Injection Deep Dive
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The Chaos Harness visualizer allows engineers to simulate real-world infrastructure catastrophes (hard worker process SIGKILL, network partitions, database disconnections) 
              in real time and observe Anchor's sub-second fault recovery algorithms.
            </p>

            <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 space-y-3 font-mono text-xs">
              <div className="font-bold text-amber-300 text-sm">Simulated Worker SIGKILL Execution Flow</div>
              <ol className="list-decimal list-inside space-y-2 text-zinc-300 font-sans text-xs leading-relaxed">
                <li>Operator clicks <strong>Kill Worker Process (`worker-a#1`)</strong> in the Chaos Console tab.</li>
                <li>Target worker container process is terminated instantaneously via SIGKILL mid-step.</li>
                <li>The killed worker's DB lease lapses as heartbeat renewals stop.</li>
                <li>A surviving worker (`worker-b#2`) reclaims the run atomically using <code>FOR UPDATE SKIP LOCKED</code>.</li>
                <li>If the killed worker wakes up later, its write attempt is rejected by trigger <code>AN001</code> (epoch fencing).</li>
              </ol>
            </div>
          </section>

          {/* Section 9: Fleet Matrix */}
          <section id="console-fleet" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Cpu className="h-3.5 w-3.5 text-amber-400" />
              <span>Operator Console & HITL</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              Fleet Matrix & Capacity Arithmetic
            </h2>
            <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 font-mono text-xs space-y-2">
              <div className="font-bold text-amber-300 text-sm">Total Fleet Capacity Calculation</div>
              <code className="leading-relaxed">Fleet Capacity = Connected Workers × per_worker_concurrency</code>
              <p className="text-zinc-300 font-sans text-xs pt-1 leading-relaxed">
                For 5 active worker processes with `per_worker_concurrency = 10`, total fleet capacity is 50 parallel workflow runs (capped by `global_concurrency_cap`).
              </p>
            </div>
          </section>

          {/* Section 10: Exhaustive Environment Settings Breakdown */}
          <section id="env-guide" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Settings className="h-3.5 w-3.5 text-amber-400" />
              <span>Environment & Concurrency</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              Environment Settings & Operator Console Cluster Configurations
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              The Environment Settings tab in the Operator Console (and corresponding <code className="text-amber-300 font-mono">.env</code> cluster configuration) 
              controls worker concurrency ceilings, timeout caps, and distributed lease heartbeats. Below is the exhaustive reference for every configurable setting:
            </p>

            <div className="space-y-4 font-mono text-xs">
              {/* Profile Selector */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-2">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">1. Profile Selector (DEMO vs PRODUCTION)</span>
                  <span className="rounded bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">Cluster Preset</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Selects predefined cluster operational parameters. <strong>DEMO profile</strong> uses short 4s leases and 1s heartbeats for fast local chaos feedback. 
                  <strong>PRODUCTION profile</strong> uses 20s leases and 5s heartbeats to minimize database load across hundreds of worker nodes.
                </p>
              </div>

              {/* Step Timeout */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-2">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">2. Step Timeout (ANCHOR_STEP_TIMEOUT_MS)</span>
                  <span className="rounded bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">Default: 600,000 ms (10m)</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Maximum execution duration allowed for an individual step before an worker process raises a step timeout exception. 
                  In v1.5.9, default timeout is baseline set to <strong>10 minutes (600,000 ms)</strong> across DEMO and PRODUCTION profiles. Supports formatted units (<code className="text-amber-300">10m</code>, <code className="text-amber-300">300s</code>, <code className="text-amber-300">600000ms</code>).
                </p>
              </div>

              {/* Worker Concurrency */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-2">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">3. Per-Worker Concurrency (per_worker_concurrency)</span>
                  <span className="rounded bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">DEMO: 10 | PROD: 25</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Maximum number of active workflow run claims an individual worker container process can execute in parallel.
                </p>
              </div>

              {/* Global Concurrency Cap */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-2">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">4. Global Concurrency Cap (global_concurrency_cap)</span>
                  <span className="rounded bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">DEMO: 50 | PROD: 500</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Cluster-wide hard upper limit on parallel active runs. Prevents database connection exhaustion during traffic spikes.
                </p>
              </div>

              {/* Distributed Lease Duration */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-2">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">5. Distributed Lease Duration (lease_duration_ms)</span>
                  <span className="rounded bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">DEMO: 4,000 ms | PROD: 20,000 ms</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Database lease TTL duration for worker ownership. If a worker dies and fails to renew heartbeats, its lease expires after this duration, allowing surviving workers to reclaim the run.
                </p>
              </div>

              {/* Renewal Interval */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-2">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">6. Renewal Interval (renewal_interval_ms)</span>
                  <span className="rounded bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">DEMO: 1,000 ms | PROD: 5,000 ms</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Background heartbeat renewal loop frequency (<code className="text-amber-300">renew_forever</code> task). Active workers extend their DB lease expirations at this frequency.
                </p>
              </div>

              {/* Ratio Integrity Rule */}
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-5 space-y-2">
                <div className="flex items-center justify-between border-b border-amber-500/15 pb-2">
                  <span className="font-bold text-amber-300 text-sm">7. Lease Ratio Integrity Validation Rule</span>
                  <span className="rounded bg-amber-500/20 text-amber-300 px-2.5 py-0.5 text-[10px] font-bold">Safety Rule: ≥ 4×</span>
                </div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">
                  Mathematical integrity constraint enforced by Console UI and API gateway: <code className="text-amber-300 font-mono">lease_duration_ms &gt;= 4 * renewal_interval_ms</code>. 
                  Guarantees that active workers have at least 4 heartbeat attempts to extend their lease before expiration, preventing premature lease loss under CPU spikes.
                </p>
              </div>
            </div>
          </section>

          {/* Section 11: CLI Reference */}
          <section id="cli-reference" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Terminal className="h-3.5 w-3.5 text-amber-400" />
              <span>CLI & Infrastructure</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              CLI Reference (python -m anchor.cli)
            </h2>

            <div className="space-y-3 font-mono text-xs">
              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 space-y-1.5">
                <div className="font-bold text-amber-300">python -m anchor.cli config get [key]</div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">Queries cluster configuration or local .env with formatted duration units.</p>
                <div className="p-3 rounded-lg bg-black/60 border border-amber-500/20 text-xs font-mono space-y-1">
                  <div>$ python -m anchor.cli config get step_timeout_ms</div>
                  <div className="text-zinc-400">step_timeout_ms: 600000 ms (10.0m / 600.0s)</div>
                </div>
              </div>

              <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 space-y-1.5">
                <div className="font-bold text-amber-300">python -m anchor.cli config set key value</div>
                <p className="text-zinc-300 font-sans text-xs leading-relaxed">Patches cluster config via API (PATCH /api/config) or updates local .env. Supports units (10m, 300s, 600000ms).</p>
                <div className="p-3 rounded-lg bg-black/60 border border-amber-500/20 text-xs font-mono space-y-1">
                  <div>$ python -m anchor.cli config set step_timeout_ms 10m</div>
                  <div className="text-emerald-400">[+] Updated cluster configuration: step_timeout_ms = 600000</div>
                </div>
              </div>
            </div>
          </section>

          {/* Section 12: Operations & Fault Recovery */}
          <section id="operations-chaos" className="space-y-5 scroll-mt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 font-mono text-xs font-semibold text-amber-400">
              <Server className="h-3.5 w-3.5 text-amber-400" />
              <span>System Architecture</span>
            </div>
            <h2 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
              Operations, SIGKILL Fault Bounds & Epoch Fencing
            </h2>
            <p className="text-sm text-zinc-300 font-sans leading-relaxed">
              Anchor provides sub-second fault recovery bounds under hard process kills (SIGKILL) using monotonic epoch fencing (`AN001`).
            </p>
            <div className="rounded-xl border border-amber-500/20 bg-[#090a0d] p-4 sm:p-5 font-mono text-xs space-y-1.5">
              <div className="font-bold text-amber-300">Recovery Time Objective Formula (T_recover)</div>
              <div className="p-3 rounded-lg bg-black/60 border border-amber-500/20 text-xs font-mono">
                T_recover ≈ lease_duration_ms - (renewal_interval_ms / 2) + (reclaim_poll_interval_ms / 2)
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
