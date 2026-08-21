/**
 * Status is always icon + label + color, never a bare colored dot
 * (anchor-spec.md §22.3: completed-green vs failed-red measures CVD ΔE 4.1 —
 * far below a safe separation — so color alone cannot be trusted to carry
 * the distinction for a substantial fraction of readers).
 */
import type { RunStatus } from "@/lib/types";

const RUN_STATUS_META: Record<RunStatus, { label: string; icon: string; colorVar: string }> = {
  pending: { label: "pending", icon: "○", colorVar: "--status-pending" },
  running: { label: "running", icon: "◐", colorVar: "--status-executing" },
  completed: { label: "completed", icon: "✓", colorVar: "--status-good" },
  failed: { label: "failed", icon: "✕", colorVar: "--status-critical" },
  cancelled: { label: "cancelled", icon: "⊘", colorVar: "--status-pending" },
  needs_review: { label: "needs review", icon: "?", colorVar: "--status-warning" },
};

export function StatusPill({ status, className = "" }: { status: RunStatus; className?: string }) {
  const meta = RUN_STATUS_META[status];
  const isRunning = status === "running";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium backdrop-blur-md transition-all duration-base ${
        isRunning ? "glow-status-running ring-1 ring-status-executing/30" : ""
      } ${className}`}
      style={{
        color: `var(${meta.colorVar})`,
        borderColor: `var(${meta.colorVar})`,
        backgroundColor: `color-mix(in srgb, var(${meta.colorVar}) 12%, transparent)`,
      }}
      data-status={status}
    >
      <span aria-hidden="true" className={isRunning ? "animate-spin" : ""}>
        {meta.icon}
      </span>
      <span>{meta.label}</span>
    </span>
  );
}
