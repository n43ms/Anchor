/**
 * anchor-spec.md §13.2 — the raw event log beneath the timeline, with type,
 * worker, epoch and sequence visible. Distinct from SegmentLog, which is
 * the human-readable per-segment narration; this is the ground truth.
 */
import type { RunEvent } from "@/lib/types";

export function RawEventLog({ events }: { events: RunEvent[] }) {
  if (events.length === 0) {
    return <p className="text-xs text-ink-muted">no events yet</p>;
  }
  return (
    <table className="w-full text-left font-data text-[11px]" data-testid="raw-event-log">
      <thead>
        <tr className="text-ink-muted">
          <th className="figures-tabular pr-3">seq</th>
          <th className="pr-3">type</th>
          <th className="pr-3">worker</th>
          <th className="figures-tabular pr-3">epoch</th>
          <th>created_at</th>
        </tr>
      </thead>
      <tbody>
        {events.map((e) => (
          <tr key={e.seq}>
            <td className="figures-tabular pr-3 text-ink-secondary">{e.seq}</td>
            <td className="pr-3 text-ink-primary">{e.type}</td>
            <td className="pr-3 text-ink-secondary">{e.worker_id}</td>
            <td className="figures-tabular pr-3 text-ink-secondary">{e.epoch}</td>
            <td className="text-ink-muted">{e.created_at}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
