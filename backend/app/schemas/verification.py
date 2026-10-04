from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFIED_WITHIN_SCOPE = "VERIFIED_WITHIN_SCOPE"
    REGRESSION_FOUND = "REGRESSION_FOUND"
    FIX_VERIFIED = "FIX_VERIFIED"
    PRE_EXISTING_FAILURE = "PRE_EXISTING_FAILURE"
    INCONCLUSIVE = "INCONCLUSIVE"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    ANALYSIS_ONLY = "ANALYSIS_ONLY"


class ExecutionStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    SKIPPED = "SKIPPED"


class StageState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"


class VerificationStage(BaseModel):
    key: str
    label: str
    state: StageState = StageState.PENDING
    detail: str | None = None
    timestamp: datetime | None = None


class PullRequestSummary(BaseModel):
    owner: str
    repository: str
    number: int
    title: str = ""
    html_url: str
    clone_url: str
    base_ref: str = ""
    head_ref: str = ""
    base_commit: str = ""
    head_commit: str = ""
    changed_files: int = 0
    additions: int = 0
    deletions: int = 0


class RepositoryProfile(BaseModel):
    languages: list[str] = Field(default_factory=list)
    framework: str | None = None
    package_manager: str | None = None
    test_framework: str | None = None
    install_command: str | None = None
    test_command: str | None = None
    build_command: str | None = None
    lint_command: str | None = None
    important_files: list[str] = Field(default_factory=list)


class ImpactNode(BaseModel):
    id: str
    label: str
    kind: str = "file"
    changed: bool = False
    reason: str = ""


class ImpactEdge(BaseModel):
    source: str
    target: str
    reason: str = "dependency"


class Hypothesis(BaseModel):
    id: str
    description: str
    risk_type: str = "business_logic"
    affected_files: list[str] = Field(default_factory=list)
    test_strategy: str
    testable: bool = True


class GeneratedTest(BaseModel):
    id: str
    hypothesis_id: str
    file_path: str
    framework: str
    test_code: str
    test_command: str | None = None


class TestExecution(BaseModel):
    branch: str
    commit: str
    status: ExecutionStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    environment: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    hypothesis_id: str
    generated_test_id: str
    classification: str
    severity: str = "medium"
    summary: str
    affected_file: str | None = None
    affected_line: int | None = None
    root_cause: str | None = None
    base_execution: TestExecution
    head_execution: TestExecution


class VerificationMetrics(BaseModel):
    files_analyzed: int = 0
    hypotheses_generated: int = 0
    generated_tests: int = 0
    regressions_found: int = 0
    model_calls: int = 0
    context_accelerator: str = "cpu"
    analysis_duration_ms: int = 0
    sandbox_duration_ms: int = 0


class VerificationRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    pull_request_url: str
    status: VerificationStatus = VerificationStatus.QUEUED
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    model_used: str | None = None
    summary: PullRequestSummary | None = None
    repository_profile: RepositoryProfile | None = None
    stages: list[VerificationStage] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    impact_nodes: list[ImpactNode] = Field(default_factory=list)
    impact_edges: list[ImpactEdge] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    generated_tests: list[GeneratedTest] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    metrics: VerificationMetrics = Field(default_factory=VerificationMetrics)
    error: str | None = None
    disclaimer: str = (
        "A successful AegisPR verification does not prove that software contains no defects or "
        "security vulnerabilities. It reports evidence from the analyses and tests executed in this run."
    )


class CreateVerificationRequest(BaseModel):
    pull_request_url: str
    focus: str | None = Field(default=None, max_length=500)
    test_command: str | None = Field(default=None, max_length=300)


class RepairRequest(BaseModel):
    instructions: str | None = Field(default=None, max_length=1000)


TestExecution.__test__ = False
