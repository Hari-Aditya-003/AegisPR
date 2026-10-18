import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  it("keeps execution proof when explanation is unavailable and labels cost as an app estimate", async () => {
    const run = {
      ...completedRun,
      findings: [{ ...completedRun.findings[0], root_cause: null, explanation_error: "Explanation unavailable: inference spending cap reached." }],
      metrics: { ...completedRun.metrics, input_tokens: 450, output_tokens: 180, accounted_cost_usd: 0.0042, cache_hits: 1 },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(run), { status: 200 })));
    render(<VerificationPage />);
    await screen.findByRole("heading", { name: "Coupon support" });
    expect(screen.getByText("Explanation unavailable: inference spending cap reached.")).toBeInTheDocument();
    expect(screen.getByText("App cost estimate")).toBeInTheDocument();
    expect(screen.getByText("$0.0042")).toBeInTheDocument();
    expect(screen.getByText("450 / 180")).toBeInTheDocument();
    expect(screen.getByText(/not the provider balance/i)).toBeInTheDocument();
    expect(screen.getByText("Inspect branch execution evidence")).toBeInTheDocument();
  });
  it("renders a completed evidence report", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(completedRun), { status: 200 })));
    render(<VerificationPage />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Coupon support" })).toBeInTheDocument());
    expect(screen.getByText("CUDA")).toBeInTheDocument();
    expect(screen.getAllByText("REGRESSION").length).toBeGreaterThan(0);
    expect(screen.getByText(/omits the zero-floor clamp/i)).toBeInTheDocument();
    expect(screen.getByText("Evidence is scoped.")).toBeInTheDocument();
  });

  it("exposes exact branch execution evidence and does not invent existing-suite or build results", async () => {
    const run = { ...completedRun, findings: [{ ...completedRun.findings[0], head_execution: { ...completedRun.findings[0].head_execution, stdout: "AssertionError: -10 != 0", stderr: "", duration_ms: 17, environment: { command: "python -m pytest -q -- tests/test_boundary.py" } } }] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(run), { status: 200 })));
    render(<VerificationPage />);
    await screen.findByRole("heading", { name: "Coupon support" });
    fireEvent.click(screen.getByText("Inspect branch execution evidence"));
    expect(screen.getByText("AssertionError: -10 != 0")).toBeInTheDocument();
    expect(screen.getByText("17 ms")).toBeInTheDocument();
    expect(screen.getByText("python -m pytest -q -- tests/test_boundary.py")).toBeInTheDocument();
    expect(screen.getAllByText("Not recorded").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText("RECORDED")).not.toBeInTheDocument();
  });

  it("allows retry after an unavailable report", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response("", { status: 503 }))
      .mockResolvedValue(new Response(JSON.stringify(completedRun), { status: 200 })));
    render(<VerificationPage />);
    fireEvent.click(await screen.findByRole("button", { name: /retry loading evidence/i }));
    await screen.findByRole("heading", { name: "Coupon support" });
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

  it("starts repair verification for a confirmed regression", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(completedRun), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...completedRun, status: "RUNNING", repair: { finding_id: "finding-1", status: "PENDING", patch: "", summary: "", checks: [] } }), { status: 202 }))
      .mockResolvedValue(new Response(JSON.stringify({
        ...completedRun,
        status: "FIX_VERIFIED",
        repair: {
          finding_id: "finding-1",
          status: "VERIFIED",
          patch: "diff --git a/coupon.py b/coupon.py",
          summary: "Clamp the result at zero.",
          checks: [
            { name: "existing_tests", command: "pytest -q", execution: { branch: "repair", commit: "b".repeat(40), status: "PASSED", stdout: "", stderr: "", duration_ms: 8 } },
          ],
        },
      }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<VerificationPage />);
    const button = await screen.findByRole("button", { name: /generate and verify repair/i });
    fireEvent.click(button);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/verifications/run-1/repair"),
      expect.objectContaining({ method: "POST" }),
    ));
    await waitFor(() => expect(screen.getByText("Clamp the result at zero.")).toBeInTheDocument());
    expect(screen.getAllByText("FIX VERIFIED").length).toBeGreaterThan(0);
    expect(screen.getAllByText("PASSED").length).toBeGreaterThan(0);
  });
});
