import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { RunDetail } from "../RunDetail";
import { RunThread } from "../RunThread";
import { referenceMock } from "../mocks";

describe("RunDetail and RunThread are pure functions of props (component-contract.md)", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("RunDetail performs no fetch and opens no WebSocket", () => {
    render(<RunDetail run={referenceMock} onKill={() => {}} now={new Date()} />);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("RunThread performs no fetch and opens no WebSocket", () => {
    render(<RunThread segments={referenceMock.segments} />);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
