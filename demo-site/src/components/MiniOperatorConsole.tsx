import React from "react";
import { useDemo, DemoProvider, DemoTab } from "../context/DemoProvider";
import { RunThread } from "./RunThread";
import { WorkerBar } from "./WorkerBar";
import { ChaosVisualizer } from "./ChaosVisualizer";
import { SystemInspector } from "./SystemInspector";
import { TerminalConsole } from "./TerminalConsole";

import {
  LayoutDashboard,
  Activity,
  AlertTriangle,
  Cpu,
  Wrench,
  BarChart3,
  Terminal,
  Settings,
  Flame,
  ShieldCheck,
  Zap,
  Play,
  RotateCcw,
  CheckCircle2,
  Lock,
  Search,
  ExternalLink,
  Clock,
  Layers,
  PlusCircle,
  FileText,
  Server,
  Code2,
  Sliders,
  SlidersHorizontal,
} from "lucide-react";

export const MiniOperatorConsoleContent: React.FC = () => {
  const {
    stage,
    activeTab,
    setActiveTab,
    selectedRunId,
    setSelectedRunId,
    isInspectorOpen,
    setIsInspectorOpen,
    health,
    workers,
    timeline,
    runs,
    chaosReport,
    events,
    isSimulating,
    killWorker,
    triggerRecovery,
    submitNewRun,
    resetDemoState,
  } = useDemo();

  const navGroups: {
    label: string;
    items: { id: DemoTab; label: string; icon: React.FC<{ className?: string }>; badge?: string; highlight?: boolean }[];
  }[] = [

    {
      label: "Overview",
      items: [{ id: "overview-dashboard", label: "Dashboard", icon: LayoutDashboard }],
    },
    {
      label: "Runs",
      items: [
        { id: "runs-all", label: "All runs", icon: Activity, badge: `${runs.length}` },
        { id: "runs-needs-review", label: "Needs review", icon: AlertTriangle, badge: "1" },
      ],


    },
    {
      label: "Workers",
      items: [
        { id: "workers-fleet", label: "Fleet", icon: Cpu, badge: `${health.worker_count}` },
        { id: "workers-deployments", label: "Deployments", icon: Server, badge: "v1.4.8" },
      ],
    },
    {
      label: "Chaos",
      items: [
        { id: "chaos-console", label: "Chaos console", icon: Flame, badge: "⚡ TRY THIS OUT", highlight: true },
        { id: "chaos-history", label: "Run history", icon: FileText, badge: "42" },
      ],
    },

    {
      label: "Tools",
      items: [
        { id: "tools-registry", label: "Registry", icon: Wrench, badge: "4" },
        { id: "tools-test-run", label: "Test run", icon: Code2 },
      ],
    },
    {
      label: "Observability",
      items: [
        { id: "observability-metrics", label: "Metrics", icon: BarChart3 },
        { id: "observability-logs", label: "Logs", icon: Terminal },
      ],
    },
    {
      label: "Settings",
      items: [{ id: "settings-environment", label: "Environment", icon: Settings }],
    },
  ];


  return (
    <div className="relative flex h-full bg-zinc-950 font-mono text-xs text-zinc-100 select-none overflow-hidden rounded-2xl border border-white/10 shadow-2xl">
      {/* 1. Left Operator Sidebar Navigation */}
      <div className="w-56 shrink-0 border-r border-white/10 bg-black/60 backdrop-blur-xl flex flex-col justify-between p-3">
        <div className="space-y-3 overflow-y-auto custom-scrollbar pr-1">
          {/* Workspace Title */}
          <div className="flex items-center gap-2.5 px-2 py-1.5 border-b border-white/10">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-amber-500/40 bg-amber-500/10 p-1">
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
              <div className="font-extrabold text-white text-xs tracking-wider">ANCHOR</div>
              <div className="text-[9px] text-zinc-500">OPERATOR CONSOLE</div>
            </div>
          </div>


          {/* Navigation Groups */}
          <div className="space-y-3">
            {navGroups.map((group) => (
              <div key={group.label} className="space-y-1">
                <div className="px-2 py-0.5 text-[9px] font-bold text-zinc-500 uppercase tracking-widest">
                  {group.label}
                </div>
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setActiveTab(item.id)}
                      className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-[11px] transition-all cursor-pointer ${
                        active
                          ? "bg-amber-500/15 text-amber-300 font-bold border border-amber-500/30"
                          : (item as any).highlight
                          ? "bg-rose-500/20 text-rose-200 font-bold border border-rose-500/50 shadow-glow-rose animate-pulse"
                          : "text-zinc-400 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Icon className={`h-3.5 w-3.5 ${active ? "text-amber-400" : (item as any).highlight ? "text-rose-400" : "text-zinc-400"}`} />
                        <span>{item.label}</span>
                      </div>

                      {item.badge && (
                        <span
                          className={`rounded-full px-1.5 py-0.2 text-[9px] font-bold ${
                            (item as any).highlight
                              ? "bg-rose-500 text-white animate-bounce shadow-md"
                              : active
                              ? "bg-amber-500/30 text-amber-200"
                              : "bg-white/10 text-zinc-400"
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* Footer info in sidebar */}
        <div className="rounded-xl border border-white/5 bg-white/[0.02] p-2 text-[9px] text-zinc-500 space-y-1 mt-2">
          <div className="flex items-center justify-between">
            <span>Profile:</span>
            <span className="text-amber-400 font-bold">demo</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Mode:</span>
            <span className="text-emerald-400 font-bold">local</span>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-white/5 text-[8.5px]">
            <span>License:</span>
            <span className="text-amber-300 font-bold flex items-center gap-1">
              <ShieldCheck className="h-2.5 w-2.5 text-amber-400" />
              <span>Apache 2.0</span>
            </span>
          </div>
        </div>
      </div>

      {/* 2. Main Console Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-black/40">
        {/* Top Header Bar */}
        <div className="flex items-center justify-between border-b border-white/10 bg-black/60 px-4 py-2.5 backdrop-blur-xl">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold text-white uppercase tracking-wider">
              {activeTab}
            </span>
            <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold text-emerald-400">
              HEALTHY (3 NODES)
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsInspectorOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-[10px] font-bold text-amber-300 hover:bg-amber-500/20 transition-all cursor-pointer"
            >
              <SlidersHorizontal className="h-3 w-3" />
              <span>System Inspector</span>
            </button>

            <button
              type="button"
              onClick={() => submitNewRun("candidate_eval")}
              disabled={isSimulating}
              className="flex items-center gap-1.5 rounded-lg border border-emerald-500/50 bg-emerald-500/20 px-2.5 py-1 text-[10px] font-bold text-emerald-300 hover:bg-emerald-500/30 transition-all cursor-pointer"
            >
              <PlusCircle className="h-3 w-3" />
              <span>▶ Run Demo Agent</span>
            </button>



            {stage === "crashed" && (
              <button
                type="button"
                onClick={triggerRecovery}
                disabled={isSimulating}
                className="flex items-center gap-1.5 rounded-lg border border-amber-500/50 bg-amber-500/20 px-2.5 py-1 text-[10px] font-bold text-amber-300 hover:bg-amber-500/30 transition-all animate-pulse cursor-pointer"
              >
                <Play className="h-3 w-3" />
                <span>Auto-Reclaim Run</span>
              </button>
            )}

            <button
              type="button"
              onClick={resetDemoState}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] text-zinc-300 hover:bg-white/10 transition-all cursor-pointer"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Reset</span>
            </button>
          </div>
        </div>

        {/* Dynamic Sub-View Renderer */}
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-4">
          {/* VIEW 1: OVERVIEW DASHBOARD */}
          {activeTab === "overview-dashboard" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-xl border border-white/10 bg-black/60 p-3">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Active Connected Workers</div>
                  <div className="text-base font-bold text-emerald-400 mt-1">{health.worker_count} processes</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/60 p-3">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Per-Worker Capacity</div>
                  <div className="text-base font-bold text-amber-400 mt-1">10 runs / worker</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/60 p-3">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Fleet Total Capacity</div>
                  <div className="text-base font-bold text-cyan-400 mt-1">30 (Cap: 50)</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/60 p-3">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Duplicate Side Effects</div>
                  <div className="text-base font-bold text-emerald-400 mt-1">0 duplicates</div>
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-3">
                <div className="text-xs font-bold text-white uppercase tracking-wider">Active Candidate Workflows</div>
                <div className="space-y-2">
                  {runs.map((r) => (
                    <div
                      key={r.id}
                      onClick={() => {
                        setSelectedRunId(r.id);
                        setActiveTab("run-detail");
                      }}
                      className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] p-3 hover:border-amber-500/40 transition-all cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-white">#{r.display_id}</span>
                        <span className="text-zinc-300 font-semibold">{r.agent_type}</span>
                        <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[9px] text-emerald-400 font-bold uppercase">
                          {r.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-zinc-400 text-[10px]">
                        <span>epoch {r.epoch}</span>
                        <span className="rounded bg-white/5 px-2 py-0.5">{r.owner_worker_id || "none"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* VIEW 2: RUNS - ALL RUNS */}
          {activeTab === "runs-all" && (
            <div className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-white/10 pb-2 text-[10px] text-zinc-500 font-bold uppercase">
                <span>RUN ID & AGENT TYPE</span>
                <span>STATUS & WORKER</span>
                <span>ELAPSED & SIDE EFFECTS</span>
              </div>
              <div className="space-y-2">
                {runs.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => {
                      if (r.id === 102) return;
                      setSelectedRunId(r.id);
                      setActiveTab("run-detail");
                    }}
                    className={`flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] p-3 transition-all ${
                      r.id === 102 ? "cursor-default opacity-85" : "hover:border-amber-500/40 cursor-pointer"
                    }`}
                  >

                    <div>
                      <div className="font-bold text-white">#{r.display_id} — {r.agent_type}</div>
                      <div className="text-[10px] text-zinc-500 mt-0.5">Created {r.created_at}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${
                          r.status === "needs_review"
                            ? "border border-amber-500/40 bg-amber-500/10 text-amber-400 font-mono uppercase"
                            : "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        }`}
                      >
                        {r.status}
                      </span>
                      <span className="rounded bg-white/5 px-2 py-0.5 text-zinc-300 font-mono text-[10px]">{r.owner_worker_id || "unassigned"}</span>
                    </div>

                    <div className="text-right">
                      <div className="text-emerald-400 font-bold">0 duplicates</div>
                      <div className="text-[10px] text-zinc-500">{r.summary.handoff_count} handoffs</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VIEW 3: RUNS - NEEDS REVIEW */}
          {activeTab === "runs-needs-review" && (
            <div className="space-y-4 font-mono text-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-4 backdrop-blur-2xl">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-ui text-sm font-bold uppercase tracking-wider text-white">Needs Review Queue</h2>
                    <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 font-mono text-[10px] text-amber-400 border border-amber-500/30 font-semibold">
                      1 PENDING
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                    Runs halted at the uncertainty window following a worker crash during non-idempotent tool execution
                  </p>
                </div>
              </div>

              {/* Needs Review Item Card matching real operator console */}
              <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 backdrop-blur-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="font-mono text-xs font-bold text-white flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <span>r102 · financial_payout_agent</span>
                  </div>
                  <span className="rounded-full border border-amber-500/40 bg-amber-500/20 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-amber-300">
                    ACTION REQUIRED
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-zinc-400">
                  <span>agent: <strong className="text-white">financial_payout_agent</strong></span>
                  <span className="text-zinc-600">·</span>
                  <span>failing step: <strong className="text-white">2 (check_compliance)</strong></span>
                  <span className="text-zinc-600">·</span>
                  <span>last owner: <strong className="text-white">worker-c#1</strong></span>
                </div>

                {/* Operator Resolution Action Badges (Static Display) */}
                <div className="border-t border-white/10 pt-3 space-y-2">
                  <div className="text-[11px] font-semibold text-white">Available operator resolutions:</div>
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-xl border border-amber-500/40 bg-amber-500/15 px-3 py-1 text-[11px] font-mono font-medium text-amber-300">
                      mark executed
                    </span>
                    <span className="rounded-xl border border-amber-500/40 bg-amber-500/15 px-3 py-1 text-[11px] font-mono font-medium text-amber-300">
                      mark not executed
                    </span>
                    <span className="rounded-xl border border-amber-500/40 bg-amber-500/15 px-3 py-1 text-[11px] font-mono font-medium text-amber-300">
                      retry
                    </span>
                  </div>
                </div>

              </div>
            </div>
          )}



          {/* VIEW 4: RUN DETAIL */}
          {activeTab === "run-detail" && (
            <div className="space-y-3">
              {/* Back to All Runs Breadcrumb Navigation */}
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setActiveTab("runs-all")}
                  className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-bold text-zinc-300 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
                >
                  <span>← Back to All Runs</span>
                </button>

                <div className="text-[10px] text-zinc-400 font-mono">
                  Viewing Run Details for <strong className="text-white">#{timeline.display_id}</strong>
                </div>
              </div>

              {/* 15-Strand Golden Ribbon SVG Component */}
              <div className="rounded-xl border border-amber-500/30 bg-black/90 p-3 space-y-1 shadow-2xl">
                <div className="flex items-center justify-between text-[10px] text-zinc-400 font-bold uppercase tracking-wider px-1 border-b border-white/10 pb-1.5">
                  <span className="flex items-center gap-1.5 text-white">
                    <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                    <span>RUNTIME EXECUTION STREAM</span>
                  </span>
                  <span className="text-amber-400 font-bold">
                    🔵 MODEL CALL | 🟧 TOOL CALL | 🟩 REPLAYED | ⇄ WORKER SWAP
                  </span>
                </div>
                <RunThread segments={timeline.segments} />
              </div>



              {/* Run Segments & Handoff Stream */}
              <div className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                  <div>
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Run #{timeline.display_id} — {timeline.agent_type}
                    </span>
                    <span className="ml-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[9px] text-emerald-400 font-bold uppercase">
                      {timeline.status}
                    </span>
                  </div>
                  <div className="text-[10px] text-zinc-400">
                    Active Epoch: <strong className="text-amber-400">{timeline.segments[timeline.segments.length - 1]?.epoch || 1}</strong>
                  </div>
                </div>

                {/* Segments Stream */}
                <div className="space-y-3 pt-1">
                  {timeline.segments.map((seg, idx) => (
                    <React.Fragment key={seg.worker_id}>
                      {idx > 0 && (
                        <div className="flex items-center justify-between rounded-xl border border-amber-500/50 bg-amber-500/10 px-4 py-2 text-xs font-mono text-amber-300 shadow-glow-gold">
                          <div className="flex items-center gap-2 font-bold">
                            <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                            <span>⚡ WORKER SWAP & LEASE RECLAMATION (EPOCH {seg.epoch})</span>
                          </div>
                          <span className="text-[10px] text-amber-200 font-semibold">
                            worker-a#1 SIGKILL → worker-b#1 (epoch {(seg.epoch || 2) - 1} → {seg.epoch || 2})
                          </span>
                        </div>
                      )}

                      <div
                        className={`rounded-xl border p-3.5 space-y-2 ${
                          seg.ended_at
                            ? "border-rose-500/30 bg-rose-500/[0.03]"
                            : "border-emerald-500/30 bg-emerald-500/[0.03]"
                        }`}
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white">{seg.worker_id}</span>
                            <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-zinc-300">
                              {seg.claim_reason || "owner"}
                            </span>
                          </div>
                          <span className="text-zinc-500">{seg.ended_at ? "Terminated (SIGKILL)" : "Active Owner"}</span>
                        </div>

                        {/* Worker Progress Bar */}
                        <WorkerBar segment={seg} />

                        {/* Steps */}
                        <div className="space-y-1.5 pt-1">
                          {seg.steps.map((st) => (
                            <div
                              key={st.step_index}
                              className="flex items-center justify-between rounded-lg bg-black/40 px-3 py-1.5 text-[11px] border border-white/5"
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-zinc-500 font-bold">#{st.step_index}</span>
                                <span className="text-zinc-200 font-semibold">{st.name}</span>
                                <span
                                  className={`rounded px-1.5 py-0.2 text-[9px] font-bold uppercase ${
                                    st.action_kind === "model"
                                      ? "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                                      : "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                                  }`}
                                >
                                  {st.action_kind || "tool"}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                {st.executed ? (
                                  <span className="text-emerald-400 font-bold">executed</span>
                                ) : (
                                  <span className="text-amber-400 font-bold">replayed (skipped side-effect)</span>
                                )}
                                <span className="text-[10px] font-mono text-zinc-500">{st.idempotency_key_display}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </React.Fragment>
                  ))}
                </div>

              </div>
            </div>
          )}

          {/* VIEW 5: WORKERS - FLEET */}
          {activeTab === "workers-fleet" && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {workers.map((w) => (
                <div key={w.id} className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-2">
                  <div className="flex items-center justify-between border-b border-white/10 pb-2">
                    <span className="font-bold text-white">{w.id}</span>
                    <span className="rounded-full bg-emerald-500/20 text-emerald-400 px-2 py-0.5 text-[9px] font-bold">
                      HEALTHY
                    </span>
                  </div>
                  <div className="text-[10px] text-zinc-400 space-y-1">
                    <div>Host: {w.hostname}</div>
                    <div>PID: {w.pid}</div>
                    <div>Heartbeat: {w.heartbeat_age_ms}ms ago</div>
                    <div>Capacity: {w.current_run_count} / {w.capacity} runs</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* VIEW 6: WORKERS - DEPLOYMENTS */}
          {activeTab === "workers-deployments" && (
            <div className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-3">
              <div className="text-xs font-bold text-white uppercase tracking-wider mb-2">Build Deployments Matrix</div>
              <div className="space-y-2">
                <div className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div>
                    <div className="font-bold text-emerald-400">v1.4.8-prod (Active Release)</div>
                    <div className="text-[10px] text-zinc-400 mt-0.5">Schema Revision: 005_chaos</div>
                  </div>
                  <span className="rounded bg-emerald-500/20 text-emerald-300 px-2.5 py-1 text-[10px] font-bold">
                    3 Active Workers
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* VIEW 7: CHAOS - CHAOS CONSOLE */}
          {activeTab === "chaos-console" && (
            <div className="space-y-4">
              {/* Chaos Console Architectural Explanation Header */}
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/[0.04] p-4 space-y-2 font-mono text-xs shadow-lg">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Flame className="h-4 w-4 text-rose-400" />
                    <span className="font-extrabold text-white text-xs uppercase tracking-wider">
                      Live Chaos Fault Injection Harness
                    </span>
                    <span className="rounded-full border border-rose-500/40 bg-rose-500/20 px-2 py-0.5 text-[9.5px] text-rose-300 font-bold">
                      Adversarial Testing
                    </span>
                  </div>
                  <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    5 / 5 SQL INVARIANTS PROVED
                  </span>
                </div>
                <p className="text-[11px] text-zinc-300 font-sans leading-relaxed">
                  The <strong className="text-white">Chaos Console</strong> simulates hard process terminations (<code className="text-rose-300">SIGKILL</code>) mid-step while multi-tool agents execute side-effects. Anchor's database engine enforces atomic two-phase tool journaling (<code className="text-amber-300">INTENT</code> / <code className="text-emerald-300">RESULT</code>) and monotonic epoch fencing (<code className="text-amber-300">AN001</code>) — guaranteeing zero duplicate API calls and sub-second crash recovery natively in PostgreSQL.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1.5 border-t border-white/10 text-[10px]">
                  <div className="flex items-center gap-1.5 text-zinc-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    <span>0 Duplicate Side-Effects</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-zinc-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                    <span>Monotonic Epoch Fencing</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-zinc-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
                    <span>Sub-Second Crash Recovery</span>
                  </div>
                </div>
              </div>

              <ChaosVisualizer activeRun={timeline} report={chaosReport} />
            </div>
          )}

          {/* VIEW 8: CHAOS - RUN HISTORY */}
          {activeTab === "chaos-history" && (
            <div className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-3">
              <div className="text-xs font-bold text-white uppercase tracking-wider mb-2">Chaos Experiment Reports History</div>
              <div className="space-y-2">
                <div className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div>
                    <div className="font-bold text-white">Report #42 — 15 Runs Submitted</div>
                    <div className="text-[10px] text-zinc-400 mt-0.5">4 Kills Injected • P50: 3100ms</div>
                  </div>
                  <span className="text-emerald-400 font-bold text-[11px]">0 VIOLATIONS</span>
                </div>
              </div>
            </div>
          )}

          {/* VIEW 9: TOOLS - REGISTRY */}
          {activeTab === "tools-registry" && (
            <div className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-3">
              <div className="text-xs font-bold text-white uppercase tracking-wider mb-2">Registered Execution Tools</div>
              <div className="space-y-2">
                {[
                  { name: "initialize_eval_sandbox", safety: "retry_safe", desc: "Spawns isolated candidate sandbox" },
                  { name: "compile_candidate_solution", safety: "retry_safe", desc: "Compiles code with strict flags" },
                  { name: "run_unit_test_suite", safety: "reconcilable", desc: "Executes test runner & reconciles log" },
                  { name: "send_candidate_result_email", safety: "unsafe", desc: "Dispatches result email" },
                ].map((t) => (
                  <div key={t.name} className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] p-3">
                    <div>
                      <div className="font-bold text-white">{t.name}</div>
                      <div className="text-[10px] text-zinc-400 mt-0.5">{t.desc}</div>
                    </div>
                    <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${
                      t.safety === "retry_safe" ? "bg-emerald-500/20 text-emerald-300" :
                      t.safety === "reconcilable" ? "bg-amber-500/20 text-amber-300" : "bg-rose-500/20 text-rose-300"
                    }`}>
                      {t.safety}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VIEW 10: TOOLS - TEST RUN */}
          {activeTab === "tools-test-run" && (
            <div className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-3 font-mono text-xs">
              <div className="text-xs font-bold text-white uppercase tracking-wider mb-2">Interactive Tool Call Tester</div>
              <div className="rounded-lg border border-white/5 bg-black/80 p-3 space-y-2">
                <div className="text-[10px] text-zinc-400">Derived Idempotency Key:</div>
                <div className="text-amber-400 font-bold">r101:s0:init:a1b2c3d4</div>
              </div>
            </div>
          )}

          {/* VIEW 11: OBSERVABILITY - METRICS */}
          {activeTab === "observability-metrics" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
                <div className="rounded-xl border border-white/10 bg-black/60 p-3">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Duplicate Side Effects</div>
                  <div className="text-lg font-bold text-emerald-400 mt-0.5">0</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/60 p-3">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Stranded Runs</div>
                  <div className="text-lg font-bold text-emerald-400 mt-0.5">0</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/60 p-3">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Recovery P50</div>
                  <div className="text-lg font-bold text-amber-400 mt-0.5">{chaosReport.recovery_ms_p50}ms</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/60 p-3">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Kills Injected</div>
                  <div className="text-lg font-bold text-rose-400 mt-0.5">{chaosReport.kills_injected}</div>
                </div>
              </div>
            </div>
          )}

          {/* VIEW 12: OBSERVABILITY - LOGS */}
          {activeTab === "observability-logs" && (
            <div className="rounded-xl border border-white/10 bg-black/80 p-4 space-y-2">
              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-[11px] text-zinc-400 font-bold">
                <span>SEQUENCE & EVENT TYPE</span>
                <span>EPOCH & WORKER</span>
              </div>
              <div className="space-y-1.5">
                {events.map((ev) => (
                  <div
                    key={ev.seq}
                    className="flex items-center justify-between text-[11px] py-1 border-b border-white/[0.04] text-zinc-300"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-zinc-500 font-mono">#{ev.seq}</span>
                      <span className="font-bold text-amber-400">{ev.type}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-zinc-400">epoch {ev.epoch}</span>
                      <span className="rounded bg-white/5 px-1.5 py-0.5 text-zinc-300">{ev.worker_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VIEW 13: SETTINGS - ENVIRONMENT & RATE LIMITS */}
          {activeTab === "settings-environment" && (
            <div className="rounded-xl border border-white/10 bg-black/60 p-4 space-y-4 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <div>
                  <div className="text-xs font-bold text-white uppercase tracking-wider">Cluster Configuration & Rate Limits</div>
                  <div className="text-[10px] text-zinc-400">Configure rate-limiting buckets and lease settings within safe bounds.</div>
                </div>
                <span className="rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 text-[9px] font-bold">
                  LOCAL EDITABLE MODE
                </span>
              </div>

              {/* Rate Limits Section */}
              <div className="space-y-3">
                <div className="text-[11px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                  <span>⚡ Request Rate Limits (Token Buckets)</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="rounded-lg border border-white/10 bg-black/40 p-3 space-y-1">
                    <label className="text-[10px] text-zinc-400 block font-bold">Submission Rate Limit</label>
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="1"
                        max="10000"
                        defaultValue="60"
                        className="w-full rounded border border-white/20 bg-zinc-900 px-2 py-1 text-white font-bold focus:border-amber-400 focus:outline-none"
                      />
                      <span className="text-[10px] text-zinc-500">req/min</span>
                    </div>
                    <div className="text-[9px] text-zinc-500">Allowed: 1 - 10,000 req/min</div>
                  </div>

                  <div className="rounded-lg border border-white/10 bg-black/40 p-3 space-y-1">
                    <label className="text-[10px] text-zinc-400 block font-bold">Kill Worker Limit</label>
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        defaultValue="30"
                        className="w-full rounded border border-white/20 bg-zinc-900 px-2 py-1 text-white font-bold focus:border-amber-400 focus:outline-none"
                      />
                      <span className="text-[10px] text-zinc-500">req/min</span>
                    </div>
                    <div className="text-[9px] text-zinc-500">Allowed: 1 - 1,000 req/min</div>
                  </div>

                  <div className="rounded-lg border border-white/10 bg-black/40 p-3 space-y-1">
                    <label className="text-[10px] text-zinc-400 block font-bold">Demo Hourly Cap</label>
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="1"
                        max="50000"
                        defaultValue="1000"
                        className="w-full rounded border border-white/20 bg-zinc-900 px-2 py-1 text-white font-bold focus:border-amber-400 focus:outline-none"
                      />
                      <span className="text-[10px] text-zinc-500">runs/hr</span>
                    </div>
                    <div className="text-[9px] text-zinc-500">Allowed: 1 - 50,000 runs/hr</div>
                  </div>
                </div>
              </div>

              {/* Timing & Concurrency Section */}
              <div className="space-y-3 pt-2 border-t border-white/10">
                <div className="text-[11px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                  <span>⏱️ Lease & Concurrency Invariants</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="flex items-center justify-between py-1.5 border-b border-white/5">
                    <div>
                      <div className="text-zinc-300 font-semibold">Lease Duration</div>
                      <div className="text-[9px] text-zinc-500">Worker claim lease TTL</div>
                    </div>
                    <span className="font-bold text-amber-400">4,000 ms</span>
                  </div>
                  <div className="flex items-center justify-between py-1.5 border-b border-white/5">
                    <div>
                      <div className="text-zinc-300 font-semibold">Renewal Interval</div>
                      <div className="text-[9px] text-zinc-500">Heartbeat renew cadence</div>
                    </div>
                    <span className="font-bold text-amber-400">1,000 ms</span>
                  </div>
                  <div className="flex items-center justify-between py-1.5 border-b border-white/5">
                    <div>
                      <div className="text-zinc-300 font-semibold">Per-Worker Concurrency</div>
                      <div className="text-[9px] text-zinc-500">Max parallel runs per replica</div>
                    </div>
                    <span className="font-bold text-amber-400">10 runs / worker</span>
                  </div>
                  <div className="flex items-center justify-between py-1.5 border-b border-white/5">
                    <div>
                      <div className="text-zinc-300 font-semibold">Global Concurrency Cap</div>
                      <div className="text-[9px] text-zinc-500">Total cluster run ceiling</div>
                    </div>
                    <span className="font-bold text-amber-400">50 runs</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2 border-t border-white/10">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => alert("Rate limits updated! Active on anchor-api.")}
                    className="rounded-lg bg-amber-500/20 border border-amber-500/40 px-3 py-1.5 text-[11px] font-bold text-amber-300 hover:bg-amber-500/30 transition-all cursor-pointer"
                  >
                    Save & Apply Rate Limits
                  </button>
                  <span className="text-[10px] text-zinc-500">Validates bounds before PATCH /api/config</span>
                </div>
                <span className="text-[10px] text-emerald-400 font-bold">✓ Bounds Verified (FR-063)</span>
              </div>
            </div>
          )}
        </div>

        {/* Docked Collapsible Terminal Console at Bottom */}
        <TerminalConsole />

        {/* Footer Status Bar */}
        <div className="flex items-center justify-between border-t border-white/10 bg-black/60 px-4 py-2 text-[10px] text-zinc-400 shrink-0">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Connected to Anchor Engine v1.4.8</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-zinc-500 font-mono">5 Active Worker Nodes</span>
            <span>•</span>
            <div className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400 font-bold">0 Duplicate Side-Effects</span>
            </div>
          </div>
        </div>
      </div>


      {/* System Inspector Slide-Out Drawer */}
      {isInspectorOpen && <SystemInspector onClose={() => setIsInspectorOpen(false)} />}
    </div>
  );
};

export const MiniOperatorConsole: React.FC = () => {
  return (
    <DemoProvider>
      <div className="w-full max-w-5xl h-[640px] mx-auto my-6">
        <MiniOperatorConsoleContent />
      </div>
    </DemoProvider>
  );
};


