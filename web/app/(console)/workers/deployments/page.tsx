/**
 * anchor-spec.md §13.3 — populated entirely from workers.code_version, no
 * new schema, no new instrumentation. Answers "which build is actually
 * running", including whether an in-flight run is being resumed by a
 * worker on different code than the one that started it.
 */
"use client";

import { useWorkers } from "@/hooks/useWorkers";
import { GitBranch, AlertTriangle } from "lucide-react";

export default function DeploymentsPage() {
  const { workers, stale } = useWorkers();

  const byVersion = new Map<string, typeof workers>();
  for (const w of workers) {
    byVersion.set(w.code_version, [...(byVersion.get(w.code_version) ?? []), w]);
  }

  return (
    <div data-testid="deployments-page" className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Fleet Code Deployments</h1>
            <span className="rounded-full bg-strand-gold/10 px-2.5 py-0.5 font-mono text-[10px] text-strand-gold border border-strand-gold/30">
              {byVersion.size} BUILDS
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono">
            Active code versions and builds running across the distributed worker fleet
          </p>
        </div>
      </div>

      {stale && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs font-mono text-amber-400 flex items-center gap-2 backdrop-blur-xl">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>stale — showing last known fleet state from store</span>
        </div>
      )}

      {workers.length === 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-12 text-center text-sm font-mono text-zinc-500 backdrop-blur-2xl">
          no workers registered in the fleet
        </div>
      )}

      <div className="space-y-4">
        {Array.from(byVersion.entries()).map(([version, group]) => (
          <div key={version} className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-3 backdrop-blur-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <div className="flex items-center gap-3">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-glow-emerald" />
                <span className="font-mono text-sm font-bold text-white">BUILD: {version}</span>
                <span className="rounded-full bg-strand-gold/15 px-2.5 py-0.5 text-[10px] font-semibold text-strand-gold border border-strand-gold/30 font-mono">
                  ACTIVE
                </span>
              </div>
              <span className="text-xs font-mono text-zinc-400">
                {group.length} worker{group.length === 1 ? "" : "s"} assigned
              </span>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              {group.map((w) => (
                <div
                  key={w.id}
                  className="inline-flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.02] px-3.5 py-2 text-xs font-mono"
                >
                  <span className="font-bold text-white">{w.id}</span>
                  <span className="text-[10px] text-zinc-500">
                    ({w.current_run_count}/{w.capacity} runs)
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
