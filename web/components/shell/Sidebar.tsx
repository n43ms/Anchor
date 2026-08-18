/**
 * anchor-spec.md §13.3 — three zones: workspace switcher pinned at top,
 * seven grouped sections, a docs link pinned at the bottom. Present on
 * every page.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY } from "@/lib/navigation";
import { useHealth } from "@/hooks/useHealth";

export function Sidebar() {
  const pathname = usePathname();
  const { data: health } = useHealth();
  const groups = health?.deployment_mode === "local" ? [...NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY] : NAV_GROUPS;

  return (
    <nav className="flex w-56 shrink-0 flex-col border-r border-gridline bg-surface-panel" data-testid="sidebar">
      <div className="border-b border-gridline px-4 py-3">
        <span className="text-sm font-bold text-ink-primary">anchor</span>
        <div className="mt-0.5 text-xs text-ink-muted">default workspace</div>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <div className="px-4 py-1 text-[10px] uppercase tracking-wide text-ink-muted">{group.label}</div>
            {group.pages.map((page) => {
              const active = pathname === page.href;
              return (
                <Link
                  key={page.href}
                  href={page.href}
                  className={`block px-4 py-1.5 text-sm transition-colors duration-fast ${
                    active ? "bg-surface-page text-ink-primary" : "text-ink-secondary hover:text-ink-primary"
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
        {/* The written design document (anchor-spec.md §26.3) is permitted, not
            required, before phase 8 — constitution Principle IX. No doc is
            published yet, so this points at the repository rather than a 404. */}
        <a
          href={process.env.NEXT_PUBLIC_REPO_URL ?? "#"}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-ink-secondary transition-colors duration-fast hover:text-ink-primary"
        >
          docs
        </a>
      </div>
    </nav>
  );
}
