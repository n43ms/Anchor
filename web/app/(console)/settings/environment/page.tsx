/**
 * anchor-spec.md §13.3 — live-editable settings. Absent in demonstration
 * mode, not present-and-disabled (constitution §31, FR-064) — an
 * availability restriction, not a security one.
 */
"use client";

import { useState } from "react";
import { useHealth } from "@/hooks/useHealth";
import { usePolling } from "@/hooks/usePolling";
import { api, ApiRequestError } from "@/lib/api";
import { Save, AlertTriangle, CheckCircle2, RefreshCw, ShieldCheck, Clock, Zap, Cpu } from "lucide-react";

interface SettingMetadata {
  label: string;
  category: "lease" | "execution" | "concurrency";
  unit: string;
  description: string;
  type?: "number" | "select";
  options?: string[];
}

const SETTINGS_META: Record<string, SettingMetadata> = {
  // Lease & Renewal
  lease_duration_ms: {
    label: "Lease Duration",
    category: "lease",
    unit: "ms",
    description: "Max duration a worker holds a run without renewal (>= 4x renewal interval).",
  },
  renewal_interval_ms: {
    label: "Renewal Interval",
    category: "lease",
    unit: "ms",
    description: "Frequency of background lease renewal ticks.",
  },
  margin_ms: {
    label: "Lease Margin",
    category: "lease",
    unit: "ms",
    description: "Delta added to now() on renewal (lease_duration_ms - renewal_interval_ms).",
  },
  reclaim_poll_interval_ms: {
    label: "Reclaim Poll Interval",
    category: "lease",
    unit: "ms",
    description: "Sleep time between claim attempts when PostgreSQL queue is empty.",
  },
  renewal_latency_warn_pct: {
    label: "Renewal Warning Latency",
    category: "lease",
    unit: "ratio",
    description: "Fraction of lease duration above which renewal is flagged as slow (0.0 to 1.0).",
  },
  lease_renewed_emit_policy: {
    label: "Renewal Logging Policy",
    category: "lease",
    unit: "policy",
    description: "When LEASE_RENEWED events are logged to run_events.",
    type: "select",
    options: ["boundaries_and_slow", "always"],
  },

  // Execution & Retry
  step_timeout_ms: {
    label: "Step Timeout",
    category: "execution",
    unit: "ms",
    description: "Hard wall-clock timeout for a single tool or model step.",
  },
  max_attempts_per_step: {
    label: "Max Step Attempts",
    category: "execution",
    unit: "attempts",
    description: "Retry count ceiling per step before dead-lettering to failed.",
  },
  backoff_base_ms: {
    label: "Backoff Base Delay",
    category: "execution",
    unit: "ms",
    description: "Initial retry delay before exponential scaling.",
  },
  backoff_factor: {
    label: "Backoff Factor",
    category: "execution",
    unit: "multiplier",
    description: "Exponential multiplier per retry attempt.",
  },
  backoff_jitter_pct: {
    label: "Backoff Jitter",
    category: "execution",
    unit: "ratio",
    description: "Random jitter fraction (e.g. 0.25 = ±25%) added to backoff.",
  },
  backoff_cap_ms: {
    label: "Backoff Cap",
    category: "execution",
    unit: "ms",
    description: "Maximum delay ceiling for retry backoff.",
  },

  // Concurrency & Payload
  per_worker_concurrency: {
    label: "Per-Worker Concurrency",
    category: "concurrency",
    unit: "runs",
    description: "Max active in-memory runs per worker process (range: 1 to 26+).",
  },

  global_concurrency_cap: {
    label: "Global Concurrency Cap",
    category: "concurrency",
    unit: "runs",
    description: "Fleet-wide limit on total active running runs in PostgreSQL.",
  },
  max_event_payload_bytes: {
    label: "Max Payload Size",
    category: "concurrency",
    unit: "bytes",
    description: "Payload size ceiling per event (default: 1 MB).",
  },
};

export default function EnvironmentPage() {
  const { data: health } = useHealth();
  const config = usePolling(api.getRuntimeConfig, 15_000);
  const [overrides, setOverrides] = useState<Record<string, string | number>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  if (health && health.deployment_mode === "demonstration") {
    return (
      <div data-testid="environment-page" className="space-y-4 pb-12">
        <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Environment Configuration</h1>
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-6 text-sm font-mono text-zinc-400 backdrop-blur-2xl">
          Environment configuration is unavailable in demonstration mode (FR-064).
        </div>
      </div>
    );
  }

  if (!config.data) {
    return (
      <div data-testid="environment-page" className="p-8 text-center">
        <p className="text-sm font-mono text-zinc-500">loading environment configuration…</p>
      </div>
    );
  }

  const values: Record<string, string | number> = {
    ...(config.data.values as unknown as Record<string, string | number>),
    ...overrides,
  };

  const leaseMs = Number(values.lease_duration_ms || 0);
  const renewalMs = Number(values.renewal_interval_ms || 0);
  const isRatioValid = leaseMs >= 4 * renewalMs;
  const autoMargin = leaseMs - renewalMs;

  const save = () => {
    setError(null);
    setSaved(false);

    // Cast numeric types properly before sending to API
    const payload: Record<string, string | number> = {};
    for (const [k, v] of Object.entries(values)) {
      if (SETTINGS_META[k]) {
        payload[k] = SETTINGS_META[k]?.type === "select" ? String(v) : Number(v);
      }
    }

    api
      .updateRuntimeConfig(payload)
      .then(() => {
        setSaved(true);
        setOverrides({});
      })
      .catch((err: unknown) =>
        setError(err instanceof ApiRequestError ? err.message : "save failed")
      );
  };

  const resetOverrides = () => {
    setOverrides({});
    setError(null);
    setSaved(false);
  };

  const categories = [
    {
      id: "lease",
      title: "Lease & Renewal Engine",
      icon: Clock,
      description: "Distributed locking and fault-detection timing",
    },
    {
      id: "execution",
      title: "Step Execution & Retry Backoff",
      icon: Zap,
      description: "Step timeouts, exponential backoff, and attempt caps",
    },
    {
      id: "concurrency",
      title: "Concurrency & Payload Ceilings",
      icon: Cpu,
      description: "Per-worker capacity, fleet caps, and payload safety limits",
    },
  ];

  return (
    <div data-testid="environment-page" className="max-w-4xl space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Environment Configuration</h1>
            <span className="rounded-full border border-strand-gold/40 bg-strand-gold/10 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-strand-gold">
              v{config.data.version}
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Active Profile: <strong className="text-strand-gold">{config.data.active_profile}</strong> • Editable:{" "}
            <strong className={config.data.editable ? "text-emerald-400" : "text-amber-400"}>
              {config.data.editable ? "Yes (Local)" : "No (Demonstration)"}
            </strong>
          </p>
        </div>

        {/* Live Ratio Integrity Indicator */}
        <div
          className={`flex items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-mono backdrop-blur-md ${
            isRatioValid
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-amber-500/30 bg-amber-500/10 text-amber-300"
          }`}
        >
          <ShieldCheck className="h-4 w-4 shrink-0" />
          <span>{isRatioValid ? "Timing Ratio Valid (Lease ≥ 4x Renewal)" : "Warning: Lease should be ≥ 4x Renewal"}</span>
        </div>
      </div>

      {/* Live Worker Fleet Summary Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-4 backdrop-blur-2xl font-mono text-xs">
        <div className="flex items-center gap-3 p-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
            <Cpu className="h-4 w-4" />
          </div>
          <div>
            <div className="text-[10px] uppercase text-zinc-500 font-bold">Active Workers Connected</div>
            <div className="text-sm font-bold text-white mt-0.5">
              {health?.worker_count ?? 0} <span className="text-[10px] text-zinc-400 font-normal">processes</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 p-2 border-t sm:border-t-0 sm:border-l border-white/[0.06]">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-strand-gold/30 bg-strand-gold/10 text-strand-gold">
            <Zap className="h-4 w-4" />
          </div>
          <div>
            <div className="text-[10px] uppercase text-zinc-500 font-bold">Per-Worker Capacity</div>
            <div className="text-sm font-bold text-white mt-0.5">
              {values.per_worker_concurrency ?? 5} <span className="text-[10px] text-zinc-400 font-normal">runs / worker</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 p-2 border-t sm:border-t-0 sm:border-l border-white/[0.06]">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-400">
            <Clock className="h-4 w-4" />
          </div>
          <div>
            <div className="text-[10px] uppercase text-zinc-500 font-bold">Fleet Total Capacity</div>
            <div className="text-sm font-bold text-white mt-0.5">
              {(health?.worker_count ?? 0) * Number(values.per_worker_concurrency ?? 5)}{" "}
              <span className="text-[10px] text-zinc-400 font-normal">(Cap: {values.global_concurrency_cap})</span>
            </div>
          </div>
        </div>
      </div>


      {/* Categorized Settings Cards */}
      <div className="space-y-6">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const catEntries = Object.entries(SETTINGS_META).filter(([_, meta]) => meta.category === cat.id);

          return (
            <div key={cat.id} className="rounded-2xl border border-white/[0.08] bg-black/40 p-6 space-y-4 backdrop-blur-2xl">
              <div className="flex items-center gap-2.5 pb-2 border-b border-white/[0.06]">
                <Icon className="h-4 w-4 text-strand-gold" />
                <div>
                  <h2 className="font-ui text-sm font-bold uppercase tracking-wider text-white">{cat.title}</h2>
                  <p className="text-[11px] text-zinc-500 font-mono">{cat.description}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {catEntries.map(([key, meta]) => (
                  <div key={key} className="rounded-xl border border-white/[0.04] bg-white/[0.01] p-3.5 space-y-1.5 hover:border-white/[0.1] transition-all">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-semibold text-zinc-200">{meta.label}</span>
                      <span className="font-mono text-[10px] font-bold text-zinc-500 uppercase px-1.5 py-0.5 rounded bg-white/[0.05]">
                        {meta.unit}
                      </span>
                    </div>

                    {meta.type === "select" ? (
                      <select
                        value={String(values[key])}
                        onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: e.target.value }))}
                        className="w-full rounded-lg border border-white/[0.08] bg-black/60 px-3 py-1.5 font-mono text-xs text-white focus:border-strand-gold focus:outline-none"
                      >
                        {meta.options?.map((opt) => (
                          <option key={opt} value={opt} className="bg-zinc-900 text-white">
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="number"
                        value={values[key]}
                        onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                        className="w-full rounded-lg border border-white/[0.08] bg-black/60 px-3 py-1.5 font-mono text-xs text-white focus:border-strand-gold focus:outline-none transition-all"
                      />
                    )}

                    <p className="text-[10px] text-zinc-400 font-mono leading-tight">{meta.description}</p>
                    {key === "step_timeout_ms" && (
                      <div className="space-y-1.5 pt-1">
                        <div className="flex items-center gap-1.5 font-mono text-[10px]">
                          <span className="text-zinc-500 font-semibold">Presets:</span>
                          <button
                            type="button"
                            onClick={() => setOverrides((prev) => ({ ...prev, step_timeout_ms: 60000 }))}
                            className="rounded px-1.5 py-0.5 border border-white/[0.1] bg-white/[0.05] hover:bg-white/[0.1] text-zinc-300 transition-all"
                          >
                            1m
                          </button>
                          <button
                            type="button"
                            onClick={() => setOverrides((prev) => ({ ...prev, step_timeout_ms: 300000 }))}
                            className="rounded px-1.5 py-0.5 border border-white/[0.1] bg-white/[0.05] hover:bg-white/[0.1] text-zinc-300 transition-all"
                          >
                            5m
                          </button>
                          <button
                            type="button"
                            onClick={() => setOverrides((prev) => ({ ...prev, step_timeout_ms: 600000 }))}
                            className="rounded px-1.5 py-0.5 border border-strand-gold/40 bg-strand-gold/10 hover:bg-strand-gold/20 text-strand-gold font-bold transition-all"
                          >
                            10m (Default)
                          </button>
                          <button
                            type="button"
                            onClick={() => setOverrides((prev) => ({ ...prev, step_timeout_ms: 1800000 }))}
                            className="rounded px-1.5 py-0.5 border border-white/[0.1] bg-white/[0.05] hover:bg-white/[0.1] text-zinc-300 transition-all"
                          >
                            30m
                          </button>
                        </div>
                        <p className="text-[10px] text-strand-gold/80 font-mono">
                          Duration: {(Number(values[key]) / 60000).toFixed(1)} minutes ({(Number(values[key]) / 1000).toFixed(0)} seconds)
                        </p>
                      </div>
                    )}
                    {key === "margin_ms" && (
                      <p className="text-[10px] text-strand-gold/80 font-mono">
                        Suggested Margin: {autoMargin} ms (Lease - Renewal)
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Footer */}
      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-3 backdrop-blur-2xl">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={save}
              className="flex items-center gap-2 rounded-xl border border-strand-gold/50 bg-strand-gold/20 px-5 py-2.5 text-sm font-mono font-bold text-strand-gold hover:bg-strand-gold/30 hover:border-strand-gold transition-all duration-base shadow-sm"
            >
              <Save className="h-4 w-4" />
              <span>Save Cluster Settings</span>
            </button>

            {Object.keys(overrides).length > 0 && (
              <button
                type="button"
                onClick={resetOverrides}
                className="flex items-center gap-1.5 rounded-xl border border-white/[0.1] bg-white/[0.04] px-4 py-2.5 text-xs font-mono text-zinc-300 hover:bg-white/[0.08] transition-all"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Reset Unsaved</span>
              </button>
            )}
          </div>

          {Object.keys(overrides).length > 0 && (
            <span className="text-xs font-mono text-amber-400">
              {Object.keys(overrides).length} setting{Object.keys(overrides).length > 1 ? "s" : ""} modified
            </span>
          )}
        </div>

        {error && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs font-mono text-rose-400 flex items-center gap-2" data-testid="environment-save-error">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {saved && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs font-mono text-emerald-400 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>Runtime configuration updated across fleet successfully.</span>
          </div>
        )}
      </div>
    </div>
  );
}

