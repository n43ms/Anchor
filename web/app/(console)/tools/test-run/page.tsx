/**
 * anchor-spec.md §13.3 — a one-off submission form for pre-registered
 * agents only, in every deployment mode. This page selects, it does not
 * author.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { usePolling } from "@/hooks/usePolling";
import { api, ApiRequestError } from "@/lib/api";
import type { Run } from "@/lib/types";

export default function TestRunPage() {
  const agents = usePolling(api.listAgents, 30_000);
  const [agentType, setAgentType] = useState("");
  const [isDemo, setIsDemo] = useState(true);
  const [inputJson, setInputJson] = useState("{}");
  const [submittedRun, setSubmittedRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = () => {
    setError(null);
    setSubmittedRun(null);

    let parsedInput: Record<string, unknown> = {};
    if (inputJson.trim()) {
      try {
        parsedInput = JSON.parse(inputJson) as Record<string, unknown>;
      } catch {
        setError("Input must be valid JSON");
        return;
      }
    }

    setSubmitting(true);
    api
      .submitRun({ agent_type: agentType, is_demo: isDemo, input: parsedInput })
      .then((run) => {
        setSubmittedRun(run);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiRequestError ? err.message : "submission failed");
      })
      .finally(() => {
        setSubmitting(false);
      });
  };

  return (
    <div data-testid="test-run-page" className="max-w-2xl space-y-6">
      <div>
        <h1 className="font-ui text-base font-bold text-ink-primary">test run</h1>
        <p className="text-xs text-ink-secondary">
          launch a registered agent workflow onto the durable worker fleet
        </p>
      </div>

      <div className="rounded-lg border border-gridline bg-surface-panel p-5 space-y-4">
        <div>
          <label className="block text-xs font-medium text-ink-secondary mb-1.5" htmlFor="agent-select">
            registered agent
          </label>
          <select
            id="agent-select"
            value={agentType}
            onChange={(e) => setAgentType(e.target.value)}
            className="w-full rounded border border-gridline bg-surface-page px-3 py-2 text-sm text-ink-primary focus:border-strand-gold focus:outline-none"
          >
            <option value="">select an agent…</option>
            {agents.data?.items.map((a) => (
              <option key={a.agent_type} value={a.agent_type}>
                {a.agent_type} ({a.tools_used.length} tools)
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-ink-secondary mb-1.5" htmlFor="input-json">
            input payload (JSON)
          </label>
          <textarea
            id="input-json"
            rows={4}
            value={inputJson}
            onChange={(e) => setInputJson(e.target.value)}
            placeholder="{}"
            className="w-full rounded border border-gridline bg-surface-page px-3 py-2 font-data text-xs text-ink-primary placeholder:text-ink-muted focus:border-strand-gold focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-ink-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={isDemo}
              onChange={(e) => setIsDemo(e.target.checked)}
              className="rounded border-gridline accent-strand-gold"
            />
            <span>tag as demo run (isolated for reset)</span>
          </label>
        </div>

        <div>
          <button
            type="button"
            onClick={submit}
            disabled={!agentType || submitting}
            className="rounded border border-gridline bg-surface-page px-4 py-2 text-sm font-medium text-ink-primary transition-colors duration-fast hover:border-strand-gold hover:text-strand-gold disabled:opacity-40"
          >
            {submitting ? "submitting…" : "submit run"}
          </button>
        </div>

        {error && (
          <div className="rounded-md border border-status-critical bg-status-critical/10 p-3 text-xs text-status-critical">
            {error}
          </div>
        )}

        {submittedRun && (
          <div className="rounded-md border border-status-good bg-status-good/10 p-4">
            <div className="text-xs text-status-good font-semibold">Run successfully submitted!</div>
            <div className="mt-2 flex items-center justify-between">
              <span className="font-data text-xs text-ink-primary">{submittedRun.display_id ?? `run_${submittedRun.id}`}</span>
              <Link
                to={`/runs/${submittedRun.id}`}
                className="rounded border border-status-good bg-surface-panel px-3 py-1 text-xs font-medium text-status-good hover:bg-status-good/20 transition-colors"
              >
                view run timeline →
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
