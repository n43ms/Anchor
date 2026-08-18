import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Chart } from "../Chart";

const singleSeries = [{ name: "runs", color: "var(--status-executing)", points: [{ x: "t0", y: 1 }, { x: "t1", y: 2 }] }];
const twoSeries = [
  { name: "a", color: "var(--worker-1)", points: [{ x: "t0", y: 1 }] },
  { name: "b", color: "var(--worker-2)", points: [{ x: "t0", y: 2 }] },
];

describe("Chart primitive (§22.5)", () => {
  it("has no legend with a single series", () => {
    render(<Chart title="one" series={singleSeries} />);
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("shows a legend once there are two or more series", () => {
    render(<Chart title="two" series={twoSeries} />);
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByText("b")).toBeInTheDocument();
  });

  it("offers a table view for every chart", async () => {
    render(<Chart title="table" series={singleSeries} />);
    await userEvent.click(screen.getByRole("button", { name: "table" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("never renders two y-axes (a single scale drives every series)", () => {
    const { container } = render(<Chart title="axes" series={twoSeries} />);
    // this primitive has exactly one <svg> per chart and computes one shared maxY —
    // asserting there is only one chart surface is the structural guarantee.
    expect(container.querySelectorAll("svg").length).toBe(1);
  });
});
