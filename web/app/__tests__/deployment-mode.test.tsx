import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ModeBanner } from "@/components/shell/ModeBanner";
import type { Health } from "@/lib/types";

function mockHealth(health: Health) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => health,
  } as Response);
}

describe("deployment mode is always visible (constitution → Console Surface and Deployment Modes)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows the mode banner at all times", async () => {
    mockHealth({ database_reachable: true, redis_reachable: true, worker_count: 3, deployment_mode: "demonstration" });
    render(<ModeBanner />);
    await waitFor(() => expect(screen.getByTestId("mode-banner").getAttribute("data-deployment-mode")).toBe("demonstration"));
  });

  it("states plainly when the database is unreachable, per I7", async () => {
    mockHealth({ database_reachable: false, redis_reachable: true, worker_count: 0, deployment_mode: "local" });
    render(<ModeBanner />);
    await waitFor(() => expect(screen.getByText(/database unreachable/i)).toBeInTheDocument());
  });
});
