import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { RunThread } from "../RunThread";
import { manyHandoffsMock } from "../mocks";

describe("RunThread — one gold along the whole length (§24.7, §24.8)", () => {
  it("uses a single strand color regardless of how many segments/handoffs exist", () => {
    const { container } = render(<RunThread segments={manyHandoffsMock.segments} />);
    const path = container.querySelector(".strand-path");
    expect(path?.getAttribute("stroke")).toBe("var(--strand-gold)");
    // no per-segment stroke override anywhere on the path itself
    expect(container.querySelectorAll(".strand-path").length).toBe(1);
  });

  it("marks handoffs by an enlarged marker, not a shade change", () => {
    const { container } = render(<RunThread segments={manyHandoffsMock.segments} />);
    const handoffMarkers = container.querySelectorAll('[data-marker-kind="handoff"]');
    expect(handoffMarkers.length).toBe(manyHandoffsMock.segments.length - 1);
  });
});
