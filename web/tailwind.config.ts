import type { Config } from "tailwindcss";

/**
 * Tailwind v4 config. Utilities handle layout only — signature colors stay
 * in web/styles/tokens.{dark,light}.css as CSS custom properties (constitution
 * → Technology Stack: "Signature colors live in CSS custom properties").
 * This file maps those properties into the theme so `bg-surface-panel`,
 * `text-ink-muted`, etc. resolve to `var(--surface-panel)` rather than a
 * hardcoded hex — no component is allowed to write a color literal.
 */
const config: Config = {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "surface-page": "var(--surface-page)",
        "surface-panel": "var(--surface-panel)",
        "surface-elevated": "var(--surface-elevated)",
        "surface-highlight": "var(--surface-highlight)",
        "ink-primary": "var(--ink-primary)",
        "ink-secondary": "var(--ink-secondary)",
        "ink-muted": "var(--ink-muted)",
        gridline: "var(--gridline)",
        baseline: "var(--baseline)",
        "worker-1": "var(--worker-1)",
        "worker-2": "var(--worker-2)",
        "worker-3": "var(--worker-3)",
        "status-pending": "var(--status-pending)",
        "status-executing": "var(--status-executing)",
        "status-good": "var(--status-good)",
        "status-warning": "var(--status-warning)",
        "status-critical": "var(--status-critical)",
        "strand-gold": "var(--strand-gold)",
        "marker-ordinary": "var(--marker-ordinary)",
        "marker-side-effect": "var(--marker-side-effect)",
        "marker-reconciled": "var(--marker-reconciled)",
      },
      fontFamily: {
        ui: ["var(--font-ui)"],
        data: ["var(--font-data)"],
      },
      transitionDuration: {
        fast: "150ms",
        base: "200ms",
        emphatic: "250ms",
        smooth: "350ms",
      },
    },
  },
};

export default config;
