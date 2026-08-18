/**
 * anchor-spec.md §24.2 — per segment, not one block, so every line is
 * attributed to the worker that wrote it.
 */
import type { SegmentLogLine } from "@/lib/types";

const LEVEL_COLOR_VAR: Record<SegmentLogLine["level"], string> = {
  info: "var(--ink-muted)",
  success: "var(--status-good)",
  warning: "var(--status-warning)",
};

export function SegmentLog({ lines }: { lines: SegmentLogLine[] }) {
  if (lines.length === 0) return null;
  return (
    <div className="mt-1 space-y-0.5 font-data text-[11px]" data-testid="segment-log">
      {lines.map((line, i) => (
        <div key={i} style={{ color: LEVEL_COLOR_VAR[line.level] }}>
          <span className="text-ink-muted">{line.timestamp}</span> {line.text}
        </div>
      ))}
    </div>
  );
}
