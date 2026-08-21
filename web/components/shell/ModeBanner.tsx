/**
 * Present at all times (constitution → Console Surface and Deployment
 * Modes). Also the one place staleness of the health read itself is worth
 * saying out loud, since every capability gate downstream depends on it.
 */
"use client";

import { useHealth } from "@/hooks/useHealth";

export function ModeBanner() {
  const { data, stale } = useHealth();

  if (!data) {
    return (
      <div
        className="flex items-center justify-between border-b border-white/[0.06] bg-black/40 px-4 py-1 text-xs font-mono text-zinc-500 backdrop-blur-md"
        data-testid="mode-banner"
      >
        <span>connecting to the api…</span>
      </div>
    );
  }

  const modeLabel =
    data.deployment_mode === "demonstration"
      ? "demonstration mode"
      : "local mode";

  return (
    <div
      className="flex items-center justify-between border-b border-white/[0.06] bg-black/30 px-4 py-1 text-xs font-mono backdrop-blur-md"
      data-testid="mode-banner"
      data-deployment-mode={data.deployment_mode}
    >
      <div className="flex items-center gap-2">
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            data.database_reachable
              ? "bg-emerald-400 animate-pulse shadow-glow-emerald"
              : "bg-rose-400 shadow-glow-rose"
          }`}
        />
        <span className="text-zinc-400 uppercase tracking-wider text-[11px]">
          {modeLabel}
        </span>
      </div>

      <div className="flex items-center gap-3">
        {!data.database_reachable && (
          <span className="rounded bg-rose-500/15 px-2 py-0.5 text-rose-400 font-semibold border border-rose-500/30">
            database unreachable — execution halted
          </span>
        )}
        {stale && (
          <span className="rounded bg-amber-500/15 px-2 py-0.5 text-amber-400 font-medium border border-amber-500/30">
            stale — last health check failed
          </span>
        )}
        {data.database_reachable && !stale && (
          <span className="text-[11px] text-zinc-500">
            fleet: <strong className="text-zinc-300 font-mono">{data.worker_count}</strong> worker{data.worker_count === 1 ? "" : "s"}
          </span>
        )}
      </div>
    </div>
  );
}
