/**
 * anchor-spec.md §24.5 — a Storybook-style preview: all five required mock
 * states rendered side by side, with no backend required.
 */
"use client";

import { RunDetail } from "@/components/run/RunDetail";
import {
  fortyStepsMock,
  manyHandoffsMock,
  needsReviewMock,
  orphanedMock,
  referenceMock,
  zeroHandoffsMock,
} from "@/components/run/mocks";

const NOW = new Date("2026-08-18T14:02:52.000Z");

const states = [
  { title: "reference — 1 handoff, 0 duplicates", run: referenceMock },
  { title: "zero handoffs — footer suppression", run: zeroHandoffsMock },
  { title: "three or more handoffs — beyond-three color rule", run: manyHandoffsMock },
  { title: "needs_review", run: needsReviewMock },
  { title: "40 steps — label collision", run: fortyStepsMock },
  { title: "currently orphaned — no current owner", run: orphanedMock },
];

export default function PreviewPage() {
  return (
    <main className="min-h-screen bg-surface-page p-8" data-theme="dark">
      <h1 className="mb-6 font-ui text-lg text-ink-primary">RunDetail — mock state preview</h1>
      <div className="grid gap-6">
        {states.map(({ title, run }) => (
          <section key={run.id}>
            <h2 className="mb-2 text-sm text-ink-secondary">{title}</h2>
            <RunDetail run={run} onKill={() => undefined} now={NOW} />
          </section>
        ))}
      </div>
    </main>
  );
}
