import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProofCard } from "../components/proof-card";


describe("ProofCard", () => {
  it("renders bounded verification language and evidence counts", () => {
    render(
      <ProofCard
        commit="71be309"
        status="VERIFIED_WITHIN_SCOPE"
        existingTests={{ passed: 56, total: 56 }}
        generatedTests={{ passed: 12, total: 12 }}
        regressions={0}
        buildStatus="PASS"
      />,
    );

    expect(screen.getByText("VERIFIED WITHIN TESTED SCOPE")).toBeInTheDocument();
    expect(screen.queryByText(/100% safe/i)).not.toBeInTheDocument();
    expect(screen.getByText("56/56")).toBeInTheDocument();
    expect(screen.getByText("12/12")).toBeInTheDocument();
  });

  it("renders a safe fallback for unknown and pending values", () => {
    const { rerender } = render(
      <ProofCard commit="" status="QUEUED" existingTests={{ passed: 0, total: 0 }} generatedTests={{ passed: 0, total: 0 }} regressions={0} buildStatus="PENDING" />,
    );
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("QUEUED")).toBeInTheDocument();

    rerender(
      <ProofCard commit="abcdef123" status="CUSTOM_STATUS" existingTests={{ passed: 0, total: 0 }} generatedTests={{ passed: 0, total: 0 }} regressions={0} buildStatus="RECORDED" />,
    );
    expect(screen.getByText("CUSTOM STATUS")).toBeInTheDocument();
  });
});
