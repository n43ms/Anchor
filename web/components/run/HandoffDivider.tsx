/**
 * anchor-spec.md §24.2 — "The Money Moment": Worker Handoff & Lease Recovery.
 * Rendered with dark reassuring green swap beacon icon and clear explanation.
 */
import { ArrowRightLeft } from "lucide-react";

export function HandoffDivider({
  workerId,
  newWorkerId,
}: {
  workerId: string;
  newWorkerId?: string;
}) {
  return (
    <div className="relative my-3.5 flex items-center justify-center gap-3" data-testid="handoff-divider">
      <div className="h-px flex-1 border-t border-dashed border-emerald-500/25" />
      
      {/* Specular Reassuring Green Handoff Glass Badge */}
      <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-black/85 px-3.5 py-1.5 text-xs font-mono backdrop-blur-xl shadow-[0_0_12px_rgba(16,185,129,0.15)] transition-all">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.35)]">
          <ArrowRightLeft className="h-3 w-3 text-emerald-300" />
        </span>
        <span className="font-bold text-emerald-400 uppercase tracking-wider text-[10.5px]">
          Worker Handoff
        </span>
        <span className="text-zinc-600">·</span>
        <span className="text-zinc-400 font-medium">
          {workerId} lease expired
        </span>
        {newWorkerId && (
          <>
            <span className="text-zinc-600">→</span>
            <span className="text-emerald-300 font-bold">{newWorkerId} acquired</span>
          </>
        )}
      </div>

      <div className="h-px flex-1 border-t border-dashed border-emerald-500/25" />
    </div>
  );
}
