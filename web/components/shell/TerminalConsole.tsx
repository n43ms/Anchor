/**
 * Anchor Operator Console — Collapsible Terminal Console
 * Positioned at bottom of operator console.
 * Monospace typography with bracketed timestamps [09:54:12].
 *
 * Renders the real global event log (GET /api/events, same source as the
 * Logs page) rather than synthetic telemetry — a "LIVE TELEMETRY STREAM"
 * badge over invented log lines would misrepresent runtime state
 * (constitution Principle VIII: the console must never appear to have
 * data it does not have).
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, ChevronUp, ChevronDown, Radio, AlertTriangle } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api } from "@/lib/api";
import type { RunEvent } from "@/lib/types";

const POLL_INTERVAL_MS = 3_000;

const LEVEL_BY_EVENT_TYPE: Record<string, "INFO" | "LEASE" | "HEAL" | "WARN" | "ERROR"> = {
  RUN_SUBMITTED: "INFO",
  RUN_CLAIMED: "INFO",
  REPLAY_COMPLETED: "INFO",
  STEP_STARTED: "INFO",
  LLM_CALLED: "INFO",
  TOOL_INTENT: "INFO",
  TOOL_RESULT: "INFO",
  NONDET_RECORDED: "INFO",
  STEP_COMPLETED: "INFO",
  STEP_SKIPPED_ON_REPLAY: "HEAL",
  STEP_FAILED: "WARN",
  LEASE_RENEWED: "LEASE",
  WORKER_FENCED: "ERROR",
  RUN_COMPLETED: "INFO",
  RUN_FAILED: "ERROR",
  RUN_CANCELLED: "WARN",
  RUN_NEEDS_REVIEW: "WARN",
};

function levelColor(lvl: string): string {
  switch (lvl) {
    case "LEASE":
      return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
    case "HEAL":
      return "text-cyan-400 border-cyan-500/30 bg-cyan-500/10";
    case "WARN":
      return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    case "ERROR":
      return "text-rose-400 border-rose-500/30 bg-rose-500/10";
    default:
      return "text-zinc-400 border-zinc-700 bg-zinc-800/40";
  }
}

function describe(event: RunEvent): string {
  const parts = [`run_${event.run_id}`, `seq ${event.seq}`];
  if (event.worker_id) parts.push(event.worker_id);
  if (event.step_index !== null && event.step_index !== undefined) parts.push(`step ${event.step_index}`);
  return `${event.type} — ${parts.join(" · ")}`;
}

export function TerminalConsole() {
  const [collapsed, setCollapsed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data, stale } = usePolling(() => api.listEvents({ limit: 40 }), POLL_INTERVAL_MS, true);
  const events = data?.items ?? [];

  useEffect(() => {
    if (!collapsed && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, collapsed]);

  return (
    <div className="w-full border-t border-white/[0.08] bg-black/60 backdrop-blur-2xl transition-all select-none">
      <div className="flex h-9 items-center justify-between px-4 border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
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

          {stale ? (
            <span className="flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-mono text-[9px] text-amber-400">
              <AlertTriangle className="h-2.5 w-2.5" />
              STALE — LAST KNOWN LOG
            </span>
          ) : (
            <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[9px] text-emerald-400">
              <Radio className="h-2.5 w-2.5 animate-pulse" />
              LIVE EVENT LOG
            </span>
          )}
        </div>

        <span className="font-mono text-[10px] text-zinc-500">{events.length} events</span>
      </div>

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
              {events.length === 0 ? (
                <p className="text-zinc-500">no events recorded yet</p>
              ) : (
                events
                  .slice()
                  .reverse()
                  .map((event) => {
                    const level = LEVEL_BY_EVENT_TYPE[event.type] ?? "INFO";
                    return (
                      <div
                        key={`${event.run_id}-${event.seq}`}
                        className="flex items-start gap-2 py-0.5 hover:bg-white/[0.02] rounded px-1 -mx-1"
                      >
                        <span className="text-zinc-500 shrink-0 select-none">
                          [{new Date(event.created_at).toLocaleTimeString()}]
                        </span>
                        <span
                          className={`rounded border px-1.5 py-0.2 text-[9px] font-bold uppercase shrink-0 ${levelColor(level)}`}
                        >
                          {level}
                        </span>
                        <span className="text-zinc-300 break-all">{describe(event)}</span>
                      </div>
                    );
                  })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
