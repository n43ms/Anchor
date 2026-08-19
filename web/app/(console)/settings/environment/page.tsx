/**
 * anchor-spec.md §13.3 — live-editable settings. Absent in demonstration
 * mode, not present-and-disabled (constitution §31, FR-064) — an
 * availability restriction, not a security one.
 */
import { useState } from "react";
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
    return (
      <div data-testid="environment-page" className="space-y-4">
        <h1 className="font-ui text-base font-bold text-ink-primary">environment</h1>
        <div className="rounded-lg border border-gridline bg-surface-panel p-6 text-sm text-ink-muted">
          Environment configuration is unavailable in demonstration mode (FR-064).
        </div>
      </div>
    );
  }

  if (!config.data) {
    return (
      <div data-testid="environment-page">
        <p className="text-sm text-ink-muted">loading environment configuration…</p>
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
    <div data-testid="environment-page" className="max-w-2xl space-y-6">
      <div>
        <h1 className="font-ui text-base font-bold text-ink-primary">environment</h1>
        <p className="text-xs text-ink-secondary">
          live runtime configuration parameters (profile: <strong className="text-ink-primary">{config.data.active_profile}</strong>)
        </p>
      </div>

      <div className="rounded-lg border border-gridline bg-surface-panel p-5 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {Object.entries(values).map(([key, value]) => (
            <label key={key} className="block text-xs text-ink-secondary">
              <span className="font-data text-ink-primary">{key}</span>
              <input
                type="number"
                value={value}
                onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                className="mt-1 block w-full rounded border border-gridline bg-surface-page px-3 py-1.5 font-data text-xs text-ink-primary focus:border-strand-gold focus:outline-none"
              />
            </label>
          ))}
        </div>

        <div>
          <button
            type="button"
            onClick={save}
            className="rounded border border-gridline bg-surface-page px-4 py-2 text-sm font-medium text-ink-primary transition-colors duration-fast hover:border-status-good hover:text-status-good"
          >
            save changes
          </button>
        </div>

        {error && (
          <div className="rounded-md border border-status-critical bg-status-critical/10 p-3 text-xs text-status-critical" data-testid="environment-save-error">
            {error}
          </div>
        )}

        {saved && (
          <div className="rounded-md border border-status-good bg-status-good/10 p-3 text-xs text-status-good">
            Runtime configuration updated successfully.
          </div>
        )}
      </div>
    </div>
  );
}
