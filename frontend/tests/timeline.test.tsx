import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerificationTimeline } from "../components/verification-timeline";


describe("VerificationTimeline", () => {
  it("announces completed, active, and pending stages accessibly", () => {
    render(
      <VerificationTimeline
        stages={[
          { label: "Repository loaded", state: "complete" },
          { label: "Generating adversarial tests", state: "active" },
          { label: "Executing PR branch", state: "pending" },
        ]}
      />,
    );

    expect(screen.getByText("Repository loaded")).toHaveAccessibleDescription("Complete");
    expect(screen.getByText("Generating adversarial tests")).toHaveAccessibleDescription("In progress");
    expect(screen.getByText("Executing PR branch")).toHaveAccessibleDescription("Pending");
  });
});

