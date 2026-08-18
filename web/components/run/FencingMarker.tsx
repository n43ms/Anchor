/**
 * anchor-spec.md §13.2, §22.4 — a fencing event is a full-height marker on
 * the track, showing both the stale and current epoch, never a buried log
 * line.
 */
import type { FencingEvent } from "@/lib/types";

export function FencingMarker({ event, xPercent }: { event: FencingEvent; xPercent: number }) {
  return (
    <div
      className="absolute inset-y-0 flex flex-col items-center justify-center border-l-2 border-status-critical"
      style={{ left: `${xPercent}%` }}
      title={`${event.fenced_worker_id} fenced — stale epoch ${event.stale_epoch}, current epoch ${event.current_epoch}`}
      data-testid="fencing-marker"
    >
      <span className="whitespace-nowrap rounded bg-status-critical/15 px-1.5 py-0.5 text-[10px] text-status-critical">
        fenced · epoch {event.stale_epoch} → {event.current_epoch}
      </span>
    </div>
  );
}
