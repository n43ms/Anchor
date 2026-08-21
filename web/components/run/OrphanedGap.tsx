/**
 * anchor-spec.md §13.4, §22.3: "orphaned is the absence of fill, not a
 * color." No segment has ended_at === null — the run lost its worker and
 * has not yet been reclaimed.
 */
"use client";

import { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";

export function OrphanedGap({ leaseExpiresAt, now = new Date() }: { leaseExpiresAt: string | null; now?: Date }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1_000);
    return () => window.clearInterval(id);
  }, []);

  const remainingMs = leaseExpiresAt ? new Date(leaseExpiresAt).getTime() - now.getTime() - tick * 1000 : null;
  const seconds = remainingMs !== null ? Math.max(0, Math.round(remainingMs / 1000)) : null;

  return (
    <div
      className="my-3.5 flex items-center justify-center gap-2.5 rounded-2xl border border-dashed border-amber-500/30 bg-amber-500/5 py-4 backdrop-blur-xl"
      data-testid="orphaned-gap"
    >
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse shadow-glow-amber">
        <AlertCircle className="h-3 w-3 text-amber-300" />
      </span>
      <span className="font-mono text-xs font-bold text-amber-300 uppercase tracking-wider text-[10.5px]">
        Run Orphaned
      </span>
      <span className="text-zinc-600 font-mono text-xs">·</span>
      <span className="font-mono text-xs text-zinc-300">
        {seconds !== null ? `lease expiring in ${seconds}s` : "lease expired, awaiting reclaim"}
      </span>
    </div>
  );
}
