import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { RunDetail } from "../RunDetail";
import { referenceMock } from "../mocks";

// now is injected — relative timestamps ("started 41s ago") would otherwise
// make this snapshot flap on every run (component-contract.md).
const NOW = new Date("2026-08-18T14:02:52.000Z");

describe("RunDetail snapshot", () => {
  it("matches the reference mock with now injected", () => {
    const { container } = render(<RunDetail run={referenceMock} onKill={() => {}} now={NOW} />);
    expect(container.querySelector('[data-testid="run-detail"]')).toMatchSnapshot();
  });
});
