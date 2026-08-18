/**
 * anchor-spec.md §13.4, §22.3: "orphaned is the absence of fill, not a
 * color." No segment has ended_at === null — the run lost its worker and
 * has not yet been reclaimed. This is the single most persuasive moment in
 * the product and must never be hidden, smoothed over, or rendered as an
 * error/empty state.
 */
"use client";

import { useEffect, useState } from "react";

export function OrphanedGap({ leaseExpiresAt, now = new Date() }: { leaseExpiresAt: string | null; now?: Date }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1_000);
    return () => window.clearInterval(id);
  }, []);

  const remainingMs = leaseExpiresAt ? new Date(leaseExpiresAt).getTime() - now.getTime() - tick * 1000 : null;
  const seconds = remainingMs !== null ? Math.max(0, Math.round(remainingMs / 1000)) : null;

  return (
    <div
      className="my-3 flex items-center justify-center gap-3 rounded-md border border-dashed border-gridline bg-transparent py-6"
      data-testid="orphaned-gap"
    >
      <span className="h-2 w-2 animate-pulse rounded-full border border-ink-muted" aria-hidden="true" />
      <span className="text-sm text-ink-secondary">
        orphaned — {seconds !== null ? `lease expiring in ${seconds}s` : "lease expired, awaiting reclaim"}
      </span>
    </div>
  );
}
