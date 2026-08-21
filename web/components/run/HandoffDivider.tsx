/**
 * anchor-spec.md §24.2 — "The Money Moment": Worker Handoff & Lease Recovery.
 * Rendered with radiant sun-gold handoff beacon icon and clear 2-3 word explanation.
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
      <div className="h-px flex-1 border-t border-dashed border-amber-500/25" />
      
      {/* Specular Handoff Glass Badge with Glowing Sun Gold Icon */}
      <div className="flex items-center gap-2 rounded-xl border border-strand-gold/40 bg-black/85 px-3.5 py-1.5 text-xs font-mono backdrop-blur-xl shadow-lg transition-all">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-strand-gold/20 text-strand-gold border border-strand-gold/40 shadow-glow-gold">
          <ArrowRightLeft className="h-3 w-3 text-strand-gold" />
        </span>
        <span className="font-bold text-strand-gold uppercase tracking-wider text-[10.5px]">
          Worker Handoff
        </span>
        <span className="text-zinc-600">·</span>
        <span className="text-rose-400 font-medium">
          {workerId} lease expired
        </span>
        {newWorkerId && (
          <>
            <span className="text-zinc-600">→</span>
            <span className="text-indigo-300 font-bold">{newWorkerId} acquired</span>
          </>
        )}
      </div>

      <div className="h-px flex-1 border-t border-dashed border-amber-500/25" />
    </div>
  );
}
