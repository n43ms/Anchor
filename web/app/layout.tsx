import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Anchor — operator console",
  description: "durable execution runtime for AI agents",
};

// dark-first per anchor-spec.md §22.1 — light mode is a selected, validated
// set (tokens.light.css exists) but is not required to ship for phases 1-8.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-surface-page text-ink-primary">{children}</body>
    </html>
  );
}
