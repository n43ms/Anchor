/**
 * anchor-spec.md §13.2, §22.4 — the signature element. Segments sized by
 * duration, tool calls shape-distinct from model calls (notched leading
 * edge, not just hue), replayed steps ghosted in a way that survives
 * grayscale, worker id on every segment with a rail fallback when a
 * segment is too narrow to carry its own label.
 */
import type { FencingEvent, TimelineSegment } from "@/lib/types";
import { workerHueSlot } from "@/lib/hues";
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
  const claimOrder = segments.map((s) => s.worker_id);
  const allSteps = segments.flatMap((s) => s.steps.map((step) => ({ step, workerId: s.worker_id, segment: s })));
  const totalDuration = allSteps.reduce((sum, { step }) => sum + (step.duration_ms ?? 1000), 0) || 1;
  // No fallback to Date.now() here — render must stay pure. With no segments
  // there are no steps and nothing renders that depends on runStart anyway.
  const runStart = segments[0] ? new Date(segments[0].started_at).getTime() : 0;
  const runEnd = allSteps.reduce((latest, { step }) => {
    const end = step.completed_at ? new Date(step.completed_at).getTime() : latest;
    return Math.max(latest, end);
  }, runStart);
  const runSpan = Math.max(runEnd - runStart, 1);

  return (
    <div className="relative">
      <div className="relative flex h-10 w-full overflow-hidden rounded" data-testid="timeline-track">
        {allSteps.map(({ step, workerId, segment }, i) => {
          const widthPct = Math.max((((step.duration_ms ?? 1000) / totalDuration) * 100), (MIN_SEGMENT_WIDTH_PX / 6));
          const hueSlot = workerHueSlot(workerId, claimOrder, segment.ended_at === null);
          const isReplayed = step.status === "skipped_on_replay" || step.executed === false;
          const color = hueSlot === "muted" ? "var(--ink-muted)" : `var(--worker-${hueSlot})`;
          const isTool = step.action_kind === "tool";
          const canFitLabel = widthPct * 6.2 >= LABEL_MIN_WIDTH_PX; // rough px estimate at track scale

          return (
            <div
              key={`${workerId}-${step.step_index}`}
              className="relative flex h-full items-center justify-center text-[10px] text-white transition-opacity duration-base"
              style={{
                width: `${widthPct}%`,
                marginRight: i < allSteps.length - 1 ? GAP_PX : 0,
                backgroundColor: isReplayed ? `color-mix(in srgb, ${color} 10%, var(--surface-panel))` : color,
                opacity: isReplayed ? 0.85 : 1,
                // ghosted fill carried by weight/opacity, not hue, so it survives grayscale
                borderLeft: isReplayed ? `1px dashed color-mix(in srgb, ${color} 60%, transparent)` : undefined,
                clipPath: isTool ? "polygon(6px 0, 100% 0, 100% 100%, 0 100%, 0 6px)" : undefined,
              }}
              data-step-executed={!isReplayed}
              data-action-kind={step.action_kind}
              title={`${workerId} · ${step.name} · ${step.action_kind}${step.idempotency_key_display ? ` · ${step.idempotency_key_display}` : ""}`}
            >
              {canFitLabel && <span className="truncate px-1 font-data">{workerId}</span>}
            </div>
          );
        })}
      </div>

      {/* worker-id rail fallback: continuous rail beneath the track spanning each
          ownership range, so a label is never clipped with overflow: hidden. */}
      <div className="relative mt-1 flex h-4 w-full text-[10px] text-ink-muted">
        {segments.map((segment) => {
          const stepShare = (segment.steps.length / (allSteps.length || 1)) * 100;
          return (
            <span key={segment.worker_id} className="truncate font-data" style={{ width: `${stepShare}%` }}>
              {segment.worker_id}
            </span>
          );
        })}
      </div>

      {fencingEvents.map((event) => {
        const at = new Date(event.at).getTime();
        const xPercent = Math.min(100, Math.max(0, ((at - runStart) / runSpan) * 100));
        return <FencingMarker key={`${event.fenced_worker_id}-${event.at}`} event={event} xPercent={xPercent} />;
      })}
    </div>
  );
}
