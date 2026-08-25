import type { TimelineSegment } from "../lib/types";

export type MarkerKind = "ordinary" | "side_effect" | "reconciled" | "handoff";

export interface ThreadMarker {
  key: string;
  t: number;
  kind: MarkerKind;
  label: string;
  stepNumber?: number | string;
}

export function deriveMarkers(segments: TimelineSegment[]): ThreadMarker[] {
  const totalSteps = segments.reduce((n, s) => n + s.steps.length, 0);
  if (totalSteps === 0) return [];

  const markers: ThreadMarker[] = [];
  let cursor = 0;

  segments.forEach((segment, segIndex) => {
    if (segIndex > 0) {
      markers.push({
        key: `handoff-${segment.worker_id}-${segIndex}`,
        t: cursor / totalSteps,
        kind: "handoff",
        label: "Worker Handoff",
        stepNumber: "⇄",
      });
    }

    segment.steps.forEach((step) => {
      const t = totalSteps > 1 ? cursor / (totalSteps - 1) : 0.5;
      let kind: MarkerKind = "ordinary";
      let label = step.name;

      if (step.status === "skipped_on_replay") {
        kind = "reconciled";
        label = `${step.name} (replayed)`;
      } else if (step.action_kind === "tool" && step.executed && (step.status === "done" || step.status === "active")) {
        kind = "side_effect";
      }

      markers.push({
        key: `step-${segment.worker_id}-${step.step_index}`,
        t,
        kind,
        label,
        stepNumber: step.step_index + 1,
      });
      cursor += 1;
    });
  });

  return markers;
}
