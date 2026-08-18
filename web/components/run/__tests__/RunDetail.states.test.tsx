import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RunDetail } from "../RunDetail";
import {
  fortyStepsMock,
  manyHandoffsMock,
  needsReviewMock,
  orphanedMock,
  referenceMock,
} from "../mocks";

const NOW = new Date("2026-08-18T14:02:52.000Z");

describe("RunDetail five mock states", () => {
  it("renders zero handoffs without a recovery figure", () => {
    render(<RunDetail run={{ ...referenceMock, segments: [referenceMock.segments[0]!], summary: { duplicate_side_effects: 0, handoff_count: 0, recovery_seconds: null } }} onKill={() => {}} now={NOW} />);
    expect(screen.getByTestId("run-detail-footer").textContent).not.toContain("recovery");
  });

  it("renders three or more handoffs using the beyond-three color rule", () => {
    render(<RunDetail run={manyHandoffsMock} onKill={() => {}} now={NOW} />);
    expect(screen.getAllByTestId("handoff-divider").length).toBeGreaterThanOrEqual(3);
  });

  it("renders a needs_review run", () => {
    render(<RunDetail run={needsReviewMock} onKill={() => {}} now={NOW} />);
    expect(screen.getByText(/needs review/i)).toBeInTheDocument();
  });

  it("renders a 40-step run without throwing", () => {
    render(<RunDetail run={fortyStepsMock} onKill={() => {}} now={NOW} />);
    expect(screen.getByTestId("run-detail")).toBeInTheDocument();
  });

  it("renders the currently-orphaned state", () => {
    render(<RunDetail run={orphanedMock} onKill={() => {}} now={NOW} />);
    expect(screen.getByTestId("orphaned-gap")).toBeInTheDocument();
  });
});
