import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "@/components/shell/Sidebar";

describe("Sidebar navigation (constitution → Console Surface and Deployment Modes)", () => {
  it("omits Scheduled, API keys, and Webhooks rather than rendering them empty", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.queryByText("Scheduled")).not.toBeInTheDocument();
    expect(screen.queryByText("API keys")).not.toBeInTheDocument();
    expect(screen.queryByText("Webhooks")).not.toBeInTheDocument();
  });

  it("shows the built groups", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText("All runs")).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText("Fleet")).toBeInTheDocument();
  });
});
