/**
 * anchor-spec.md §13.2, §22.4 — Execution Timeline Track.
 * Rendered with sleek solid 20% opacity Deep Indigo blocks
 * matching the model call & WorkerBar ambiance with zero visual clutter.
 */
import type { FencingEvent, TimelineSegment } from "@/lib/types";
import { FencingMarker } from "./FencingMarker";

const GAP_PX = 2;
const MIN_SEGMENT_WIDTH_PX = 8;
/** below this width the worker-id label cannot fit on the segment itself. */
const LABEL_MIN_WIDTH_PX = 48;

export function TimelineTrack({
  segments,
  fencingEvents = [],
}: {
  segments: TimelineSegment[];
  fencingEvents?: FencingEvent[];
}) {
  const allSteps = segments.flatMap((s) => s.steps.map((step) => ({ step, workerId: s.worker_id, segment: s })));
  const totalDuration = allSteps.reduce((sum, { step }) => sum + (step.duration_ms ?? 1000), 0) || 1;
  const runStart = segments[0] ? new Date(segments[0].started_at).getTime() : 0;
  const runEnd = allSteps.reduce((latest, { step }) => {
    const end = step.completed_at ? new Date(step.completed_at).getTime() : latest;
    return Math.max(latest, end);
  }, runStart);
  const runSpan = Math.max(runEnd - runStart, 1);

  const hasFencing = fencingEvents.length > 0;

  return (
    <div className={`relative space-y-1.5 ${hasFencing ? "pt-7" : ""}`}>
      {/* Precision Floating Fencing Markers above track */}
      {fencingEvents.map((event) => {
        const at = new Date(event.at).getTime();
        const xPercent = Math.min(100, Math.max(0, ((at - runStart) / runSpan) * 100));
        return <FencingMarker key={`${event.fenced_worker_id}-${event.at}`} event={event} xPercent={xPercent} />;
      })}

      {/* Main Execution Blocks Container */}
      <div
        className="relative flex h-10 w-full overflow-hidden rounded-xl border border-indigo-500/20 bg-black/70 p-1 backdrop-blur-xl shadow-inner"
        data-testid="timeline-track"
      >
        {/* Crisp Dividers for Fencing Collisions */}
        {fencingEvents.map((event) => {
          const at = new Date(event.at).getTime();
          const xPercent = Math.min(100, Math.max(0, ((at - runStart) / runSpan) * 100));
          return (
            <div
              key={`laser-${event.fenced_worker_id}-${event.at}`}
              className="absolute inset-y-1 w-[2px] bg-rose-500/75 shadow-md z-10 pointer-events-none rounded-full"
              style={{ left: `${xPercent}%` }}
            />
          );
        })}

        {allSteps.map(({ step, workerId }, i) => {
          const widthPct = Math.max((((step.duration_ms ?? 1000) / totalDuration) * 100), (MIN_SEGMENT_WIDTH_PX / 6));
          const isReplayed = step.status === "skipped_on_replay" || step.executed === false;
          const isTool = step.action_kind === "tool";
          const canFitLabel = widthPct * 6.2 >= LABEL_MIN_WIDTH_PX;

          return (
            <div
              key={`${workerId}-${step.step_index}`}
              className="relative flex h-full items-center justify-center rounded-md border border-indigo-400/25 bg-indigo-500/20 text-[10px] font-mono font-bold text-indigo-100 transition-all duration-200 shadow-sm"
              style={{
                width: `${widthPct}%`,
                marginRight: i < allSteps.length - 1 ? GAP_PX : 0,
                opacity: isReplayed ? 0.45 : 1,
                borderLeft: isReplayed ? "1px dashed var(--baseline)" : undefined,
                clipPath: isTool ? "polygon(6px 0, 100% 0, 100% 100%, 0 100%, 0 6px)" : undefined,
              }}
              data-step-executed={!isReplayed}
              data-action-kind={step.action_kind}
              title={`${workerId} · ${step.name} · ${step.action_kind}${step.idempotency_key_display ? ` · ${step.idempotency_key_display}` : ""}`}
            >
              {canFitLabel && (
                <span className="truncate px-1.5 font-mono text-[10px] text-indigo-200 drop-shadow-sm">
                  {workerId}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Worker ID Rail Fallback with Glowing Indigo Ambiance */}
      <div className="relative flex h-4 w-full items-center px-1 font-mono text-[10px] text-indigo-300/80">
        {segments.map((segment) => {
          const stepShare = (segment.steps.length / (allSteps.length || 1)) * 100;
          return (
            <span
              key={segment.worker_id}
              className="truncate font-bold tracking-wider text-indigo-300 drop-shadow-md"
              style={{ width: `${stepShare}%` }}
            >
              {segment.worker_id}
            </span>
          );
        })}
      </div>
    </div>
  );
}
