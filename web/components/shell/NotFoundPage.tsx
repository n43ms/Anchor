import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center space-y-4">
      <div className="font-data text-4xl font-bold text-ink-muted">404</div>
      <h1 className="font-ui text-lg font-bold text-ink-primary">page not found</h1>
      <p className="text-xs text-ink-secondary max-w-sm">
        The requested console route does not exist or is not available in the current deployment mode.
      </p>
      <Link
        to="/"
        className="rounded border border-gridline bg-surface-panel px-4 py-2 text-xs font-medium text-ink-primary hover:border-strand-gold hover:text-strand-gold transition-colors"
      >
        return to dashboard
      </Link>
    </div>
  );
}
