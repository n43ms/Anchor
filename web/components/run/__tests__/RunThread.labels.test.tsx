import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { RunThread } from "../RunThread";
import { fortyStepsMock } from "../mocks";

describe("RunThread — a label that will not fit is dropped, not clipped (§24.3)", () => {
  it("renders fewer <text> labels than markers once steps are dense", () => {
    const { container } = render(<RunThread segments={fortyStepsMock.segments} />);
    const markerGroups = container.querySelectorAll("g[data-marker-kind]");
    const labels = container.querySelectorAll("g[data-marker-kind] > text");
    expect(labels.length).toBeLessThan(markerGroups.length);
  });

  it("never clips a label with overflow — no clipped/truncated marker text nodes exist with ellipsis", () => {
    const { container } = render(<RunThread segments={fortyStepsMock.segments} />);
    const clipped = Array.from(container.querySelectorAll("g[data-marker-kind] > text")).filter((t) =>
      t.textContent?.endsWith("…"),
    );
    expect(clipped.length).toBe(0);
  });
});
