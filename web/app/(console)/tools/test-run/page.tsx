/**
 * anchor-spec.md §13.3 — a one-off submission form for pre-registered
 * agents only, in every deployment mode. This page selects, it does not
 * author.
 */
"use client";

import { useState } from "react";
import { usePolling } from "@/hooks/usePolling";
import { api, ApiRequestError } from "@/lib/api";

export default function TestRunPage() {
  const agents = usePolling(api.listAgents, 30_000);
  const [agentType, setAgentType] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    setError(null);
    setResult(null);
    api
      .submitRun({ agent_type: agentType, is_demo: true })
      .then((run) => setResult(run.display_id ?? `run_${run.id}`))
      .catch((err: unknown) => setError(err instanceof ApiRequestError ? err.message : "submission failed"));
  };

  return (
    <div data-testid="test-run-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">test run</h1>

      <label className="block text-xs text-ink-secondary" htmlFor="agent-select">
        agent
      </label>
      <select
        id="agent-select"
        value={agentType}
        onChange={(e) => setAgentType(e.target.value)}
        className="mt-1 rounded border border-gridline bg-surface-panel px-2 py-1.5 text-sm text-ink-primary"
      >
        <option value="">select an agent…</option>
        {agents.data?.items.map((a) => (
          <option key={a.agent_type} value={a.agent_type}>
            {a.agent_type}
          </option>
        ))}
      </select>

      <button
        type="button"
        onClick={submit}
        disabled={!agentType}
        className="ml-3 rounded border border-gridline px-3 py-1.5 text-sm text-ink-primary transition-colors duration-fast hover:border-status-good disabled:opacity-40"
      >
        submit
      </button>

      {result && <p className="mt-3 text-sm text-status-good">submitted {result}</p>}
      {error && <p className="mt-3 text-sm text-status-critical">{error}</p>}
    </div>
  );
}
