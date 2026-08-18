/**
 * Canonical page inventory — constitution → "Console Surface and Deployment
 * Modes", anchor-spec.md §13.3/§30. Scheduled, API keys, and Webhooks are
 * NOT listed: they are conditional pages that must not ship as empty
 * shells (constitution Principle IX), so they are simply absent from the
 * sidebar rather than present-and-disabled.
 */
export interface NavPage {
  label: string;
  href: string;
}

export interface NavGroup {
  label: string;
  pages: NavPage[];
}

export const NAV_GROUPS: NavGroup[] = [
  { label: "Overview", pages: [{ label: "Dashboard", href: "/" }] },
  {
    label: "Runs",
    pages: [
      { label: "All runs", href: "/runs" },
      { label: "Needs review", href: "/needs-review" },
    ],
  },
  {
    label: "Workers",
    pages: [
      { label: "Fleet", href: "/workers" },
      { label: "Deployments", href: "/workers/deployments" },
    ],
  },
  // Chaos (Console, History) is omitted here deliberately: tasks.md builds it in
  // phase 8 (T521-T523), after this phase. Linking to it now would point the
  // sidebar at routes that don't exist yet. Add it back in the same shape when
  // phase 8 lands — do not build stub pages for it here.
  {
    label: "Tools",
    pages: [
      { label: "Registry", href: "/tools" },
      { label: "Test run", href: "/tools/test-run" },
    ],
  },
  {
    label: "Observability",
    pages: [
      { label: "Metrics", href: "/metrics" },
      { label: "Logs", href: "/logs" },
    ],
  },
];

/** Environment is availability-gated to local mode only — absent in
 * demonstration mode, not present-and-disabled (constitution §31, FR-064). */
export const SETTINGS_GROUP_LOCAL_ONLY: NavGroup = {
  label: "Settings",
  pages: [{ label: "Environment", href: "/settings/environment" }],
};
