import React, { useState, useEffect, useRef } from "react";
import { useDemo } from "../context/DemoProvider";
import { Terminal, ChevronUp, ChevronDown, Radio } from "lucide-react";

export function TerminalConsole() {
  const [collapsed, setCollapsed] = useState(false);
  const { events } = useDemo();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!collapsed && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, collapsed]);

  return (
    <div className="w-full border-t border-white/10 bg-black/80 backdrop-blur-2xl font-mono text-xs text-zinc-100 select-none shrink-0">
      {/* Titlebar */}
      <div className="flex h-8 items-center justify-between px-3 border-b border-white/10 bg-black/60">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-zinc-300 hover:text-white transition-colors cursor-pointer"
          >
            <Terminal className="h-3.5 w-3.5 text-amber-400" />
            <span>Terminal / Audit Stream</span>
            {collapsed ? (
              <ChevronUp className="h-3.5 w-3.5 text-zinc-500" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
            )}
          </button>

          <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold text-emerald-400">
            <Radio className="h-2.5 w-2.5 animate-pulse" />
            LIVE AUDIT STREAM
          </span>
        </div>

        <span className="text-[10px] text-zinc-500 font-mono">
          {events.length} Events Streamed
        </span>
      </div>

      {/* Log Output Container */}
      {!collapsed && (
        <div
          ref={scrollRef}
          className="max-h-32 overflow-y-auto p-3 space-y-1.5 font-mono text-[10px] bg-black/90 custom-scrollbar"
        >
          {events.map((ev) => (
            <div key={ev.seq} className="flex items-center gap-2 text-zinc-300 hover:bg-white/[0.02] py-0.5 px-1 rounded">
              <span className="text-zinc-500">[{ev.created_at ? ev.created_at.substring(11, 19) : "16:35:00"}]</span>
              <span className="text-amber-400 font-bold">#run_{ev.run_id}</span>
              <span className="text-zinc-500">seq_{ev.seq}</span>
              <span
                className={`rounded px-1.5 py-0.2 text-[8px] font-bold uppercase ${
                  ev.type === "WORKER_FENCED"
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                    : ev.type.includes("FAILED")
                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                    : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                }`}
              >
                {ev.type}
              </span>
              <span className="text-zinc-400">{ev.worker_id}</span>
              <span className="text-zinc-500 truncate">{JSON.stringify(ev.payload || {})}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
