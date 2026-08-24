/**
 * anchor-spec.md §24.2 — Worker Segment Progress Bar.
 * Styled with 75% opaque Deep Indigo & Glowing Blue Ambiance matching the timeline track.
 */
import type { TimelineSegment } from "@/lib/types";
import type { WorkerHueSlot } from "@/lib/hues";

export function WorkerBar({
  segment,
}: {
  segment: TimelineSegment;
  hueSlot?: WorkerHueSlot;
}) {
  const total = segment.steps.length || 1;
  const doneOrActive = segment.steps.filter((s) => s.status === "done" || s.status === "active").length;
  const fraction = Math.min(doneOrActive / total, 1);

  return (
    <div className="relative h-2.5 w-full overflow-hidden rounded-full border border-indigo-500/25 bg-black/70 p-[1px] shadow-inner">
      <div
        className="h-full rounded-full bg-gradient-to-r from-indigo-600 via-indigo-500 to-blue-400 opacity-[0.75] transition-[width] duration-300 ease-out shadow-md"
        style={{ width: `${Math.max(fraction * 100, 2)}%` }}
        role="progressbar"
        aria-valuenow={Math.round(fraction * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
      />
    </div>
  );
}
