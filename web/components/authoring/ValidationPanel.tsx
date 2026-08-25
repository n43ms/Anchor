/**
 * Renders a `ValidationReport` (contracts/openapi.yaml) — plan.md P9.1,
 * T589. Findings and the `unchecked` checklist are always both rendered:
 * a clean report ("0 findings") is not allowed to read as "this agent is
 * correct" on its own, so the four judgements the validator cannot make
 * are the STATED NEXT STEP, adjacent to the results, never a disclaimer
 * and never folded into "all checks passed" (D-59, FR-134).
 *
 * Handles three states explicitly: loading, empty (no report requested
 * yet), and the two content states (clean vs. findings present) —
 * component discipline per the constitution's frontend rules.
 */
import { AlertTriangle, CheckCircle2, Loader2, ListChecks } from "lucide-react";
import type { ValidationReport } from "@/lib/types";

export function ValidationPanel({
  report,
  loading,
}: {
  report: ValidationReport | null;
  loading: boolean;
}) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-4 backdrop-blur-2xl" data-testid="validation-panel">
      <div className="flex items-center justify-between">
        <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">Validation</h2>
        {loading && (
          <span className="flex items-center gap-1.5 text-xs font-mono text-zinc-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            checking…
          </span>
        )}
      </div>

      {!loading && report === null && (
        <p className="text-xs font-mono text-zinc-500">
          Nothing validated yet. Six static checks run on keystroke pause and on submission.
        </p>
      )}

      {report !== null && (
        <>
          {report.findings.length === 0 ? (
            <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2.5 text-sm text-emerald-400">
              <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>No contract violation found across the six mechanical checks.</span>
            </div>
          ) : (
            <ul className="space-y-2" data-testid="validation-findings">
              {report.findings.map((finding, i) => (
                <li
                  key={`${finding.check}-${finding.line}-${i}`}
                  className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-sm text-amber-300"
                >
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <div>
                    <div className="font-mono text-xs uppercase tracking-wider text-amber-400/80">
                      {finding.check} · line {finding.line}
                    </div>
                    <div>{finding.message}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* The stated ceiling (D-59, FR-134): these six mechanical checks
              passed or failed above; these four judgements are the human's,
              always rendered, never contingent on `valid`. */}
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3.5 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-zinc-400">
              <ListChecks className="h-3.5 w-3.5" aria-hidden="true" />
              Before registering — the validator cannot check these
            </div>
            <ul className="space-y-1 text-xs font-mono text-zinc-400">
              {report.unchecked.map((item) => (
                <li key={item} className="flex gap-2">
                  <span aria-hidden="true">□</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
