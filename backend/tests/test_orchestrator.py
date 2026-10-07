from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents import orchestrator as orchestrator_module
from app.agents.orchestrator import Orchestrator
from app.config import Settings
from app.schemas.verification import (
    CreateVerificationRequest, ExecutionStatus, GeneratedTest, Hypothesis, PullRequestSummary,
    RepositoryProfile, TestExecution, VerificationStatus,
)
from app.services.context_ranker import ContextDocument, ContextRanking
from app.services.nebius import VerificationPlan
from app.services.store import VerificationStore


def summary() -> PullRequestSummary:
    return PullRequestSummary(
        owner="acme", repository="store", number=42, title="Coupon",
        html_url="https://github.com/acme/store/pull/42", clone_url="https://github.com/acme/store.git",
        base_commit="a" * 40, head_commit="b" * 40,
    )


def execution(branch: str, status: ExecutionStatus) -> TestExecution:
    return TestExecution(branch=branch, commit=("a" if branch == "base" else "b") * 40, status=status)


@pytest.mark.asyncio
async def test_analysis_only_workflow_persists_all_reasoning_stages(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work",
        enable_sandbox=False, nebius_api_key=None,
    )
    store = VerificationStore(settings.data_path)
    orchestrator = Orchestrator(settings, store)
    request = CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42")
    run = orchestrator.create(request)

    fake_github = MagicMock()
    fake_github.get_pull_request = AsyncMock(return_value=summary())
    fake_github.close = AsyncMock()
    monkeypatch.setattr(orchestrator_module, "GitHubClient", lambda token: fake_github)

    orchestrator.repository = MagicMock()
    orchestrator.repository.profile.return_value = RepositoryProfile(languages=["Python"], test_framework="pytest")
    orchestrator.repository.changed_files.return_value = ["coupon.py"]
    orchestrator.repository.diff.return_value = "diff"
    documents = [ContextDocument(path="coupon.py", content="discount", changed=True)]
    orchestrator.repository.context_documents.return_value = documents
    orchestrator.repository.impact_graph.return_value = ([], [])
    orchestrator.ranker.rank = AsyncMock(return_value=ContextRanking(documents=documents, accelerator="cuda"))
    hypothesis = Hypothesis(id="H1", description="Risk", affected_files=["coupon.py"], test_strategy="Boundary")
    generated = GeneratedTest(id="AEG-1", hypothesis_id="H1", file_path="", framework="pytest", test_code="")
    orchestrator.nebius.create_plan = AsyncMock(return_value=VerificationPlan([hypothesis], [generated], "heuristic-fallback"))

    await orchestrator.verify(run.id, request)
    stored = store.get(run.id)
    assert stored is not None
    assert stored.status == VerificationStatus.ANALYSIS_ONLY
    assert stored.metrics.context_accelerator == "cuda"
    assert all(stage.state.value == "complete" for stage in stored.stages)


@pytest.mark.asyncio
async def test_execution_workflow_classifies_regression(tmp_path: Path) -> None:
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work")
    store = VerificationStore(settings.data_path)
    orchestrator = Orchestrator(settings, store)
    request = CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42")
    run = orchestrator.create(request)
    run.summary = summary()
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q", install_command="pip install .")
    run.hypotheses = [Hypothesis(id="H1", description="Risk", affected_files=["coupon.py"], test_strategy="Boundary")]
    run.generated_tests = [GeneratedTest(id="AEG-1", hypothesis_id="H1", file_path="tests/test_new.py", framework="pytest", test_code="def test_x(): assert True")]
    orchestrator.repository = MagicMock()
    orchestrator.sandbox = MagicMock()
    orchestrator.sandbox.execute.side_effect = [
        execution("base", ExecutionStatus.PASSED), execution("head", ExecutionStatus.FAILED),
    ]

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work")
    assert run.status == VerificationStatus.REGRESSION_FOUND
    assert run.findings[0].classification == "REGRESSION"
    assert run.metrics.regressions_found == 1


@pytest.mark.asyncio
async def test_execution_without_generated_test_code_is_analysis_only(tmp_path: Path) -> None:
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work")
    store = VerificationStore(settings.data_path)
    orchestrator = Orchestrator(settings, store)
    request = CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42")
    run = orchestrator.create(request)
    run.summary = summary()
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q")
    run.hypotheses = [Hypothesis(id="H1", description="Risk", affected_files=["coupon.py"], test_strategy="Boundary")]
    run.generated_tests = [GeneratedTest(id="AEG-1", hypothesis_id="H1", file_path="", framework="pytest", test_code="")]
    orchestrator.repository = MagicMock()
    orchestrator.sandbox = MagicMock()

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work")

    assert run.status == VerificationStatus.ANALYSIS_ONLY
    orchestrator.sandbox.execute.assert_not_called()
    assert all(
        next(stage for stage in run.stages if stage.key == key).state.value == "complete"
        for key in ("base", "head", "compare")
    )


@pytest.mark.asyncio
async def test_workflow_records_environment_error(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work")
    store = VerificationStore(settings.data_path)
    orchestrator = Orchestrator(settings, store)
    request = CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42")
    run = orchestrator.create(request)
    fake_github = MagicMock()
    fake_github.get_pull_request = AsyncMock(side_effect=RuntimeError("GitHub unavailable"))
    fake_github.close = AsyncMock()
    monkeypatch.setattr(orchestrator_module, "GitHubClient", lambda token: fake_github)
    await orchestrator.verify(run.id, request)
    stored = store.get(run.id)
    assert stored is not None and stored.status == VerificationStatus.ENVIRONMENT_ERROR
    assert "GitHub unavailable" in (stored.error or "")
