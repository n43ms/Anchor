/**
 * anchor-spec.md §13.3 — a one-off submission form for pre-registered
 * agents only, in every deployment mode. This page selects, it does not
 * author.
 */
"use client";

import { useState } from "react";
import { Link } from "react-router-dom";
import { usePolling } from "@/hooks/usePolling";
import { api, ApiRequestError } from "@/lib/api";
import type { Run } from "@/lib/types";
import { Play, CheckCircle2, AlertTriangle, ArrowUpRight } from "lucide-react";

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
    <div data-testid="test-run-page" className="max-w-2xl space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Dispatch Test Run</h1>
          <p className="text-xs text-zinc-400 font-mono">
            Launch a registered agent workflow onto the durable worker fleet
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-6 space-y-4 backdrop-blur-2xl">
        <div>
          <label className="block text-xs font-mono text-zinc-400 mb-1.5 uppercase tracking-wider" htmlFor="agent-select">
            Registered Agent
          </label>
          <select
            id="agent-select"
            value={agentType}
            onChange={(e) => setAgentType(e.target.value)}
            className="w-full rounded-xl border border-white/[0.08] bg-zinc-900 px-3.5 py-2.5 font-mono text-sm text-white focus:border-strand-gold focus:outline-none"
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
          <label className="block text-xs font-mono text-zinc-400 mb-1.5 uppercase tracking-wider" htmlFor="input-json">
            Input Payload (JSON)
          </label>
          <textarea
            id="input-json"
            rows={4}
            value={inputJson}
            onChange={(e) => setInputJson(e.target.value)}
            placeholder="{}"
            className="w-full rounded-xl border border-white/[0.08] bg-white/[0.02] px-3.5 py-2.5 font-mono text-xs text-white placeholder:text-zinc-500 focus:border-strand-gold focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs font-mono text-zinc-400 cursor-pointer">
            <input
              type="checkbox"
              checked={isDemo}
              onChange={(e) => setIsDemo(e.target.checked)}
              className="rounded border-white/[0.1] accent-strand-gold"
            />
            <span>tag as demo run (isolated for reset)</span>
          </label>
        </div>

        <div className="pt-2">
          <button
            type="button"
            onClick={submit}
            disabled={!agentType || submitting}
            className="flex items-center gap-2 rounded-xl border border-strand-gold/50 bg-strand-gold/20 px-5 py-2.5 text-sm font-mono font-bold text-strand-gold hover:bg-strand-gold/30 hover:border-strand-gold transition-all duration-base shadow-sm disabled:opacity-40"
          >
            <Play className="h-4 w-4" />
            <span>{submitting ? "dispatching…" : "Dispatch Run"}</span>
          </button>
        </div>

        {error && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs font-mono text-rose-400 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {submittedRun && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 space-y-2">
            <div className="text-xs font-mono text-emerald-400 font-bold flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" />
              <span>Run successfully submitted to worker fleet!</span>
            </div>
            <div className="flex items-center justify-between font-mono text-xs">
              <span className="text-white font-bold">{submittedRun.display_id ?? `run_${submittedRun.id}`}</span>
              <Link
                to={`/runs/${submittedRun.id}`}
                className="flex items-center gap-1 text-strand-gold hover:underline"
              >
                <span>View Timeline Track</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
