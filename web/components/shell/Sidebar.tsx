/**
 * anchor-spec.md §13.3 — three zones: workspace switcher pinned at top,
 * seven grouped sections, a docs link pinned at the bottom. Present on
 * every page.
 */
import { Link, useLocation } from "react-router-dom";
import { NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY } from "@/lib/navigation";
import { useHealth } from "@/hooks/useHealth";

export function Sidebar() {
  const location = useLocation();
  const pathname = location.pathname;
  const { data: health } = useHealth();
  const groups = health?.deployment_mode === "local" ? [...NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY] : NAV_GROUPS;

  const repoUrl =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_REPO_URL) ||
    "https://github.com/n43ms/Anchor";

  return (
    <nav className="flex w-56 shrink-0 flex-col border-r border-gridline bg-surface-panel" data-testid="sidebar">
      <div className="border-b border-gridline px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-sm font-bold text-ink-primary hover:text-strand-gold transition-colors">
          <span className="h-2 w-2 rounded-full bg-strand-gold"></span>
          <span>anchor</span>
        </Link>
        <div className="mt-0.5 text-xs text-ink-muted">operator console</div>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <div className="px-4 py-1 text-[10px] uppercase tracking-wider font-semibold text-ink-muted">{group.label}</div>
            {group.pages.map((page) => {
              const active = pathname === page.href || (page.href !== "/" && pathname.startsWith(page.href));
              return (
                <Link
                  key={page.href}
                  to={page.href}
                  className={`block px-4 py-1.5 text-sm transition-all duration-base ${
                    active
                      ? "bg-surface-page text-ink-primary font-medium border-l-2 border-strand-gold pl-[14px]"
                      : "text-ink-secondary hover:text-ink-primary hover:bg-surface-page/50"
                  }`}
                  aria-current={active ? "page" : undefined}
                >
                  {page.label}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      <div className="border-t border-gridline px-4 py-3">
        <a
          href={repoUrl}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-ink-muted transition-colors duration-fast hover:text-ink-primary flex items-center justify-between"
        >
          <span>documentation</span>
          <span className="text-[10px] font-data">↗</span>
        </a>
      </div>
    </nav>
  );
}
