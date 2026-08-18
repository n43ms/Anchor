import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RunDetail } from "../RunDetail";
import { referenceMock, zeroHandoffsMock } from "../mocks";

const NOW = new Date("2026-08-18T14:02:52.000Z");

describe("RunDetail footer (§24.2)", () => {
  it("suppresses recovery_seconds entirely at zero handoffs, not as 0.0s", () => {
    render(<RunDetail run={zeroHandoffsMock} onKill={() => {}} now={NOW} />);
    const footer = screen.getByTestId("run-detail-footer").textContent ?? "";
    expect(footer).not.toContain("0.0s recovery");
    expect(footer).not.toMatch(/recovery/);
  });

  it("leads the footer line with the duplicate side-effect count", () => {
    render(<RunDetail run={referenceMock} onKill={() => {}} now={NOW} />);
    const footer = screen.getByTestId("run-detail-footer").textContent ?? "";
    expect(footer.trim().startsWith("0 duplicate side effects")).toBe(true);
  });

  it("renders the recovery figure when handoff_count > 0", () => {
    render(<RunDetail run={referenceMock} onKill={() => {}} now={NOW} />);
    expect(screen.getByTestId("run-detail-footer").textContent).toContain("3.1s recovery");
  });
});
