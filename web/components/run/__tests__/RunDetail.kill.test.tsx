import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RunDetail } from "../RunDetail";
import { referenceMock, zeroHandoffsMock } from "../mocks";

const NOW = new Date("2026-08-18T14:02:52.000Z");

describe("RunDetail kill control (§24.2)", () => {
  it("targets the segment with ended_at === null", async () => {
    const onKill = vi.fn();
    render(<RunDetail run={referenceMock} onKill={onKill} now={NOW} />);
    const button = screen.getByRole("button", { name: /kill worker-c#1/i });
    await userEvent.click(button);
    expect(onKill).toHaveBeenCalledWith("worker-c#1");
  });

  it("is disabled with a stated reason when the run is terminal", () => {
    render(<RunDetail run={zeroHandoffsMock} onKill={() => {}} now={NOW} />);
    const button = screen.getByRole("button", { name: /kill/i });
    expect(button).toBeDisabled();
    expect(button.getAttribute("title")).toMatch(/completed/i);
  });
});
