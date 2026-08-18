import type { TimelineSegment } from "@/lib/types";

export type MarkerKind = "ordinary" | "side_effect" | "reconciled" | "handoff";

export interface ThreadMarker {
  key: string;
  /** position along the strand, 0..1 */
  t: number;
  kind: MarkerKind;
  label: string;
}

/**
 * Derives the strand's event markers from segments. One marker per
 * completed/active step, plus a handoff marker at each segment boundary.
 * Marker *shape* is required (anchor-spec.md §24.7) — never encode this as
 * three colored circles.
 */
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
        label: "handoff",
      });
    }

    segment.steps.forEach((step) => {
      const t = cursor / totalSteps;
      let kind: MarkerKind = "ordinary";
      let label = firstWord(step.name);

      if (step.status === "skipped_on_replay") {
        kind = "reconciled";
        label = "sent once";
      } else if (step.action_kind === "tool" && step.executed && (step.status === "done" || step.status === "active")) {
        kind = "side_effect";
      }

      markers.push({ key: `step-${segment.worker_id}-${step.step_index}`, t, kind, label });
      cursor += 1;
    });
  });

  return markers;
}

function firstWord(name: string): string {
  return name.trim().split(/\s+/)[0]?.toLowerCase() ?? "";
}
