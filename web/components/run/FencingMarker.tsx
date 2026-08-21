/**
 * anchor-spec.md §13.2, §22.4 — Mellow, Refined Fencing Event Collision Marker.
 * Clean, understated badge with subtle hairline tick to indicate fencing
 * without visual noise or alarming glare.
 */
import type { FencingEvent } from "@/lib/types";

export function FencingMarker({ event, xPercent }: { event: FencingEvent; xPercent: number }) {
  return (
    <div
      className="group absolute top-0 -translate-x-1/2 z-20 flex flex-col items-center pointer-events-auto select-none"
      style={{ left: `${Math.max(6, Math.min(94, xPercent))}%` }}
      title={`${event.fenced_worker_id} fenced — stale epoch ${event.stale_epoch}, current epoch ${event.current_epoch}`}
      data-testid="fencing-marker"
    >
      {/* Subtle Mellow Pill Badge */}
      <div className="flex items-center gap-1.5 whitespace-nowrap rounded-md border border-rose-500/20 bg-black/80 px-2 py-0.5 text-[9px] font-mono text-zinc-300 backdrop-blur-md shadow-sm transition-opacity hover:opacity-100 opacity-90">
        <span className="h-1 w-1 rounded-full bg-rose-400/80" />
        <span className="font-semibold text-rose-300/90">fenced</span>
        <span className="text-zinc-500">·</span>
        <span className="text-zinc-400">{event.fenced_worker_id}</span>
        <span className="text-zinc-600">·</span>
        <span className="text-zinc-400">e{event.stale_epoch}→{event.current_epoch}</span>
      </div>

      {/* Understated Hairline Tick */}
      <div className="h-1.5 w-px bg-rose-400/30" />
    </div>
  );
}
