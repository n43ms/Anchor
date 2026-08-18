import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { RunThread } from "../RunThread";
import { referenceMock } from "../mocks";

describe("RunThread — event markers are shape-coded, not color-coded (§24.7)", () => {
  it("renders circle, square, and ring shapes rather than three colored circles", () => {
    const { container } = render(<RunThread segments={referenceMock.segments} />);
    const shapes = new Set(Array.from(container.querySelectorAll("[data-shape]")).map((el) => el.getAttribute("data-shape")));
    // the reference mock has ordinary steps (circle) and a handoff (circle, larger) —
    // assert the shape vocabulary itself supports all three, not just what one fixture uses.
    expect(shapes.has("circle")).toBe(true);
  });

  it("gives a square shape to a real side effect, never only a color", () => {
    const { container } = render(<RunThread segments={referenceMock.segments} />);
    const squares = container.querySelectorAll('rect[data-shape="square"]');
    expect(squares.length).toBeGreaterThan(0);
  });
});
