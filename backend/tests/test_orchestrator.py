from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents import orchestrator as orchestrator_module
from app.agents.orchestrator import Orchestrator
from app.config import Settings
from app.schemas.verification import (
    CreateVerificationRequest, ExecutionStatus, GeneratedTest, Hypothesis, PullRequestSummary,
    RepairCheck, RepairRequest, RepairStatus, RepositoryProfile, TestExecution, VerificationStatus,
)
from app.services.context_ranker import ContextDocument, ContextRanking
from app.services.nebius import IntentReview, RepairProposal, VerificationPlan
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
    orchestrator.nebius.analyze_root_cause = AsyncMock(return_value="The changed branch drops the boundary guard.")
    orchestrator.sandbox.execute.side_effect = [
        execution("base", ExecutionStatus.PASSED), execution("head", ExecutionStatus.FAILED),
    ]

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work")
    assert run.status == VerificationStatus.REGRESSION_FOUND
    assert run.findings[0].classification == "REGRESSION"
    assert run.findings[0].root_cause == "The changed branch drops the boundary guard."
    assert run.metrics.regressions_found == 1


@pytest.mark.asyncio
async def test_output_difference_needs_two_stable_reruns_before_intent_review(tmp_path: Path) -> None:
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work")
    orchestrator = Orchestrator(settings, VerificationStore(settings.data_path))
    run = orchestrator.create(CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42"))
    run.summary = summary()
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q")
    run.hypotheses = [Hypothesis(id="H1", description="Discount boundary", test_strategy="Print result")]
    run.generated_tests = [GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest", test_code="print('AEGISPR_OUTPUT=0')", mode="output")]
    orchestrator.repository = MagicMock()
    orchestrator.sandbox = MagicMock()
    executions = []
    for _ in range(3):
        for branch, value in (("base", 0), ("head", -10)):
            result = execution(branch, ExecutionStatus.PASSED)
            result.stdout = f"AEGISPR_OUTPUT={value}\n"
            executions.append(result)
    orchestrator.sandbox.execute.side_effect = executions

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work")

    assert run.status == VerificationStatus.INCONCLUSIVE
    assert run.findings[0].classification == "BEHAVIOR_CHANGE"
    assert len(run.findings[0].confirmation_executions) == 4
    assert orchestrator.sandbox.execute.call_count == 6
    assert run.metrics.regressions_found == 0


@pytest.mark.asyncio
async def test_unstable_output_difference_is_inconclusive(tmp_path: Path) -> None:
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work")
    orchestrator = Orchestrator(settings, VerificationStore(settings.data_path))
    run = orchestrator.create(CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42"))
    run.summary = summary()
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q")
    run.hypotheses = [Hypothesis(id="H1", description="Discount boundary", test_strategy="Print result")]
    run.generated_tests = [GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest", test_code="print('AEGISPR_OUTPUT=0')", mode="output")]
    orchestrator.repository = MagicMock()
    orchestrator.sandbox = MagicMock()
    def result(branch, value):
        item = execution(branch, ExecutionStatus.PASSED)
        item.stdout = f"AEGISPR_OUTPUT={value}\n"
        return item
    orchestrator.sandbox.execute.side_effect = [result("base", 0), result("head", -10), result("base", 0), result("head", 0)]

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work")

    assert run.status == VerificationStatus.INCONCLUSIVE
    assert run.findings[0].classification == "INCONCLUSIVE"
    assert len(run.findings[0].confirmation_executions) == 2


@pytest.mark.asyncio
async def test_stable_output_difference_records_advisory_intent_without_claiming_confirmed_bug(tmp_path: Path) -> None:
    models = ["nvidia/Nemotron-3_5-Lightning", "nvidia/nemotron-3-super-120b-a12b",
              "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "nvidia/Nemotron-3-Ultra-550b-a55b"]
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work",
                        nebius_api_key="test-key", intent_review_models=",".join(models))
    orchestrator = Orchestrator(settings, VerificationStore(settings.data_path))
    run = orchestrator.create(CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42"))
    run.summary = summary()
    run.summary.description = "Only update the label"
    run.summary.commit_messages = ["Update coupon label"]
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q")
    run.hypotheses = [Hypothesis(id="H1", description="Discount boundary", test_strategy="Print result")]
    run.generated_tests = [GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest", test_code="print('AEGISPR_OUTPUT=0')", mode="output")]
    orchestrator.repository = MagicMock()
    orchestrator.sandbox = MagicMock()
    results = []
    for _ in range(3):
        for branch, value in (("base", 0), ("head", -10)):
            item = execution(branch, ExecutionStatus.PASSED)
            item.stdout = f"AEGISPR_OUTPUT={value}\n"
            results.append(item)
    orchestrator.sandbox.execute.side_effect = results
    orchestrator.nebius.classify_intent = AsyncMock(return_value=IntentReview("unintended", ["unintended"] * 4, "Outside stated scope", models=models))

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work")

    assert run.status == VerificationStatus.INCONCLUSIVE
    assert run.metrics.regressions_found == 0
    assert run.findings[0].intent_classification == "unintended"
    assert run.findings[0].intent_votes == ["unintended"] * 4
    assert run.findings[0].intent_vote_models == models
    assert orchestrator.nebius.classify_intent.await_args.kwargs["commit_messages"] == ["Update coupon label"]


@pytest.mark.asyncio
async def test_commit_metadata_failure_does_not_discard_executed_output_evidence(tmp_path: Path) -> None:
    import httpx
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work", nebius_api_key="test-key")
    orchestrator = Orchestrator(settings, VerificationStore(settings.data_path))
    run = orchestrator.create(CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42"))
    run.summary = summary()
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q")
    run.hypotheses = [Hypothesis(id="H1", description="Risk", test_strategy="Observe")]
    run.generated_tests = [GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest", test_code="print('AEGISPR_OUTPUT=1')", mode="output")]
    orchestrator.repository = MagicMock()
    orchestrator.sandbox = MagicMock()
    receipts = []
    for _ in range(3):
        for branch, value in (("base", 1), ("head", 2)):
            item = execution(branch, ExecutionStatus.PASSED)
            item.stdout = f"AEGISPR_OUTPUT={value}\n"
            receipts.append(item)
    orchestrator.sandbox.execute.side_effect = receipts
    github = MagicMock()
    github.get_commit_messages = AsyncMock(side_effect=httpx.HTTPError("metadata unavailable"))
    orchestrator.nebius.classify_intent = AsyncMock(return_value=IntentReview("unclear", ["unclear"] * 3, "More context needed"))

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work", github=github, reference=object())

    assert run.status == VerificationStatus.INCONCLUSIVE
    assert run.findings[0].intent_classification == "unclear"
    assert orchestrator.nebius.classify_intent.await_args.kwargs["commit_messages"] == []


@pytest.mark.asyncio
async def test_failed_generated_base_test_is_refined_before_head_execution(tmp_path: Path) -> None:
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work", nebius_api_key="test-key")
    orchestrator = Orchestrator(settings, VerificationStore(settings.data_path))
    run = orchestrator.create(CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42"))
    run.summary = summary()
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q")
    run.hypotheses = [Hypothesis(id="H1", description="Risk", test_strategy="Boundary")]
    generated = GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest", test_code="broken()")
    run.generated_tests = [generated]
    orchestrator.repository = MagicMock()
    orchestrator.sandbox = MagicMock()
    orchestrator.sandbox.execute.side_effect = [
        execution("base", ExecutionStatus.FAILED), execution("base", ExecutionStatus.PASSED), execution("head", ExecutionStatus.FAILED),
    ]
    orchestrator.nebius.refine_test = AsyncMock(return_value=generated.model_copy(update={"test_code": "def test_fixed(): assert True"}))
    orchestrator.nebius.analyze_root_cause = AsyncMock(return_value=None)

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work")

    assert run.status == VerificationStatus.REGRESSION_FOUND
    assert run.generated_tests[0].test_code == "def test_fixed(): assert True"
    assert len(run.findings[0].refinement_executions) == 2
    assert orchestrator.sandbox.execute.call_args_list[1].args[2] == "base"
    assert orchestrator.nebius.refine_test.await_count == 1


@pytest.mark.asyncio
async def test_mutation_score_counts_only_executed_valid_mutant(tmp_path: Path) -> None:
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work")
    orchestrator = Orchestrator(settings, VerificationStore(settings.data_path))
    run = orchestrator.create(CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42"))
    run.summary = summary()
    run.changed_files = ["coupon.py"]
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q")
    run.hypotheses = [Hypothesis(id="H1", description="Boundary", test_strategy="Assertion")]
    run.generated_tests = [GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest", test_code="def test_x(): assert True")]
    orchestrator.repository = MagicMock()
    orchestrator.repository.mutate_changed_python_line.return_value = ("coupon.py", "> to >=")
    orchestrator.sandbox = MagicMock()
    orchestrator.sandbox.execute.side_effect = [
        execution("base", ExecutionStatus.PASSED), execution("head", ExecutionStatus.PASSED), execution("mutant", ExecutionStatus.FAILED),
    ]

    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work", diff="a changed line")

    assert run.metrics.mutants_valid == 1
    assert run.metrics.mutants_caught == 1
    assert run.metrics.mutation_catch_rate == 1.0
    assert run.findings[0].mutation_operator == "> to >="
    assert run.findings[0].mutation_caught is True


@pytest.mark.asyncio
async def test_optional_explanation_failure_preserves_reproduced_regression(tmp_path):
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work")
    orchestrator = Orchestrator(settings, VerificationStore(settings.data_path))
    run = orchestrator.create(CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42"))
    run.summary = summary()
    run.repository_profile = RepositoryProfile(languages=["Python"], test_command="pytest -q")
    run.hypotheses = [Hypothesis(id="H1", description="Risk", test_strategy="Boundary")]
    run.generated_tests = [GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest", test_code="def test_x(): assert True")]
    orchestrator.repository = MagicMock()
    orchestrator.sandbox = MagicMock()
    orchestrator.sandbox.execute.side_effect = [execution("base", ExecutionStatus.PASSED), execution("head", ExecutionStatus.FAILED)]
    from app.services.nebius import InferenceUnavailable
    orchestrator.nebius.analyze_root_cause = AsyncMock(side_effect=InferenceUnavailable("Nebius credits are unavailable"))
    await orchestrator._execute_plan(run, tmp_path / "repo", tmp_path / "work")
    assert run.status == VerificationStatus.REGRESSION_FOUND
    assert len(run.findings) == 1
    assert run.findings[0].root_cause is None
    assert run.findings[0].explanation_error == "Nebius credits are unavailable"


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
    fake_github.get_pull_request = AsyncMock(side_effect=RuntimeError("private-provider-secret GitHub unavailable"))
    fake_github.close = AsyncMock()
    monkeypatch.setattr(orchestrator_module, "GitHubClient", lambda token: fake_github)
    await orchestrator.verify(run.id, request)
    stored = store.get(run.id)
    assert stored is not None and stored.status == VerificationStatus.ENVIRONMENT_ERROR
    assert "could not complete" in (stored.error or "")
    assert "private-provider-secret" not in stored.error


@pytest.mark.asyncio
async def test_repair_workflow_verifies_minimal_patch_with_separate_checks(tmp_path: Path) -> None:
    settings = Settings(
        data_path=tmp_path / "runs.sqlite3",
        workspace_root=tmp_path / "work",
        enable_sandbox=True,
        nebius_api_key="test-key",
    )
    store = VerificationStore(settings.data_path)
    orchestrator = Orchestrator(settings, store)
    request = CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42")
    run = orchestrator.create(request)
    run.summary = summary()
    run.status = VerificationStatus.REGRESSION_FOUND
    run.repository_profile = RepositoryProfile(
        languages=["Python"],
        install_command="pip install .",
        test_command="pytest -q",
        build_command=None,
        lint_command=None,
    )
    run.hypotheses = [
        Hypothesis(
            id="H1",
            description="Negative total",
            affected_files=["coupon.py"],
            test_strategy="Oversized discount",
        )
    ]
    generated = GeneratedTest(
        id="AEG-1",
        hypothesis_id="H1",
        file_path="tests/test_coupon_boundary.py",
        framework="pytest",
        test_code="def test_floor(): assert True",
    )
    run.generated_tests = [generated]
    base = execution("base", ExecutionStatus.PASSED)
    head = execution("head", ExecutionStatus.FAILED)
    run.findings = [
        orchestrator_module.Finding(
            id="finding-1",
            hypothesis_id="H1",
            generated_test_id="AEG-1",
            classification="REGRESSION",
            summary="Negative total",
            affected_file="coupon.py",
            root_cause="The result is not clamped.",
            base_execution=base,
            head_execution=head,
        )
    ]
    store.save(run)

    orchestrator.repository = MagicMock()
    orchestrator.repository.diff.return_value = "diff"
    orchestrator.repository.file_content.return_value = "def apply_coupon(total, discount): return total - discount"
    orchestrator.nebius.create_repair = AsyncMock(
        return_value=RepairProposal(
            patch="diff --git a/coupon.py b/coupon.py\n--- a/coupon.py\n+++ b/coupon.py\n",
            summary="Clamp the total at zero.",
        )
    )
    orchestrator.sandbox.verify_repair = MagicMock(
        return_value=[
            RepairCheck(name="existing_tests", command="pytest -q", execution=execution("repair", ExecutionStatus.PASSED)),
            RepairCheck(name="generated_tests", command="pytest -q", execution=execution("repair", ExecutionStatus.PASSED)),
            RepairCheck(name="build", command=None, execution=execution("repair", ExecutionStatus.SKIPPED)),
            RepairCheck(name="lint", command=None, execution=execution("repair", ExecutionStatus.SKIPPED)),
        ]
    )

    queued = orchestrator.create_repair(run.id, RepairRequest(finding_id="finding-1"))
    assert queued.repair is not None and queued.repair.status == RepairStatus.PENDING

    await orchestrator.repair(run.id, RepairRequest(finding_id="finding-1"))

    stored = store.get(run.id)
    assert stored is not None
    assert stored.status == VerificationStatus.FIX_VERIFIED
    assert stored.repair is not None
    assert stored.repair.status == RepairStatus.VERIFIED
    assert stored.repair.summary == "Clamp the total at zero."
    assert [check.name for check in stored.repair.checks] == [
        "existing_tests", "generated_tests", "build", "lint",
    ]
    orchestrator.repository.apply_patch.assert_called_once()
    assert orchestrator.repository.apply_patch.call_args.args[2] == set(run.changed_files)


def test_repair_request_rejects_non_regression_run(tmp_path: Path) -> None:
    settings = Settings(data_path=tmp_path / "runs.sqlite3", workspace_root=tmp_path / "work")
    store = VerificationStore(settings.data_path)
    orchestrator = Orchestrator(settings, store)
    request = CreateVerificationRequest(pull_request_url="https://github.com/acme/store/pull/42")
    run = orchestrator.create(request)

    with pytest.raises(ValueError, match="confirmed regression"):
        orchestrator.create_repair(run.id, RepairRequest())
