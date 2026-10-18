from __future__ import annotations

import asyncio
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.github.client import GitHubClient
from app.github.parser import parse_pull_request_url
from app.schemas.verification import (
    CreateVerificationRequest,
    ExecutionStatus,
    Finding,
    RepairRequest,
    RepairResult,
    RepairStatus,
    StageState,
    VerificationRun,
    VerificationStage,
    VerificationStatus,
)
from app.services.context_ranker import ContextRanker
from app.services.inference_budget import BudgetExceeded, InferenceBudget, current_run
from app.services.nebius import InferenceUnavailable, NebiusGateway
from app.services.repository import RepositoryService
from app.services.sandbox import DockerSandbox
from app.services.store import VerificationStore
from app.verification.differential import Classification, compare_executions


STAGES = [
    ("ingest", "Repository loaded"),
    ("analyze", "Pull request analyzed"),
    ("impact", "Impact graph generated"),
    ("hypotheses", "Risk hypotheses generated"),
    ("tests", "Adversarial tests generated"),
    ("base", "Base branch executed"),
    ("head", "Pull request branch executed"),
    ("compare", "Differential results compared"),
    ("report", "Evidence report completed"),
]

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, settings: Settings, store: VerificationStore) -> None:
        self.settings = settings
        self.store = store
        self.repository = RepositoryService(settings.max_diff_characters)
        self.ranker = ContextRanker(settings.gpu_worker_url, settings.gpu_worker_token)
        self.budget = InferenceBudget(
            settings.data_path.with_name("inference-budget.sqlite3"),
            settings.inference_budget_usd, settings.inference_run_budget_usd,
            settings.inference_max_calls_per_run,
        )
        self.nebius = NebiusGateway(
            settings.nebius_api_key, settings.nebius_base_url, settings.nebius_model, budget=self.budget
        )
        self.sandbox = DockerSandbox(
            settings.sandbox_timeout_seconds, settings.sandbox_memory, settings.sandbox_cpus
        )

    def create(self, request: CreateVerificationRequest) -> VerificationRun:
        parse_pull_request_url(request.pull_request_url)
        run = VerificationRun(
            pull_request_url=request.pull_request_url,
            stages=[VerificationStage(key=key, label=label) for key, label in STAGES],
        )
        self.store.save(run)
        return run

    def create_repair(self, run_id: str, request: RepairRequest) -> VerificationRun:
        run = self._required(run_id)
        if run.status != VerificationStatus.REGRESSION_FOUND:
            raise ValueError("A repair requires a confirmed regression")
        if not self.settings.enable_sandbox:
            raise ValueError("Repair verification requires the execution sandbox")
        if not self.settings.nebius_api_key:
            raise ValueError("Repair generation requires Nebius credentials")
        finding = self._repair_finding(run, request.finding_id)
        run.repair = RepairResult(finding_id=finding.id)
        run.status = VerificationStatus.RUNNING
        run.completed_at = None
        for key, label in (
            ("repair", "Minimal repair generated"),
            ("repair_verify", "Repair checks executed"),
        ):
            existing = next((stage for stage in run.stages if stage.key == key), None)
            if existing:
                existing.state = StageState.PENDING
                existing.detail = None
                existing.timestamp = None
            else:
                run.stages.append(VerificationStage(key=key, label=label))
        self.store.save(run)
        return run

    async def repair(self, run_id: str, request: RepairRequest) -> None:
        run = self._required(run_id)
        if not run.repair or not run.summary or not run.repository_profile:
            return
        workspace = self.settings.workspace_root / f"{run.id}-repair"
        repository = workspace / "repository.git"
        checkout = workspace / "head"
        context_token = current_run.set(run.id)
        try:
            run.repair.status = RepairStatus.RUNNING
            self._activate(run, "repair")
            finding = self._repair_finding(run, run.repair.finding_id)
            generated = next(
                test for test in run.generated_tests if test.id == finding.generated_test_id
            )
            await asyncio.to_thread(
                self.repository.clone, run.summary.clone_url, repository
            )
            await asyncio.to_thread(
                self.repository.fetch_commits,
                repository,
                run.summary.base_commit,
                run.summary.head_commit,
            )
            await asyncio.to_thread(
                self.repository.checkout, repository, run.summary.head_commit, checkout
            )
            diff = await asyncio.to_thread(
                self.repository.diff,
                repository,
                run.summary.base_commit,
                run.summary.head_commit,
            )
            source = ""
            if finding.affected_file:
                source = await asyncio.to_thread(
                    self.repository.file_content,
                    repository,
                    run.summary.head_commit,
                    finding.affected_file,
                )
            proposal = await self.nebius.create_repair(
                finding, diff, source, request.instructions
            )
            run.repair.patch = proposal.patch
            run.repair.summary = proposal.summary
            run.metrics.model_calls += 1
            allowed_paths = set(run.changed_files)
            await asyncio.to_thread(
                self.repository.apply_patch, checkout, proposal.patch, allowed_paths
            )
            self._complete(run, "repair", proposal.summary)

            self._activate(run, "repair_verify")
            run.repair.checks = await asyncio.to_thread(
                self.sandbox.verify_repair,
                checkout,
                run.summary.head_commit,
                run.repository_profile,
                generated,
            )
            verified = all(
                check.execution.status == ExecutionStatus.PASSED
                for check in run.repair.checks
                if check.name in {"existing_tests", "generated_tests"} or check.command
            ) and {
                check.name for check in run.repair.checks
                if check.execution.status == ExecutionStatus.PASSED
            }.issuperset({"existing_tests", "generated_tests"})
            if verified:
                run.status = VerificationStatus.FIX_VERIFIED
                run.repair.status = RepairStatus.VERIFIED
                detail = "All configured repair checks passed"
            else:
                run.status = VerificationStatus.REGRESSION_FOUND
                run.repair.status = RepairStatus.FAILED
                run.repair.error = "The proposed repair did not pass every required check"
                detail = "Repair was not verified"
            self._complete(run, "repair_verify", detail)
            run.completed_at = datetime.now(timezone.utc)
            self.store.save(run)
        except Exception as exc:
            logger.warning("repair failed run=%s error_type=%s", run.id, type(exc).__name__)
            run.status = VerificationStatus.REGRESSION_FOUND
            run.repair.status = RepairStatus.FAILED
            run.repair.error = self._public_error(exc)
            run.completed_at = datetime.now(timezone.utc)
            for stage in run.stages:
                if stage.state == StageState.ACTIVE:
                    stage.state = StageState.ERROR
                    stage.detail = "Repair could not complete"
            self.store.save(run)
        finally:
            try:
                self._account_usage(run)
            finally:
                current_run.reset(context_token)
                shutil.rmtree(workspace, ignore_errors=True)

    async def verify(self, run_id: str, request: CreateVerificationRequest) -> None:
        run = self._required(run_id)
        workspace = self.settings.workspace_root / run.id
        started = time.monotonic()
        github = GitHubClient(self.settings.github_token)
        context_token = current_run.set(run.id)
        try:
            run.status = VerificationStatus.RUNNING
            self._activate(run, "ingest")
            reference = parse_pull_request_url(request.pull_request_url)
            run.summary = await github.get_pull_request(reference)
            repository = workspace / "repository.git"
            await asyncio.to_thread(self.repository.clone, run.summary.clone_url, repository)
            await asyncio.to_thread(
                self.repository.fetch_commits, repository, run.summary.base_commit, run.summary.head_commit
            )
            self._complete(run, "ingest", f"{run.summary.owner}/{run.summary.repository} #{run.summary.number}")

            self._activate(run, "analyze")
            run.repository_profile = await asyncio.to_thread(
                self.repository.profile, repository, run.summary.head_commit
            )
            run.changed_files = (
                await asyncio.to_thread(
                    self.repository.changed_files,
                    repository,
                    run.summary.base_commit,
                    run.summary.head_commit,
                )
            )[: self.settings.max_changed_files]
            diff = await asyncio.to_thread(
                self.repository.diff, repository, run.summary.base_commit, run.summary.head_commit
            )
            documents = await asyncio.to_thread(
                self.repository.context_documents,
                repository,
                run.summary.head_commit,
                run.changed_files,
            )
            run.metrics.files_analyzed = len(documents)
            self._complete(run, "analyze", f"{len(run.changed_files)} files changed")

            self._activate(run, "impact")
            query = f"Potential regressions from changes to {' '.join(run.changed_files)} {request.focus or ''}"
            ranking = await self.ranker.rank(query, documents, limit=20)
            run.metrics.context_accelerator = ranking.accelerator
            run.impact_nodes, run.impact_edges = self.repository.impact_graph(
                run.changed_files, ranking.documents
            )
            self._complete(run, "impact", f"Context ranked on {ranking.accelerator.upper()}")

            self._activate(run, "hypotheses")
            plan = await self.nebius.create_plan(
                diff, run.repository_profile, ranking.documents, request.focus
            )
            run.model_used = plan.model_used
            run.hypotheses = plan.hypotheses
            run.generated_tests = plan.tests
            run.metrics.hypotheses_generated = len(plan.hypotheses)
            run.metrics.generated_tests = len(plan.tests)
            run.metrics.model_calls = 1 if self.settings.nebius_api_key else 0
            self._complete(run, "hypotheses", f"{len(plan.hypotheses)} hypotheses")
            self._activate(run, "tests")
            self._complete(run, "tests", f"{len(plan.tests)} tests")

            if not self.settings.enable_sandbox:
                run.status = VerificationStatus.ANALYSIS_ONLY
                for key in ("base", "head", "compare"):
                    self._complete(run, key, "Sandbox disabled; analysis only")
            else:
                await self._execute_plan(run, repository, workspace)

            self._activate(run, "report")
            self._complete(run, "report", "Auditable evidence stored")
            run.completed_at = datetime.now(timezone.utc)
            run.metrics.analysis_duration_ms = int((time.monotonic() - started) * 1000)
            self.store.save(run)
        except Exception as exc:
            logger.warning("verification failed run=%s error_type=%s", run.id, type(exc).__name__)
            run.status = VerificationStatus.ENVIRONMENT_ERROR
            run.error = self._public_error(exc)
            run.completed_at = datetime.now(timezone.utc)
            for stage in run.stages:
                if stage.state == StageState.ACTIVE:
                    stage.state = StageState.ERROR
                    stage.detail = "This stage could not complete"
            self.store.save(run)
        finally:
            try:
                self._account_usage(run)
            finally:
                current_run.reset(context_token)
                try:
                    await github.close()
                finally:
                    shutil.rmtree(workspace, ignore_errors=True)

    async def _execute_plan(self, run: VerificationRun, repository: Path, workspace: Path) -> None:
        assert run.summary and run.repository_profile
        executable_tests = [
            generated
            for generated in run.generated_tests
            if generated.file_path.strip() and generated.test_code.strip()
        ]
        if not executable_tests:
            run.status = VerificationStatus.ANALYSIS_ONLY
            for key in ("base", "head", "compare"):
                self._complete(run, key, "No executable generated test was available")
            return
        regression = False
        pre_existing = False
        sandbox_started = time.monotonic()
        for index, generated in enumerate(executable_tests):
            base_checkout = workspace / f"base-{index}-{generated.id}"
            head_checkout = workspace / f"head-{index}-{generated.id}"
            self._activate(run, "base")
            await asyncio.to_thread(
                self.repository.checkout, repository, run.summary.base_commit, base_checkout
            )
            base = await asyncio.to_thread(
                self.sandbox.execute,
                base_checkout,
                run.summary.base_commit,
                "base",
                run.repository_profile,
                generated,
            )
            self._complete(run, "base", base.status.value)
            self._activate(run, "head")
            await asyncio.to_thread(
                self.repository.checkout, repository, run.summary.head_commit, head_checkout
            )
            head = await asyncio.to_thread(
                self.sandbox.execute,
                head_checkout,
                run.summary.head_commit,
                "head",
                run.repository_profile,
                generated,
            )
            self._complete(run, "head", head.status.value)
            classification = compare_executions(base, head)
            hypothesis = next(item for item in run.hypotheses if item.id == generated.hypothesis_id)
            finding = Finding(
                hypothesis_id=hypothesis.id,
                generated_test_id=generated.id,
                classification=classification.value,
                severity="high" if classification == Classification.REGRESSION else "info",
                summary=hypothesis.description,
                affected_file=hypothesis.affected_files[0] if hypothesis.affected_files else None,
                base_execution=base,
                head_execution=head,
            )
            if classification == Classification.REGRESSION:
                try:
                    finding.root_cause = await self.nebius.analyze_root_cause(finding)
                    if finding.root_cause:
                        run.metrics.model_calls += 1
                except (InferenceUnavailable, BudgetExceeded) as exc:
                    finding.explanation_error = str(exc)
            run.findings.append(finding)
            regression = regression or classification == Classification.REGRESSION
            pre_existing = pre_existing or classification == Classification.PRE_EXISTING
        self._activate(run, "compare")
        run.metrics.regressions_found = sum(
            finding.classification == Classification.REGRESSION.value for finding in run.findings
        )
        run.metrics.sandbox_duration_ms = int((time.monotonic() - sandbox_started) * 1000)
        if regression:
            run.status = VerificationStatus.REGRESSION_FOUND
        elif pre_existing:
            run.status = VerificationStatus.PRE_EXISTING_FAILURE
        elif any(
            finding.classification == Classification.INCONCLUSIVE.value for finding in run.findings
        ):
            run.status = VerificationStatus.INCONCLUSIVE
        else:
            run.status = VerificationStatus.VERIFIED_WITHIN_SCOPE
        self._complete(run, "compare", run.status.value)

    @staticmethod
    def _public_error(exc: Exception) -> str:
        if isinstance(exc, (InferenceUnavailable, BudgetExceeded)):
            return str(exc)
        return "Verification could not complete; check the stage and deployment configuration"

    def _account_usage(self, run: VerificationRun) -> None:
        usage = self.budget.summary(run.id)
        run.metrics.model_calls = usage["calls"]
        run.metrics.input_tokens = usage["input_tokens"]
        run.metrics.output_tokens = usage["output_tokens"]
        run.metrics.accounted_cost_usd = usage["accounted_cost_usd"]
        run.metrics.cache_hits = usage["cache_hits"]
        self.store.save(run)

    def _required(self, run_id: str) -> VerificationRun:
        run = self.store.get(run_id)
        if not run:
            raise KeyError(run_id)
        return run

    @staticmethod
    def _repair_finding(run: VerificationRun, finding_id: str | None) -> Finding:
        candidates = [
            finding for finding in run.findings if finding.classification == Classification.REGRESSION.value
        ]
        if finding_id:
            candidates = [finding for finding in candidates if finding.id == finding_id]
        if not candidates:
            raise ValueError("A repair requires a confirmed regression finding")
        return candidates[0]

    def _activate(self, run: VerificationRun, key: str) -> None:
        stage = next(stage for stage in run.stages if stage.key == key)
        stage.state = StageState.ACTIVE
        stage.timestamp = datetime.now(timezone.utc)
        self.store.save(run)

    def _complete(self, run: VerificationRun, key: str, detail: str) -> None:
        stage = next(stage for stage in run.stages if stage.key == key)
        stage.state = StageState.COMPLETE
        stage.detail = detail
        stage.timestamp = datetime.now(timezone.utc)
        self.store.save(run)
