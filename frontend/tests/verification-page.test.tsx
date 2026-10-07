import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "run-1" }) }));

import VerificationPage from "../app/verifications/[id]/page";


const completedRun = {
  id: "run-1",
  pull_request_url: "https://github.com/acme/store/pull/42",
  status: "REGRESSION_FOUND",
  model_used: "nvidia/nemotron",
  summary: {
    owner: "acme", repository: "store", number: 42, title: "Coupon support",
    base_commit: "a".repeat(40), head_commit: "b".repeat(40), changed_files: 1, additions: 4, deletions: 1,
  },
  stages: [{ key: "report", label: "Evidence report completed", state: "complete", detail: "Stored" }],
  findings: [{
    id: "finding-1", classification: "REGRESSION", severity: "high", summary: "Negative total",
    affected_file: "coupon.py",
    root_cause: "The changed discount branch omits the zero-floor clamp.",
    base_execution: { branch: "base", commit: "a".repeat(40), status: "PASSED", stdout: "", stderr: "", duration_ms: 4 },
    head_execution: { branch: "head", commit: "b".repeat(40), status: "FAILED", stdout: "", stderr: "", duration_ms: 5 },
  }],
  changed_files: ["coupon.py"],
  hypotheses: [{ id: "H1", description: "Negative total", test_strategy: "Oversized discount" }],
  metrics: { files_analyzed: 3, hypotheses_generated: 1, generated_tests: 1, regressions_found: 1, context_accelerator: "cuda" },
  disclaimer: "Evidence is scoped.",
};

afterEach(() => vi.unstubAllGlobals());

describe("VerificationPage", () => {
  it("renders a completed evidence report", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(completedRun), { status: 200 })));
    render(<VerificationPage />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Coupon support" })).toBeInTheDocument());
    expect(screen.getByText("CUDA")).toBeInTheDocument();
    expect(screen.getAllByText("REGRESSION").length).toBeGreaterThan(0);
    expect(screen.getByText(/omits the zero-floor clamp/i)).toBeInTheDocument();
    expect(screen.getByText("Evidence is scoped.")).toBeInTheDocument();
  });

  it("renders a bounded loading error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 404 })));
    render(<VerificationPage />);
    await waitFor(() => expect(screen.getByRole("heading", { name: /verification unavailable/i })).toBeInTheDocument());
  });

  it("renders in-progress empty evidence without claiming success", async () => {
    const running = {
      ...completedRun,
      status: "RUNNING",
      summary: null,
      findings: [],
      hypotheses: [],
      stages: [],
      error: "Sandbox is warming up",
      metrics: { ...completedRun.metrics, regressions_found: 0, context_accelerator: "cpu" },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(running), { status: 200 })));
    render(<VerificationPage />);
    await waitFor(() => expect(screen.getByRole("heading", { name: /analyzing pull request/i })).toBeInTheDocument());
    expect(screen.getByText(/findings appear after differential execution/i)).toBeInTheDocument();
    expect(screen.getByText("Sandbox is warming up")).toBeInTheDocument();
    expect(screen.getByText("CPU")).toBeInTheDocument();
  });
});
