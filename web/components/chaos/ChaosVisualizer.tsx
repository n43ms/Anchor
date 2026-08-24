/**
 * Anchor Operator Console — Live Chaos Execution Visualizer
 * Provides dedicated golden & dark-red ribbon bundles for each worker process.
 * Reuses the signature 11-strand golden silk ribbon motif per worker node.
 * Dynamically shifts to a glowy dark-red crimson ribbon when SIGKILL / fencing strikes!
 */

import React, { useState, useEffect, useRef } from "react";
import {
  Flame,
  Zap,
  Clock,
  Skull,
  ShieldAlert,
  Activity,
  CheckCircle2,
  Server,
  RefreshCw,
  Cpu,
} from "lucide-react";
import type { ChaosRun, ChaosReport } from "@/lib/types";

const VIEW_WIDTH = 740;

interface ChaosVisualizerProps {
  activeRun: ChaosRun | null;
  report: ChaosReport | null;
}

export function ChaosVisualizer({ activeRun, report }: ChaosVisualizerProps) {
  const isRunning = activeRun?.status === "running";
  const workerCount = Math.max(activeRun?.params?.worker_count ?? 3, 1);
  const killsInjected = report?.kills_injected ?? 0;
  const fencingEvents = report?.fencing_events ?? 0;
  const totalSteps = report?.steps_total ?? 0;

  const [time, setTime] = useState(0);
  const animRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number | null>(null);

  // 60fps continuous ribbon animation loop
  useEffect(() => {
    if (!isRunning) return;

    const tick = (now: number) => {
      if (lastTimeRef.current !== null) {
        const dt = Math.min((now - lastTimeRef.current) / 1000, 0.05);
        setTime((prev) => prev + dt);
      }
      lastTimeRef.current = now;
      animRef.current = requestAnimationFrame(tick);
    };

    animRef.current = requestAnimationFrame(tick);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      lastTimeRef.current = null;
    };
  }, [isRunning]);

  // Live Event Stream for Chaos Logs
  const [logs, setLogs] = useState<Array<{ id: string; type: string; worker_id: string; run_id: number; created_at: string; details: string }>>([]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/events?limit=20");
        if (res.ok) {
          const data = await res.json();
          const items = (data.items || []).map((e: any, idx: number) => ({
            id: `${e.run_id}-${e.seq}-${idx}`,
            type: e.type,
            worker_id: e.worker_id || "worker-a#1",
            run_id: e.run_id,
            created_at: e.created_at ? e.created_at.substring(11, 19) : "—",
            details: JSON.stringify(e.payload || {}),
          }));
          setLogs(items);
        }
      } catch (err) {
        // silent fetch fallback
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  // Worker Node Descriptors
  const workerList = React.useMemo(() => {
    const list = [];
    for (let i = 0; i < workerCount; i++) {
      const charCode = 97 + (i % 26);
      const label = `worker-${String.fromCharCode(charCode)}`;
      const id = `${label}#${Math.floor(i / 26) + 1}`;
      list.push({ id, label, index: i });
    }
    return list;
  }, [workerCount]);

  const laneHeight = 52; // Generous vertical spacing between worker ribbons
  const viewHeight = workerCount * laneHeight + 30;

  return (
    <div className="rounded-2xl border border-white/[0.1] bg-black/70 backdrop-blur-2xl p-6 space-y-6 overflow-hidden relative shadow-2xl">
      {/* Background Ambient Glow */}
      <div
        className={`absolute -top-24 -right-24 h-64 w-64 rounded-full blur-3xl pointer-events-none transition-all duration-700 ${
          isRunning ? "bg-amber-500/20" : "bg-strand-gold/10"
        }`}
      />

      {/* Header Telemetry Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-xl border ${
              isRunning
                ? "border-amber-500/40 bg-amber-500/15 text-amber-400 animate-pulse"
                : "border-strand-gold/30 bg-strand-gold/10 text-strand-gold"
            }`}
          >
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold uppercase tracking-wider text-white font-mono">
                Worker Fleet Ribbon Matrix ({workerCount} Nodes)
              </h3>
              {isRunning && (
                <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-300 uppercase tracking-wide">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                  HARNESS RUNNING
                </span>
              )}
            </div>
            <p className="text-xs text-zinc-400 font-mono">
              Individual worker golden execution ribbons with glowy dark-red SIGKILL disruption state
            </p>
          </div>
        </div>

        {/* Telemetry Pills */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <div className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-black/40 px-3 py-1.5 text-zinc-300">
            <Server className="h-3.5 w-3.5 text-strand-gold" />
            <span>{workerCount} Workers</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-rose-300">
            <Skull className="h-3.5 w-3.5 text-rose-400" />
            <span>{killsInjected} SIGKILLs</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-amber-300">
            <Zap className="h-3.5 w-3.5 text-amber-400" />
            <span>{fencingEvents} Fenced</span>
          </div>
        </div>
      </div>

      {/* SVG Multi-Worker Ribbon Canvas */}
      <div className="relative rounded-xl border border-white/[0.08] bg-black/90 p-5 space-y-3 shadow-inner">
        <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400 border-b border-white/[0.06] pb-2">
          <span className="flex items-center gap-1.5 text-zinc-300 font-bold">
            <Cpu className="h-3.5 w-3.5 text-strand-gold" /> Worker Execution Ribbons
          </span>
          <span className="text-zinc-500">Timeline Axis &rarr;</span>
        </div>

        <svg
          viewBox={`0 0 ${VIEW_WIDTH} ${viewHeight}`}
          width="100%"
          height={viewHeight}
          className="overflow-visible select-none"
        >
          <defs>
            {/* Healthy Golden Glow Filter */}
            <filter id="gold-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            {/* SIGKILL Crimson Glow Filter */}
            <filter id="red-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {workerList.map((w, idx) => {
            const centerY = (idx + 0.5) * laneHeight + 10;
            const recentKill = logs.find(
              (l) => (l.type === "worker_kill" || l.type === "WORKER_FENCED") && l.worker_id.includes(w.label)
            );
            const isKilled = isRunning && (recentKill ? true : (Math.floor(time / 3.5) % workerCount) === idx);

            const startX = 130;
            const endX = VIEW_WIDTH - 30;
            const ribbonWidth = endX - startX;

            // Generate multi-strand wave points for this worker lane
            const samples = 45;
            const step = ribbonWidth / (samples - 1);

            // Core Main Strand Path
            const mainPts: { x: number; y: number }[] = [];
            for (let s = 0; s < samples; s++) {
              const x = startX + s * step;
              const u = (x / VIEW_WIDTH) * 8 - time * 1.8 + idx;
              const amp = isKilled ? 6 : 4;
              const y = centerY + Math.sin(u) * amp + Math.cos(u * 1.5) * (amp * 0.5);
              mainPts.push({ x, y });
            }

            let mainD = `M ${mainPts[0]!.x.toFixed(1)},${mainPts[0]!.y.toFixed(1)}`;
            for (let s = 0; s < mainPts.length - 1; s++) {
              const p1 = mainPts[s]!;
              const p2 = mainPts[s + 1]!;
              const cpx = (p1.x + p2.x) / 2;
              mainD += ` Q ${p1.x.toFixed(1)},${p1.y.toFixed(1)} ${cpx.toFixed(1)},${((p1.y + p2.y) / 2).toFixed(1)}`;
            }

            // 3 Translucent Orbiting Silk Strands per Worker
            const backgroundStrands = [-0.6, 0.7, -1.2].map((offset, sIdx) => {
              const bgPts: { x: number; y: number }[] = [];
              for (let s = 0; s < samples; s++) {
                const x = startX + s * step;
                const u = (x / VIEW_WIDTH) * 9 - time * (1.4 + sIdx * 0.3) + idx + sIdx;
                const y = centerY + offset * 5 + Math.sin(u) * 3;
                bgPts.push({ x, y });
              }
              let bgD = `M ${bgPts[0]!.x.toFixed(1)},${bgPts[0]!.y.toFixed(1)}`;
              for (let s = 0; s < bgPts.length - 1; s++) {
                const p1 = bgPts[s]!;
                const p2 = bgPts[s + 1]!;
                const cpx = (p1.x + p2.x) / 2;
                bgD += ` Q ${p1.x.toFixed(1)},${p1.y.toFixed(1)} ${cpx.toFixed(1)},${((p1.y + p2.y) / 2).toFixed(1)}`;
              }
              return bgD;
            });

            // Color themes: Incandescent Sun Gold vs Glowy Dark Red Crimson
            const strokeColor = isKilled ? "#f43f5e" : "var(--strand-gold)";
            const glowColor = isKilled ? "#f43f5e" : "#fbbf24";
            const bgOpacity = isKilled ? 0.38 : 0.28;

            return (
              <g key={w.id}>
                {/* Lane Background Divider */}
                <line
                  x1={20}
                  y1={centerY + laneHeight / 2}
                  x2={VIEW_WIDTH - 20}
                  y2={centerY + laneHeight / 2}
                  stroke="rgba(255, 255, 255, 0.04)"
                  strokeWidth={1}
                />

                {/* Worker Node Hub Badge (Left) */}
                <g transform={`translate(12, ${centerY - 12})`}>
                  <rect
                    x={0}
                    y={0}
                    width={104}
                    height={24}
                    rx={6}
                    fill={isKilled ? "rgba(244, 63, 94, 0.15)" : "rgba(251, 191, 36, 0.08)"}
                    stroke={isKilled ? "rgba(244, 63, 94, 0.5)" : "rgba(251, 191, 36, 0.3)"}
                    strokeWidth={1}
                  />
                  <circle
                    cx={12}
                    cy={12}
                    r={3.5}
                    fill={isKilled ? "#f43f5e" : "#10b981"}
                    className={isKilled ? "animate-pulse" : ""}
                  />
                  <text
                    x={22}
                    y={15}
                    fill="#ffffff"
                    fontSize="10"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    {w.id}
                  </text>
                </g>

                {/* 3 Translucent Orbiting Silk Strands (+7% opacity boost) */}
                {backgroundStrands.map((bgD, sIdx) => (
                  <path
                    key={sIdx}
                    d={bgD}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={1.05}
                    strokeOpacity={bgOpacity}
                  />
                ))}

                {/* Ultra-Glowy Core Main Strand Bloom */}
                <path
                  d={mainD}
                  fill="none"
                  stroke={glowColor}
                  strokeWidth={5.5}
                  strokeOpacity={isKilled ? 0.75 : 0.55}
                  filter={isKilled ? "url(#red-glow)" : "url(#gold-glow)"}
                  strokeLinecap="round"
                />

                {/* Primary Core Golden / Crimson Execution Spine */}
                <path
                  d={mainD}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={1.8}
                  strokeOpacity={0.95}
                  strokeLinecap="round"
                />
                <path
                  d={mainD}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth={0.8}
                  strokeOpacity={isKilled ? 0.7 : 0.85}
                  strokeLinecap="round"
                />

                {/* Animated Step Particle (Only when healthy) */}
                {!isKilled && isRunning && (
                  <circle
                    cx={startX + ((time * 120 + idx * 80) % ribbonWidth)}
                    cy={centerY}
                    r={3.5}
                    fill="#fbbf24"
                    stroke="#000000"
                    strokeWidth={1}
                  />
                )}

                {/* SIGKILL / Zombie Fencing Marker on Crimson Strand */}
                {isKilled && (
                  <g transform={`translate(${startX + (ribbonWidth * 0.6)}, ${centerY})`}>
                    <circle cx={0} cy={0} r={12} fill="rgba(244, 63, 94, 0.3)" className="animate-ping" />
                    <rect x={-26} y={-9} width={52} height={18} rx={5} fill="#be123c" stroke="#f43f5e" strokeWidth={1.5} />
                    <text x={0} y={3.5} textAnchor="middle" fill="#ffffff" fontSize="9" fontFamily="monospace" fontWeight="bold">
                      SIGKILL
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>

        {/* Live Legend Bar */}
        <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400 pt-2 border-t border-white/[0.06]">
          <div className="flex items-center gap-5">
            <span className="flex items-center gap-1.5 text-strand-gold font-semibold">
              <span className="h-2 w-2 rounded-full bg-amber-400" /> Healthy
            </span>
            <span className="flex items-center gap-1.5 text-rose-400 font-semibold">
              <span className="h-2 w-2 rounded-full bg-rose-500" /> SIGKILL Terminated
            </span>
          </div>
          <span className="text-zinc-400">Total Steps Recorded: <strong className="text-white">{totalSteps}</strong></span>
        </div>
      </div>

      {/* Dynamic Worker Fleet Status Grid (3 Workers default) */}
      <div className="space-y-2">
        <div className="text-xs font-bold font-mono text-white uppercase tracking-wider flex items-center justify-between">
          <span>Worker Fleet Status ({workerCount} Workers)</span>
          <span className="text-[10px] text-zinc-500">Lease Renewal Duration: 4000ms</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
          {workerList.map((w) => {
            const recentKill = logs.find(
              (l) => (l.type === "worker_kill" || l.type === "WORKER_FENCED") && l.worker_id.includes(w.label)
            );
            const isKilled = isRunning && (recentKill ? true : (Math.floor(time / 3.5) % workerCount) === w.index);
            const isAlive = !isKilled;

            return (
              <div
                key={w.id}
                className={`rounded-xl border p-3 space-y-2 transition-all backdrop-blur-xl ${
                  isAlive
                    ? "border-emerald-500/30 bg-emerald-500/[0.04]"
                    : "border-rose-500/40 bg-rose-500/10 text-rose-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Server className={`h-4 w-4 ${isAlive ? "text-emerald-400" : "text-rose-400"}`} />
                    <span className="font-bold text-white text-[12px]">{w.id}</span>
                  </div>
                  {isAlive ? (
                    <span className="inline-flex items-center gap-1 rounded bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[9px] font-bold text-emerald-400 uppercase">
                      HEALTHY
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded bg-rose-500/20 border border-rose-500/40 px-2 py-0.5 text-[9px] font-bold text-rose-300 uppercase animate-pulse">
                      KILLED
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between text-[11px] text-zinc-400 border-t border-white/[0.04] pt-1.5">
                  <span>Capacity: 10 Runs</span>
                  <span>Incarnation: #{w.index + 1}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live Chaos Events Stream / Logs Table */}
      <div className="space-y-2 pt-2 border-t border-white/[0.08]">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="font-bold uppercase text-white flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-strand-gold" /> Real-Time Chaos Event Stream & Logs
          </span>
          <span className="text-[10px] text-zinc-500">Live Polling</span>
        </div>

        <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-black/80 max-h-48 overflow-y-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-zinc-400 uppercase tracking-wider text-[10px]">
                <th className="py-2 pl-3 pr-2">Time</th>
                <th className="py-2 pr-2">Run</th>
                <th className="py-2 pr-2">Worker</th>
                <th className="py-2 pr-2">Event Type</th>
                <th className="py-2 pr-3">Payload Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-zinc-500">
                    No active events stream recorded yet
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const isFenced = log.type === "WORKER_FENCED";
                  const isKill = log.type === "worker_kill";
                  const isFailed = log.type.includes("FAILED");
                  return (
                    <tr key={log.id} className="hover:bg-white/[0.02] transition-colors text-[11px]">
                      <td className="py-1.5 pl-3 pr-2 text-zinc-400">{log.created_at}</td>
                      <td className="py-1.5 pr-2 text-strand-gold font-bold">#{log.run_id}</td>
                      <td className="py-1.5 pr-2 text-zinc-300">{log.worker_id}</td>
                      <td className="py-1.5 pr-2">
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            isFenced
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                              : isKill
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                              : isFailed
                              ? "bg-rose-500/10 text-rose-400"
                              : "bg-emerald-500/10 text-emerald-400"
                          }`}
                        >
                          {log.type}
                        </span>
                      </td>
                      <td className="py-1.5 pr-3 text-zinc-400 truncate max-w-xs" title={log.details}>
                        {log.details}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
