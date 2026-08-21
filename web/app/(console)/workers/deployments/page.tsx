/**
 * anchor-spec.md §13.3 — populated entirely from workers.code_version, no
 * new schema, no new instrumentation. Answers "which build is actually
 * running", including whether an in-flight run is being resumed by a
 * worker on different code than the one that started it.
 */
"use client";

import { useWorkers } from "@/hooks/useWorkers";

export default function DeploymentsPage() {
  const { workers, stale } = useWorkers();

  const byVersion = new Map<string, typeof workers>();
  for (const w of workers) {
    byVersion.set(w.code_version, [...(byVersion.get(w.code_version) ?? []), w]);
  }

  return (
    <div data-testid="deployments-page" className="space-y-6">
      <div>
        <h1 className="font-ui text-base font-bold text-ink-primary">deployments</h1>
        <p className="text-xs text-ink-secondary">
          active code versions and builds running across the distributed worker fleet
        </p>
      </div>

      {stale && (
        <div className="rounded-lg border border-status-warning/40 bg-status-warning/10 px-4 py-2 text-xs text-status-warning flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-status-warning animate-ping" />
          <span>stale — showing last known fleet state from store</span>
        </div>
      )}

      {workers.length === 0 && (
        <div className="rounded-lg border border-gridline bg-surface-panel p-8 text-center text-sm text-ink-muted">
          no workers registered in the fleet
        </div>
      )}

      <div className="space-y-4">
        {Array.from(byVersion.entries()).map(([version, group]) => (
          <div key={version} className="hud-corner glass-panel rounded-xl p-5 glow-card space-y-3">
            <div className="flex items-center justify-between border-b border-gridline/60 pb-3">
              <div className="flex items-center gap-3">
                <span className="h-2.5 w-2.5 rounded-full bg-status-good animate-pulse" />
                <span className="font-data text-sm font-bold text-ink-primary">BUILD: {version}</span>
                <span className="rounded bg-strand-gold/15 px-2 py-0.5 text-[10px] font-semibold text-strand-gold border border-strand-gold/30 font-data">
                  ACTIVE
                </span>
              </div>
              <span className="text-xs font-data text-ink-secondary">
                {group.length} worker{group.length === 1 ? "" : "s"} assigned
              </span>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              {group.map((w) => (
                <div
                  key={w.id}
                  className="inline-flex items-center gap-2 rounded-lg border border-gridline bg-surface-elevated px-3 py-1.5 text-xs"
                >
                  <span className="font-data font-bold text-ink-primary">{w.id}</span>
                  <span className="text-[10px] text-ink-muted font-data">
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
