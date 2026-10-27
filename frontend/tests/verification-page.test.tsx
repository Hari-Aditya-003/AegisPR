import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  it("distinguishes executed controlled fixture evidence from live PR and model evidence", async () => {
    const fixtureRun = {
      ...completedRun,
      evidence_mode: "controlled_fixture",
      model_used: "controlled-fixture-no-model",
      summary: { ...completedRun.summary, title: "Controlled coupon fixture", number: 0 },
      generated_tests: [{ id: "fixed-1", file_path: "tests/test_boundary.py", test_code: "assert total(10, 20) == 0" }],
      repair: {
        finding_id: "finding-1", status: "VERIFIED", patch: "diff --git a/coupon.py b/coupon.py",
        summary: "Manually authored clamp repair.", checks: [],
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(fixtureRun), { status: 200 })));
    render(<VerificationPage />);

    await screen.findByRole("heading", { name: "Controlled coupon fixture" });
    const provenance = screen.getByRole("note", { name: /controlled fixture/i });
    expect(provenance).toHaveTextContent(/no model call or live github pull request analysis/i);
    expect(provenance).toHaveTextContent(/prewritten tests and hypothesis/i);
    expect(provenance).toHaveTextContent(/docker execution/i);
    expect(screen.getByRole("heading", { name: "Fixed fixture test artifacts" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Prewritten fixture hypothesis" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Manual repair evidence" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Fixture execution timeline" })).toBeInTheDocument();
    expect(screen.getByText("Fixture head revision")).toBeInTheDocument();
    expect(within(screen.getByLabelText("Verification proof card")).getByText("Fixture head tests")).toBeInTheDocument();
    expect(screen.queryByText("Generated tests")).not.toBeInTheDocument();
    expect(screen.queryByText(/PR #0/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /generate and verify repair/i })).not.toBeInTheDocument();
  });

  it("never offers a model repair for an unfinished controlled fixture", async () => {
    const fixtureRun = { ...completedRun, evidence_mode: "controlled_fixture", model_used: "controlled-fixture-no-model" };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(fixtureRun), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<VerificationPage />);
    await screen.findByRole("heading", { name: "Coupon support" });
    expect(screen.queryByRole("button", { name: /generate and verify repair/i })).not.toBeInTheDocument();
    expect(screen.getByText("Not used (controlled fixture)")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("exposes the exact manual repair check logs without inferring successful checks", async () => {
    const run = {
      ...completedRun,
      evidence_mode: "controlled_fixture", model_used: "controlled-fixture-no-model", status: "FIX_VERIFIED",
      repair: {
        finding_id: "finding-1", status: "VERIFIED", patch: "", summary: "Manual fixture patch.",
        checks: [{
          name: "existing_tests", command: "python -m pytest -q",
          execution: { branch: "repair", commit: "c".repeat(40), status: "PASSED", stdout: "3 passed in 0.03s", stderr: "fixture stderr", duration_ms: 31, exit_code: 0 },
        }],
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(run), { status: 200 })));
    render(<VerificationPage />);
    await screen.findByRole("heading", { name: "Manual repair evidence" });
    fireEvent.click(screen.getByText("Inspect repair check: existing tests"));
    expect(screen.getByText("3 passed in 0.03s")).toBeInTheDocument();
    expect(screen.getByText("fixture stderr")).toBeInTheDocument();
    expect(screen.getByText("python -m pytest -q")).toBeInTheDocument();
    expect(screen.getByText("c".repeat(40))).toBeInTheDocument();
    expect(screen.getByText("31 ms")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.queryByText("RECORDED")).not.toBeInTheDocument();
  });

  it("keeps the no-model fixture marker safe when evidence mode is absent on older records", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      ...completedRun, model_used: "controlled-fixture-no-model",
    }), { status: 200 })));
    render(<VerificationPage />);
    await screen.findByRole("heading", { name: "Coupon support" });
    expect(screen.getByRole("note", { name: /controlled fixture/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /generate and verify repair/i })).not.toBeInTheDocument();
  });

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

  it("labels output intent and mutation results as bounded advisory evidence", async () => {
    const run = {
      ...completedRun,
      status: "INCONCLUSIVE",
      findings: [{
        ...completedRun.findings[0], classification: "BEHAVIOR_CHANGE", severity: "info",
        base_execution: { ...completedRun.findings[0].base_execution, stdout: "AEGISPR_OUTPUT=0" },
        head_execution: { ...completedRun.findings[0].head_execution, status: "PASSED", stdout: "AEGISPR_OUTPUT=-10" },
        confirmation_executions: Array.from({ length: 4 }, (_, i) => ({ branch: i % 2 ? "head" : "base", status: "PASSED" })),
        intent_classification: "unintended", intent_votes: ["unintended", "unclear", "unintended"],
        intent_vote_models: ["nvidia/Nemotron-3_5-Lightning", "nvidia/nemotron-3-super-120b-a12b", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"],
        intent_reason: "The PR only describes copy changes.",
        mutation_operator: "> to >=", mutation_caught: true,
      }],
      metrics: { ...completedRun.metrics, regressions_found: 0, mutants_valid: 1, mutants_caught: 1, mutation_catch_rate: 1 },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(run), { status: 200 })));
    render(<VerificationPage />);
    await screen.findByRole("heading", { name: "Coupon support" });
    expect(screen.getByText(/Advisory intent: unintended/i)).toBeInTheDocument();
    expect(screen.getByText(/3 model votes/i)).toBeInTheDocument();
    expect(screen.getByText("nvidia/Nemotron-3_5-Lightning")).toBeInTheDocument();
    expect(screen.getByText("nvidia/nemotron-3-super-120b-a12b")).toBeInTheDocument();
    expect(screen.getByText("nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")).toBeInTheDocument();
    expect(screen.getByText(/Model agreement does not confirm the PR author.s intent/i)).toBeInTheDocument();
    expect(screen.getByText(/4 confirmation executions/i)).toBeInTheDocument();
    expect(screen.getByText(/1 of 1 valid mutants caught/i)).toBeInTheDocument();
    expect(screen.getByText(/not a confirmed regression/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /generate and verify repair/i })).not.toBeInTheDocument();
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
