/**
 * anchor-spec.md §13.3 — one card per worker: id, uptime, current runs,
 * steps executed, last heartbeat age, code version, and a kill control.
 * Killing a worker from the interface is a first-class feature.
 */
"use client";

import { useState } from "react";
import { useWorkers } from "@/hooks/useWorkers";
import { api, ApiRequestError } from "@/lib/api";

export default function FleetPage() {
  const { workers, stale, degraded } = useWorkers();
  const [errors, setErrors] = useState<Record<string, string>>({});

  const kill = (id: string, graceful: boolean) => {
    setErrors((prev) => ({ ...prev, [id]: "" }));
    api.killWorker(id, graceful).catch((err: unknown) => {
      setErrors((prev) => ({ ...prev, [id]: err instanceof ApiRequestError ? err.message : "kill failed" }));
    });
  };

  return (
    <div data-testid="fleet-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">fleet</h1>
      {stale && <p className="mb-3 text-xs text-status-warning">stale — showing last known fleet state</p>}
      {degraded && <p className="mb-3 text-xs text-status-critical">fleet is below its expected complement</p>}
      {workers.length === 0 && <p className="text-sm text-ink-muted">no workers registered</p>}

      <div className="grid grid-cols-3 gap-4">
        {workers.map((w) => (
          <div key={w.id} className="rounded-md border border-gridline bg-surface-panel p-4" data-testid="worker-card">
            <div className="flex items-center justify-between">
              <span className="font-data text-sm font-bold text-ink-primary">{w.id}</span>
              {w.stale && <span className="text-xs text-status-warning">stale</span>}
            </div>
            <dl className="mt-2 space-y-1 text-xs text-ink-secondary">
              <Row label="uptime" value={w.uptime_ms !== undefined ? `${Math.round(w.uptime_ms / 1000)}s` : "—"} />
              <Row label="current runs" value={`${w.current_run_count}/${w.capacity}`} />
              <Row label="steps executed" value={w.steps_executed ?? "—"} />
              <Row label="heartbeat age" value={w.heartbeat_age_ms !== undefined ? `${w.heartbeat_age_ms}ms` : "—"} />
              <Row label="code version" value={w.code_version} />
            </dl>
            {errors[w.id] && <p className="mt-2 text-xs text-status-critical">{errors[w.id]}</p>}
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => kill(w.id, false)}
                className="rounded bg-status-critical/15 px-2 py-1 text-xs text-status-critical transition-colors duration-fast hover:bg-status-critical/25"
              >
                kill
              </button>
              <button
                type="button"
                onClick={() => kill(w.id, true)}
                className="rounded border border-gridline px-2 py-1 text-xs text-ink-secondary transition-colors duration-fast hover:text-ink-primary"
                title="releases the lease on the way out — a cooperative shutdown, distinct from the crash-modelling hard kill"
              >
                graceful stop
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between">
      <dt>{label}</dt>
      <dd className="figures-tabular text-ink-primary">{value}</dd>
    </div>
  );
}
