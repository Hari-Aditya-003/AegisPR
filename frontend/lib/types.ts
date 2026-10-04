export type StageState = "pending" | "active" | "complete" | "error";

export interface VerificationStage {
  key: string;
  label: string;
  state: StageState;
  detail?: string;
}

export interface TestExecution {
  branch: "base" | "head";
  commit: string;
  status: string;
  stdout: string;
  stderr: string;
  duration_ms: number;
}

export interface Finding {
  id: string;
  classification: string;
  severity: string;
  summary: string;
  affected_file?: string;
  root_cause?: string;
  base_execution: TestExecution;
  head_execution: TestExecution;
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
  changed_files: string[];
  hypotheses: Array<{ id: string; description: string; test_strategy: string }>;
  metrics: {
    files_analyzed: number;
    hypotheses_generated: number;
    generated_tests: number;
    regressions_found: number;
    context_accelerator: string;
  };
  error?: string;
  disclaimer: string;
}

