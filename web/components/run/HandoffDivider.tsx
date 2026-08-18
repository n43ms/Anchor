/**
 * anchor-spec.md §24.2 — "the money moment". Must never be collapsed,
 * hidden behind a toggle, or animated away.
 */
export function HandoffDivider({ workerId }: { workerId: string }) {
  return (
    <div className="relative my-3 flex items-center" data-testid="handoff-divider">
      <div className="h-px flex-1 border-t border-dashed border-status-critical/40" />
      <span className="mx-3 rounded-full bg-status-critical/15 px-3 py-1 text-xs text-status-critical">
        {workerId} lease expired
      </span>
      <div className="h-px flex-1 border-t border-dashed border-status-critical/40" />
    </div>
  );
}
