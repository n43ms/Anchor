/**
 * anchor-spec.md §24.2 — the bar. Fill is the worker's identity hue; the
 * unfilled portion is a neutral surface step, never a lighter tint of the
 * same hue (that would read as a magnitude ramp and imply the empty portion
 * carried a value).
 */
import type { TimelineSegment } from "@/lib/types";
import { hueSlotVar, type WorkerHueSlot } from "@/lib/hues";

export function WorkerBar({ segment, hueSlot }: { segment: TimelineSegment; hueSlot: WorkerHueSlot }) {
  const total = segment.steps.length || 1;
  const doneOrActive = segment.steps.filter((s) => s.status === "done" || s.status === "active").length;
  const fraction = Math.min(doneOrActive / total, 1);
  const color = hueSlotVar(hueSlot);

  return (
    <div className="relative h-3 w-full overflow-hidden rounded-full bg-surface-page">
      <div
        className="h-full rounded-full transition-[width] duration-base ease-out"
        style={{ width: `${fraction * 100}%`, backgroundColor: color }}
        role="progressbar"
        aria-valuenow={Math.round(fraction * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
      />
    </div>
  );
}
