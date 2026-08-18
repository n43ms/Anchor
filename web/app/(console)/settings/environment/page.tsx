/**
 * anchor-spec.md §13.3 — live-editable settings. Absent in demonstration
 * mode, not present-and-disabled (constitution §31, FR-064) — an
 * availability restriction, not a security one.
 */
"use client";

import { useState } from "react";
import { notFound } from "next/navigation";
import { useHealth } from "@/hooks/useHealth";
import { usePolling } from "@/hooks/usePolling";
import { api, ApiRequestError } from "@/lib/api";

export default function EnvironmentPage() {
  const { data: health } = useHealth();
  const config = usePolling(api.getRuntimeConfig, 15_000);
  // Local edits overlay the polled values rather than being synced via an
  // effect, so an in-flight edit is never clobbered by the next poll tick.
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  if (health && health.deployment_mode === "demonstration") {
    notFound();
  }

  if (!config.data) return <p className="text-sm text-ink-muted">loading…</p>;

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
    <div data-testid="environment-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">environment</h1>
      <p className="mb-4 text-xs text-ink-secondary">active profile: {config.data.active_profile}</p>

      <div className="grid grid-cols-2 gap-3">
        {Object.entries(values).map(([key, value]) => (
          <label key={key} className="text-xs text-ink-secondary">
            {key}
            <input
              type="number"
              value={value}
              onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
              className="mt-1 block w-full rounded border border-gridline bg-surface-panel px-2 py-1.5 text-sm text-ink-primary"
            />
          </label>
        ))}
      </div>

      <button
        type="button"
        onClick={save}
        className="mt-4 rounded border border-gridline px-3 py-1.5 text-sm text-ink-primary transition-colors duration-fast hover:border-status-good"
      >
        save
      </button>

      {error && (
        <p className="mt-3 text-sm text-status-critical" data-testid="environment-save-error">
          {error}
        </p>
      )}
      {saved && <p className="mt-3 text-sm text-status-good">saved</p>}
    </div>
  );
}
