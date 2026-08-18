/**
 * anchor-spec.md / constitution I7 — "if the database is unreachable,
 * nothing executes... degrading into unrecorded execution is never an
 * acceptable fallback." This screen states that plainly: the halt is a
 * designed behaviour, not a crash, so it must not read as one.
 */
"use client";

export default function ConsoleError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center" data-testid="console-error">
      <p className="text-sm text-status-critical">execution is halted deliberately</p>
      <p className="max-w-md text-xs text-ink-secondary">
        the database could not be reached. anchor fails closed: a side effect that cannot be recorded must not
        happen, so nothing runs until the database is reachable again. this is not a crash — it is the guarantee
        working as designed.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-2 rounded border border-gridline px-3 py-1.5 text-xs text-ink-secondary transition-colors duration-fast hover:text-ink-primary"
      >
        retry
      </button>
      {error.digest && <p className="text-[10px] text-ink-muted">ref: {error.digest}</p>}
    </div>
  );
}
