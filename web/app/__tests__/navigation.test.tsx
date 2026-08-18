import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

import { Sidebar } from "@/components/shell/Sidebar";

describe("Sidebar navigation (constitution → Console Surface and Deployment Modes)", () => {
  it("omits Scheduled, API keys, and Webhooks rather than rendering them empty", () => {
    render(<Sidebar />);
    expect(screen.queryByText("Scheduled")).not.toBeInTheDocument();
    expect(screen.queryByText("API keys")).not.toBeInTheDocument();
    expect(screen.queryByText("Webhooks")).not.toBeInTheDocument();
  });

  it("shows the built groups", () => {
    render(<Sidebar />);
    expect(screen.getByText("All runs")).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText("Fleet")).toBeInTheDocument();
  });
});
