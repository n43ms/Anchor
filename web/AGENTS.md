# Anchor Console — Agent Rules

- **Framework**: React 19 + Vite + `react-router-dom` + Tailwind CSS v4.
- **Pure Client Architecture**: `web/` is a pure client observability console. Data fetching is performed via `web/lib/api.ts` and hooks in `web/hooks/`.
- **Tokenized Design**: No hardcoded color literals (`#...` or `rgba(...)`) are allowed in component files. Use CSS custom properties from `web/styles/tokens.dark.css` and `tokens.light.css`.
- **Motion & Accessibility**: Always respect `prefers-reduced-motion`. No bare colored dots for status — always include label and icon.
