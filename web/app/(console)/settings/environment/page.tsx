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
import { Save, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function EnvironmentPage() {
  const { data: health } = useHealth();
  const config = usePolling(api.getRuntimeConfig, 15_000);
  // Local edits overlay the polled values rather than being synced via an
  // effect, so an in-flight edit is never clobbered by the next poll tick.
  const [overrides, setOverrides] = useState<Record<string, number>>({});
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

  const values: Record<string, number> = { ...(config.data.values as unknown as Record<string, number>), ...overrides };

  const save = () => {
    setError(null);
    setSaved(false);
    api
      .updateRuntimeConfig(values)
      .then(() => setSaved(true))
      .catch((err: unknown) => setError(err instanceof ApiRequestError ? err.message : "save failed"));
  };

  return (
    <div data-testid="environment-page" className="max-w-2xl space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Environment Configuration</h1>
          <p className="text-xs text-zinc-400 font-mono">
            Live runtime configuration parameters (profile: <strong className="text-strand-gold">{config.data.active_profile}</strong>)
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-6 space-y-5 backdrop-blur-2xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {Object.entries(values).map(([key, value]) => (
            <label key={key} className="block text-xs font-mono text-zinc-400">
              <span className="text-zinc-300 font-semibold">{key}</span>
              <input
                type="number"
                value={value}
                onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                className="mt-1.5 block w-full rounded-xl border border-white/[0.08] bg-white/[0.02] px-3.5 py-2 font-mono text-xs text-white focus:border-strand-gold focus:outline-none transition-all"
              />
            </label>
          ))}
        </div>

        <div className="pt-2">
          <button
            type="button"
            onClick={save}
            className="flex items-center gap-2 rounded-xl border border-strand-gold/50 bg-strand-gold/20 px-5 py-2.5 text-sm font-mono font-bold text-strand-gold hover:bg-strand-gold/30 hover:border-strand-gold transition-all duration-base shadow-sm"
          >
            <Save className="h-4 w-4" />
            <span>Save Changes</span>
          </button>
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
            <span>Runtime configuration updated successfully.</span>
          </div>
        )}
      </div>
    </div>
  );
}
