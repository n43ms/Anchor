import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { RunThread } from "../RunThread";
import { referenceMock } from "../mocks";

describe("RunThread — flow animation stops at terminal state (§24.3)", () => {
  it("flows while the run is in progress", () => {
    const { container } = render(<RunThread segments={referenceMock.segments} terminal={false} />);
    const path = container.querySelector(".strand-path");
    expect(path?.getAttribute("data-flowing")).toBe("true");
  });

  it("stops flowing once the run reaches a terminal state", () => {
    const { container } = render(<RunThread segments={referenceMock.segments} terminal={true} />);
    const path = container.querySelector(".strand-path");
    expect(path?.getAttribute("data-flowing")).toBe("false");
  });

  it("does not flow when animate is forced off by the parent", () => {
    const { container } = render(<RunThread segments={referenceMock.segments} terminal={false} animate={false} />);
    const path = container.querySelector(".strand-path");
    expect(path?.getAttribute("data-flowing")).toBe("false");
  });
});
