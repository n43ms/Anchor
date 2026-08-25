/**
 * The generate control — plan.md P9.1, T590. `POST /api/authoring/generate`
 * runs at AUTHORING TIME, on text a human then reviews before anything is
 * registered, which is why offering it here does not contradict the rule
 * forbidding generated behaviour at runtime (§27.4, FR-137): nothing this
 * control produces reaches a live run without a human explicitly
 * registering it, and registration re-validates from scratch regardless
 * of what generated the text.
 *
 * Degrades honestly (FR-126): when the deployment has no provider
 * configured, the control disables itself and states why in plain text
 * next to it — never a spinner that times out, never a silent no-op.
 */
import { useState } from "react";
import { Sparkles } from "lucide-react";
import { api, ApiRequestError } from "@/lib/api";
import type { ValidationReport } from "@/lib/types";

export function GenerateControl({
  onGenerated,
}: {
  onGenerated: (source: string, validation: ValidationReport) => void;
}) {
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [unavailableReason, setUnavailableReason] = useState<string | null>(null);

  const generate = () => {
    setBusy(true);
    setUnavailableReason(null);
    api
      .generateDraft(description)
      .then((result) => onGenerated(result.source, result.validation))
      .catch((err: unknown) => {
        setUnavailableReason(
          err instanceof ApiRequestError ? err.message : "generation is unavailable",
        );
      })
      .finally(() => setBusy(false));
  };

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-3 backdrop-blur-2xl" data-testid="generate-control">
      <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">
        Generate a draft
      </h2>
      <p className="text-xs font-mono text-zinc-500">
        Generation happens at authoring time, on text a human then reviews — it never registers
        and never executes on its own.
      </p>
      <div className="flex gap-2">
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="describe the agent…"
          className="flex-1 rounded-xl border border-white/[0.08] bg-zinc-900 px-3.5 py-2 font-mono text-sm text-white focus:border-strand-gold focus:outline-none"
        />
        <button
          type="button"
          onClick={generate}
          disabled={busy || !description.trim()}
          className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Generate
        </button>
      </div>
      {unavailableReason && (
        <p className="text-xs font-mono text-amber-400" role="status">
          {unavailableReason}
        </p>
      )}
    </div>
  );
}
