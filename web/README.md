# Anchor — Operator Console

The operator console for Anchor, built with React 19, Vite, Tailwind CSS v4, Monaco Editor, Lucide icons, and `react-router-dom`.

## Installation & Local Setup

When running outside Docker Compose, install dependencies inside the `web` directory:

```bash
cd web
npx pnpm install
# or
npm install --legacy-peer-deps
```

## Running the Operator Console

Run the Vite development server with API/WebSocket proxying to `http://localhost:8000`:

```bash
npx pnpm dev
# or
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) (or [http://localhost:5173](http://localhost:5173)) in your browser.

## Testing & Typecheck

```bash
# Run Vitest test suite
npx pnpm test

# Run TypeScript strict typecheck
npx pnpm typecheck

# Build for production
npx pnpm build
```
