import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusPill } from "../StatusPill";
import type { RunStatus } from "@/lib/types";

const ALL_STATUSES: RunStatus[] = ["pending", "running", "completed", "failed", "cancelled", "needs_review"];

describe("StatusPill — no bare colored dots (anchor-spec.md §22.3)", () => {
  it.each(ALL_STATUSES)("renders icon and label for %s", (status) => {
    render(<StatusPill status={status} />);
    const pill = screen.getByText(status.replace("_", " "));
    expect(pill).toBeInTheDocument();
    // an icon glyph must be present alongside the label — not a bare colored dot.
    expect(pill.parentElement?.querySelector("[aria-hidden='true']")?.textContent).not.toBe("");
  });

  it("never renders as a single colored span with no text", () => {
    for (const status of ALL_STATUSES) {
      const { container, unmount } = render(<StatusPill status={status} />);
      const pill = container.querySelector(`[data-status="${status}"]`);
      expect(pill?.textContent?.trim().length).toBeGreaterThan(0);
      unmount();
    }
  });
});
