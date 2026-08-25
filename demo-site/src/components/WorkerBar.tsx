import React from "react";
import type { TimelineSegment } from "../lib/types";

export function WorkerBar({ segment }: { segment: TimelineSegment }) {
  const total = segment.steps.length || 1;
  const doneOrActive = segment.steps.filter((s) => s.status === "done" || s.status === "active").length;
  const fraction = Math.min(doneOrActive / total, 1);

  return (
    <div className="relative h-2.5 w-full overflow-hidden rounded-full border border-indigo-500/25 bg-black/70 p-[1px] shadow-inner my-1.5">
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
