/**
 * Anchor Operator Console — Collapsible Terminal Console
 * Positioned at bottom of operator console.
 * Monospace typography with bracketed timestamps [09:54:12].
 * Animated log line stream using Framer Motion spring physics.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, ChevronUp, ChevronDown, Trash2, Radio } from "lucide-react";

interface LogEntry {
  id: string;
  timestamp: string;
  level: "INFO" | "LEASE" | "HEAL" | "WARN" | "ERROR";
  message: string;
  source?: string;
}

const DEFAULT_LOGS: LogEntry[] = [
  {
    id: "log-1",
    timestamp: "09:54:02",
    level: "INFO",
    message: "Anchor runtime initialized — lease renewer active on cluster worker-1",
    source: "runtime",
  },
  {
    id: "log-2",
    timestamp: "09:54:05",
    level: "LEASE",
    message: "Heartbeat ping dispatched: worker-1 [capacity: 8/10, latency: 1.2ms]",
    source: "worker-1",
  },
  {
    id: "log-3",
    timestamp: "09:54:08",
    level: "INFO",
    message: "Fencing token seq-4092 assigned to workflow segment run_9918c",
    source: "orchestrator",
  },
  {
    id: "log-4",
    timestamp: "09:54:12",
    level: "HEAL",
    message: "Crash detected on worker-3 (simulated timeout) -> automatic lease handoff to worker-2 completed with 0 duplicate effects",
    source: "auto-healer",
  },
  {
    id: "log-5",
    timestamp: "09:54:15",
    level: "INFO",
    message: "Runtime thread checkpoint verified: CatmullRom spline c1-5 secured",
    source: "thread-gamma-1",
  },
];

export function TerminalConsole() {
  const [collapsed, setCollapsed] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>(DEFAULT_LOGS);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Poll or append periodic telemetry log events
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      const timeStr = now.toTimeString().split(" ")[0] ?? "09:54:20";

      const sampleEvents: LogEntry[] = [
        {
          id: `log-${Date.now()}-1`,
          timestamp: timeStr,
          level: "LEASE",
          message: `Worker lease renewed across ${Math.floor(Math.random() * 4 + 2)} active workers`,
          source: "heartbeat",
        },
        {
          id: `log-${Date.now()}-2`,
          timestamp: timeStr,
          level: "INFO",
          message: `AST step executed: step_${Math.floor(Math.random() * 50 + 1)} recorded in durable state`,
          source: "executor",
        },
        {
          id: `log-${Date.now()}-3`,
          timestamp: timeStr,
          level: "HEAL",
          message: `Zero duplicate effects verified across cluster checkpoint c-${Math.floor(Math.random() * 100 + 10)}`,
          source: "verifier",
        },
      ];

      const chosen = sampleEvents[Math.floor(Math.random() * sampleEvents.length)]!;
      setLogs((prev) => [...prev.slice(-40), chosen]);
    }, 4500);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!collapsed && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, collapsed]);

  const levelColor = (lvl: LogEntry["level"]) => {
    switch (lvl) {
      case "INFO":
        return "text-zinc-400 border-zinc-700 bg-zinc-800/40";
      case "LEASE":
        return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
      case "HEAL":
        return "text-cyan-400 border-cyan-500/30 bg-cyan-500/10";
      case "WARN":
        return "text-amber-400 border-amber-500/30 bg-amber-500/10";
      case "ERROR":
        return "text-rose-400 border-rose-500/30 bg-rose-500/10";
    }
  };

  return (
    <div className="w-full border-t border-white/[0.08] bg-black/60 backdrop-blur-2xl transition-all select-none">
      {/* Console Header Bar */}
      <div className="flex h-9 items-center justify-between px-4 border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center gap-1.5 text-xs font-mono font-bold uppercase tracking-wider text-zinc-300 hover:text-white transition-colors"
          >
            <Terminal className="h-3.5 w-3.5 text-strand-gold" />
            <span>TERMINAL</span>
            {collapsed ? (
              <ChevronUp className="h-3.5 w-3.5 text-zinc-500" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
            )}
          </button>

          <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[9px] text-emerald-400">
            <Radio className="h-2.5 w-2.5 animate-pulse" />
            LIVE TELEMETRY STREAM
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-zinc-500">
            {logs.length} events
          </span>
          <button
            type="button"
            onClick={() => setLogs([])}
            title="Clear console"
            className="rounded p-1 text-zinc-500 hover:bg-white/[0.05] hover:text-zinc-300 transition-colors"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Terminal Log Stream with Smooth Height Collapse */}
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            key="terminal-drawer"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "9rem", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            className="overflow-hidden"
          >
            <div
              ref={scrollRef}
              className="h-full overflow-y-auto p-3 font-mono text-[11px] leading-relaxed space-y-1 scrollbar-thin"
            >
              <AnimatePresence initial={false}>
                {logs.map((log) => (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                    className="flex items-start gap-2 py-0.5 hover:bg-white/[0.02] rounded px-1 -mx-1"
                  >
                    {/* Timestamp in brackets */}
                    <span className="text-zinc-500 shrink-0 select-none">
                      [{log.timestamp}]
                    </span>

                    {/* Level badge */}
                    <span
                      className={`rounded border px-1.5 py-0.2 text-[9px] font-bold uppercase shrink-0 ${levelColor(
                        log.level
                      )}`}
                    >
                      {log.level}
                    </span>

                    {/* Log message */}
                    <span className="text-zinc-300 break-all">{log.message}</span>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
