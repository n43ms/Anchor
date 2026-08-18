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
    <div data-testid="deployments-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">deployments</h1>
      {stale && <p className="mb-3 text-xs text-status-warning">stale — showing last known fleet state</p>}
      {workers.length === 0 && <p className="text-sm text-ink-muted">no workers registered</p>}

      <div className="space-y-3">
        {Array.from(byVersion.entries()).map(([version, group]) => (
          <div key={version} className="rounded-md border border-gridline bg-surface-panel p-3">
            <div className="font-data text-sm text-ink-primary">{version}</div>
            <div className="mt-1 text-xs text-ink-secondary">
              {group.length} worker{group.length === 1 ? "" : "s"} · {group.map((w) => w.id).join(", ")}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
