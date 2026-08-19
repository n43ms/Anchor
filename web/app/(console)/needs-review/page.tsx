/**
 * anchor-spec.md §13.3 — its own page, never only a filter. A failure
 * reachable only by narrowing a list is a failure that goes unnoticed.
 */
import { Link } from "react-router-dom";
import { useNeedsReview } from "@/hooks/useNeedsReview";

export default function NeedsReviewPage() {
  const { data, error } = useNeedsReview();

  return (
    <div data-testid="needs-review-page" className="space-y-4">
      <div>
        <h1 className="font-ui text-base font-bold text-ink-primary">needs review</h1>
        <p className="text-xs text-ink-secondary">
          runs halted at the uncertainty window following a worker crash during non-idempotent tool execution
        </p>
      </div>

      {error && !data && <p className="text-sm text-status-critical">could not load review queue</p>}
      {!error && !data && <p className="text-sm text-ink-muted">loading…</p>}
      {data && data.items.length === 0 && (
        <div className="rounded-lg border border-gridline bg-surface-panel p-8 text-center text-sm text-ink-muted">
          no runs currently require operator review
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((run) => (
            <Link
              key={run.id}
              to={`/needs-review/${run.id}`}
              className="block rounded-lg border border-status-warning/40 bg-surface-panel p-4 transition-all duration-base hover:border-status-warning hover:bg-surface-page"
            >
              <div className="flex items-center justify-between">
                <div className="font-data text-sm font-bold text-ink-primary">{run.display_id ?? `run_${run.id}`}</div>
                <span className="rounded bg-status-warning/15 px-2 py-0.5 text-xs text-status-warning">action required</span>
              </div>
              <div className="mt-2 flex items-center gap-4 text-xs text-ink-secondary">
                <span>agent: <strong className="text-ink-primary">{run.agent_type}</strong></span>
                <span>step: <strong className="text-ink-primary font-data">{run.current_step_index ?? "—"}</strong></span>
                <span>last owner: <strong className="text-ink-primary font-data">{run.owner_worker_id ?? "—"}</strong></span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
