import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RunDetail } from "../RunDetail";
import { orphanedMock } from "../mocks";

const NOW = new Date("2026-08-18T15:00:32.000Z");

describe("RunDetail — currently orphaned (no segment has ended_at === null)", () => {
  it("has no segment with ended_at === null in the fixture itself", () => {
    expect(orphanedMock.segments.some((s) => s.ended_at === null)).toBe(false);
  });

  it("renders the gap, not an error and not an empty state", () => {
    render(<RunDetail run={orphanedMock} onKill={() => {}} now={NOW} />);
    expect(screen.getByTestId("orphaned-gap")).toBeInTheDocument();
    expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
    expect(screen.getByTestId("run-detail")).toBeInTheDocument();
  });

  it("shows a lease-expiry countdown as plain text", () => {
    render(<RunDetail run={orphanedMock} onKill={() => {}} now={NOW} />);
    expect(screen.getByTestId("orphaned-gap").textContent).toMatch(/orphaned/i);
  });

  it("disables kill with a stated reason rather than targeting a stale worker", () => {
    render(<RunDetail run={orphanedMock} onKill={() => {}} now={NOW} />);
    const button = screen.getByRole("button", { name: /kill/i });
    expect(button).toBeDisabled();
    expect(button.getAttribute("title")).toMatch(/orphaned/i);
  });
});
