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
import type { ChaosReport, RunTimeline } from "../lib/types";

const VIEW_WIDTH = 740;

interface ChaosVisualizerProps {
  activeRun?: RunTimeline | null;
  report?: ChaosReport | null;
}

export function ChaosVisualizer({ activeRun, report }: ChaosVisualizerProps) {
  const isRunning = true;
  const workerCount = 5;
  const killsInjected = report?.kills_injected ?? 4;
  const fencingEvents = report?.fencing_events_count ?? 4;
  const totalSteps = 42;

  const [time, setTime] = useState(0);
  const animRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number | null>(null);

  // 60fps continuous ribbon animation loop
  useEffect(() => {
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
  }, []);

  // Live Event Stream for Chaos Logs
  const [logs, setLogs] = useState<Array<{ id: string; type: string; worker_id: string; run_id: number; created_at: string; details: string }>>([
    { id: "1", type: "WORKER_FENCED", worker_id: "worker-c#1", run_id: 101, created_at: "16:32:01", details: "stale_epoch: 1, current_epoch: 2" },
    { id: "2", type: "worker_kill", worker_id: "worker-c#1", run_id: 101, created_at: "16:32:00", details: "process os._exit(137) injected" },
    { id: "3", type: "RUN_CLAIMED", worker_id: "worker-d#1", run_id: 101, created_at: "16:32:02", details: "reclaimed_after_lease_expiry (epoch 2)" },
    { id: "4", type: "STEP_COMPLETED", worker_id: "worker-d#1", run_id: 101, created_at: "16:32:04", details: "verify_epoch_fencing executed" },
  ]);

  // Rotate simulated kills across the 5 workers
  const workerList = [
    { id: "worker-a#1", label: "worker-a", index: 0 },
    { id: "worker-b#1", label: "worker-b", index: 1 },
    { id: "worker-c#1", label: "worker-c", index: 2 },
    { id: "worker-d#1", label: "worker-d", index: 3 },
    { id: "worker-e#1", label: "worker-e", index: 4 },
  ];

  const laneHeight = 48;
  const viewHeight = workerCount * laneHeight + 20;

  return (
    <div className="rounded-2xl border border-white/[0.1] bg-black/70 backdrop-blur-2xl p-5 space-y-5 overflow-hidden relative shadow-2xl font-mono text-xs select-none">
      {/* Background Ambient Glow */}
      <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full blur-3xl pointer-events-none bg-amber-500/10" />

      {/* Header Telemetry Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-amber-500/40 bg-amber-500/15 text-amber-400 animate-pulse">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                Worker Fleet Execution Stream ({workerCount} Nodes)
              </h3>
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/20 px-2 py-0.5 text-[9px] font-bold text-amber-300 uppercase tracking-wide">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                HARNESS RUNNING
              </span>
            </div>
            <p className="text-[10px] text-zinc-400 font-sans">
              Per-worker execution thread telemetry with live SIGKILL fault injection state
            </p>
          </div>
        </div>

        {/* Telemetry Pills */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-black/40 px-2.5 py-1 text-zinc-300">
            <Server className="h-3.5 w-3.5 text-amber-400" />
            <span>{workerCount} Workers</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-rose-300">
            <Skull className="h-3.5 w-3.5 text-rose-400" />
            <span>{killsInjected} SIGKILLs</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-amber-300">
            <Zap className="h-3.5 w-3.5 text-amber-400" />
            <span>{fencingEvents} Fenced</span>
          </div>
        </div>
      </div>

      {/* SVG Multi-Worker Execution Canvas */}
      <div className="relative rounded-xl border border-white/[0.08] bg-black/90 p-4 space-y-2 shadow-inner">
        <div className="flex items-center justify-between text-[10px] text-zinc-400 border-b border-white/[0.06] pb-1.5">
          <span className="flex items-center gap-1.5 text-zinc-300 font-bold">
            <Cpu className="h-3.5 w-3.5 text-amber-400" /> Worker Execution Threads
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
            <filter id="gold-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="red-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {workerList.map((w, idx) => {
            const centerY = (idx + 0.5) * laneHeight + 5;
            const isKilled = (Math.floor(time / 2.8) % workerCount) === idx;

            const startX = 120;
            const endX = VIEW_WIDTH - 20;
            const ribbonWidth = endX - startX;

            const samples = 40;
            const step = ribbonWidth / (samples - 1);

            const mainPts: { x: number; y: number }[] = [];
            for (let s = 0; s < samples; s++) {
              const x = startX + s * step;
              const u = (x / VIEW_WIDTH) * 8 - time * 1.8 + idx;
              const amp = isKilled ? 5 : 3.5;
              const y = centerY + Math.sin(u) * amp + Math.cos(u * 1.5) * (amp * 0.5);
              mainPts.push({ x, y });
            }

            let mainD = `M ${mainPts[0].x.toFixed(1)},${mainPts[0].y.toFixed(1)}`;
            for (let s = 0; s < mainPts.length - 1; s++) {
              const p1 = mainPts[s];
              const p2 = mainPts[s + 1];
              const cpx = (p1.x + p2.x) / 2;
              mainD += ` Q ${p1.x.toFixed(1)},${p1.y.toFixed(1)} ${cpx.toFixed(1)},${((p1.y + p2.y) / 2).toFixed(1)}`;
            }

            const backgroundStrands = [-0.6, 0.7, -1.2].map((offset, sIdx) => {
              const bgPts: { x: number; y: number }[] = [];
              for (let s = 0; s < samples; s++) {
                const x = startX + s * step;
                const u = (x / VIEW_WIDTH) * 9 - time * (1.4 + sIdx * 0.3) + idx + sIdx;
                const y = centerY + offset * 4 + Math.sin(u) * 2.5;
                bgPts.push({ x, y });
              }
              let bgD = `M ${bgPts[0].x.toFixed(1)},${bgPts[0].y.toFixed(1)}`;
              for (let s = 0; s < bgPts.length - 1; s++) {
                const p1 = bgPts[s];
                const p2 = bgPts[s + 1];
                const cpx = (p1.x + p2.x) / 2;
                bgD += ` Q ${p1.x.toFixed(1)},${p1.y.toFixed(1)} ${cpx.toFixed(1)},${((p1.y + p2.y) / 2).toFixed(1)}`;
              }
              return bgD;
            });

            const strokeColor = isKilled ? "#f43f5e" : "#f6c453";
            const glowColor = isKilled ? "#f43f5e" : "#fbbf24";
            const bgOpacity = isKilled ? 0.38 : 0.28;

            return (
              <g key={w.id}>
                {/* Lane Divider */}
                <line
                  x1={15}
                  y1={centerY + laneHeight / 2}
                  x2={VIEW_WIDTH - 15}
                  y2={centerY + laneHeight / 2}
                  stroke="rgba(255, 255, 255, 0.04)"
                  strokeWidth={1}
                />

                {/* Worker Node Hub Badge */}
                <g transform={`translate(10, ${centerY - 10})`}>
                  <rect
                    x={0}
                    y={0}
                    width={95}
                    height={20}
                    rx={5}
                    fill={isKilled ? "rgba(244, 63, 94, 0.15)" : "rgba(251, 191, 36, 0.08)"}
                    stroke={isKilled ? "rgba(244, 63, 94, 0.5)" : "rgba(251, 191, 36, 0.3)"}
                    strokeWidth={1}
                  />
                  <circle
                    cx={10}
                    cy={10}
                    r={3}
                    fill={isKilled ? "#f43f5e" : "#10b981"}
                    className={isKilled ? "animate-pulse" : ""}
                  />
                  <text x={18} y={13} fill="#ffffff" fontSize="9" fontWeight="bold">
                    {w.id}
                  </text>
                </g>

                {/* Orbiting Silk Strands */}
                {backgroundStrands.map((bgD, sIdx) => (
                  <path
                    key={sIdx}
                    d={bgD}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={1}
                    strokeOpacity={bgOpacity}
                  />
                ))}

                {/* Main Strand Glow */}
                <path
                  d={mainD}
                  fill="none"
                  stroke={glowColor}
                  strokeWidth={5}
                  strokeOpacity={isKilled ? 0.75 : 0.55}
                  filter={isKilled ? "url(#red-glow)" : "url(#gold-glow)"}
                  strokeLinecap="round"
                />

                {/* Primary Core Execution Spine */}
                <path
                  d={mainD}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={1.8}
                  strokeOpacity={0.95}
                  strokeLinecap="round"
                />

                {/* SIGKILL Disruption Marker on Crimson Strand */}
                {isKilled && (
                  <g transform={`translate(${startX + (ribbonWidth * 0.6)}, ${centerY})`}>
                    <circle cx={0} cy={0} r={10} fill="rgba(244, 63, 94, 0.3)" className="animate-ping" />
                    <rect x={-22} y={-8} width={44} height={16} rx={4} fill="#be123c" stroke="#f43f5e" strokeWidth={1.5} />
                    <text x={0} y={3} textAnchor="middle" fill="#ffffff" fontSize="8" fontWeight="bold">
                      SIGKILL
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>

        {/* Live Legend Bar */}
        <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1.5 border-t border-white/[0.06]">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-amber-400 font-semibold">
              <span className="h-2 w-2 rounded-full bg-amber-400" /> Active Execution Thread
            </span>
            <span className="flex items-center gap-1.5 text-rose-400 font-semibold">
              <span className="h-2 w-2 rounded-full bg-rose-500" /> SIGKILL Disrupted State
            </span>
          </div>
          <span>Total Steps Recorded: <strong className="text-white">{totalSteps}</strong></span>
        </div>
      </div>

      {/* Dynamic Worker Fleet Status Grid (5 Workers) */}
      <div className="space-y-2">
        <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center justify-between">
          <span>Worker Fleet Status ({workerCount} Workers)</span>
          <span className="text-[10px] text-zinc-500">Lease Renewal: 1000ms</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[10px]">
          {workerList.map((w) => {
            const isKilled = (Math.floor(time / 2.8) % workerCount) === w.index;

            return (
              <div
                key={w.id}
                className={`rounded-xl border p-2 space-y-1 transition-all ${
                  !isKilled
                    ? "border-emerald-500/30 bg-emerald-500/[0.04]"
                    : "border-rose-500/40 bg-rose-500/10 text-rose-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">{w.id}</span>
                  {!isKilled ? (
                    <span className="rounded bg-emerald-500/20 text-emerald-400 px-1.5 py-0.2 text-[8px] font-bold">
                      HEALTHY
                    </span>
                  ) : (
                    <span className="rounded bg-rose-500/20 text-rose-300 px-1.5 py-0.2 text-[8px] font-bold animate-pulse">
                      KILLED
                    </span>
                  )}
                </div>
                <div className="text-[9px] text-zinc-400">Cap: 10 Runs</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live Event Stream Table */}
      <div className="space-y-2 pt-2 border-t border-white/[0.08]">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold uppercase text-white flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-amber-400" /> Real-Time Chaos Event Stream
          </span>
          <span className="text-[10px] text-zinc-500">Live Polling</span>
        </div>

        <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-black/80 max-h-36 overflow-y-auto">
          <table className="w-full text-left text-[10px]">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-zinc-400 uppercase tracking-wider text-[9px]">
                <th className="py-1.5 pl-3 pr-2">Time</th>
                <th className="py-1.5 pr-2">Run</th>
                <th className="py-1.5 pr-2">Worker</th>
                <th className="py-1.5 pr-2">Event Type</th>
                <th className="py-1.5 pr-3">Payload Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-1 pl-3 pr-2 text-zinc-400">{log.created_at}</td>
                  <td className="py-1 pr-2 text-amber-400 font-bold">#{log.run_id}</td>
                  <td className="py-1 pr-2 text-zinc-300">{log.worker_id}</td>
                  <td className="py-1 pr-2">
                    <span
                      className={`inline-block px-1.5 py-0.2 rounded text-[9px] font-bold ${
                        log.type === "WORKER_FENCED"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          : log.type === "worker_kill"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : "bg-emerald-500/10 text-emerald-400"
                      }`}
                    >
                      {log.type}
                    </span>
                  </td>
                  <td className="py-1 pr-3 text-zinc-400 truncate max-w-xs">{log.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}



