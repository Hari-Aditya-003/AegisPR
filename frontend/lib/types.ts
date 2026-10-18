export type StageState = "pending" | "active" | "complete" | "error";

export interface VerificationStage {
  key: string;
  label: string;
  state: StageState;
  detail?: string;
}

export interface TestExecution {
  branch: "base" | "head" | "repair";
  commit: string;
  status: string;
  stdout: string;
  stderr: string;
  duration_ms: number;
  exit_code?: number | null;
  environment?: { command?: string; [key: string]: unknown };
}

export interface Finding {
  id: string;
  generated_test_id?: string;
  classification: string;
  severity: string;
  summary: string;
  affected_file?: string;
  root_cause?: string;
  explanation_error?: string | null;
  base_execution: TestExecution;
  head_execution: TestExecution;
}

export interface RepairCheck {
  name: string;
  command?: string;
  execution: TestExecution;
}

export interface RepairResult {
  finding_id: string;
  status: "PENDING" | "RUNNING" | "VERIFIED" | "FAILED";
  patch: string;
  summary: string;
  checks: RepairCheck[];
  error?: string;
}

export interface VerificationRun {
  id: string;
  pull_request_url: string;
  status: string;
  model_used?: string;
  summary?: {
    owner: string;
    repository: string;
    number: number;
    title: string;
    base_commit: string;
    head_commit: string;
    changed_files: number;
    additions: number;
    deletions: number;
  };
  stages: VerificationStage[];
  findings: Finding[];
  generated_tests?: Array<{ id: string; file_path: string; test_code: string; test_command?: string | null }>;
  repair?: RepairResult;
  changed_files: string[];
  hypotheses: Array<{ id: string; description: string; test_strategy: string }>;
  metrics: {
    files_analyzed: number;
    hypotheses_generated: number;
    generated_tests: number;
    regressions_found: number;
    context_accelerator: string;
    input_tokens?: number;
    output_tokens?: number;
    accounted_cost_usd?: number;
    cache_hits?: number;
  };
  error?: string;
  disclaimer: string;
}

