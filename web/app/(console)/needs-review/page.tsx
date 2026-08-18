/**
 * anchor-spec.md §13.3 — its own page, never only a filter. A failure
 * reachable only by narrowing a list is a failure that goes unnoticed.
 */
"use client";

import Link from "next/link";
import { useNeedsReview } from "@/hooks/useNeedsReview";

export default function NeedsReviewPage() {
  const { data, error } = useNeedsReview();

  return (
    <div data-testid="needs-review-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">needs review</h1>
      {error && !data && <p className="text-sm text-status-critical">could not load</p>}
      {!error && !data && <p className="text-sm text-ink-muted">loading…</p>}
      {data && data.items.length === 0 && <p className="text-sm text-ink-muted">nothing needs review</p>}

      <div className="space-y-2">
        {data?.items.map((run) => (
          <Link
            key={run.id}
            href={`/needs-review/${run.id}`}
            className="block rounded-md border border-gridline bg-surface-panel p-3 transition-colors duration-fast hover:border-status-warning"
          >
            <div className="font-data text-sm text-ink-primary">{run.display_id ?? `run_${run.id}`}</div>
            <div className="text-xs text-ink-secondary">{run.agent_type} · step {run.current_step_index ?? "—"}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
