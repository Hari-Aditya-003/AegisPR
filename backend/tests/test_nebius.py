import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.verification import ExecutionStatus, Finding, GeneratedTest, RepositoryProfile, TestExecution
from app.services.context_ranker import ContextDocument
from app.services.nebius import NebiusGateway


@pytest.mark.asyncio
async def test_missing_key_returns_explicit_heuristic_plan() -> None:
    gateway = NebiusGateway(None, "https://example.invalid/v1", "model")
    plan = await gateway.create_plan(
        "diff",
        RepositoryProfile(languages=["Python"], test_framework="pytest", test_command="pytest -q"),
        [ContextDocument(path="coupon.py", content="discount", changed=True)],
    )
    assert plan.model_used == "heuristic-fallback"
    assert plan.hypotheses[0].affected_files == ["coupon.py"]
    assert plan.tests[0].test_code == ""


@pytest.mark.asyncio
async def test_structured_model_response_becomes_verification_plan() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    payload = {
        "hypotheses": [{
            "id": "H1", "description": "Risk", "risk_type": "logic",
            "affected_files": ["a.py"], "test_strategy": "Boundary", "testable": True,
        }],
        "tests": [{
            "id": "AEG-1", "hypothesis_id": "H1", "file_path": "tests/test_a.py",
            "framework": "pytest", "test_code": "def test_a(): assert True", "test_command": "pytest -q",
        }],
    }
    create = AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    ))
    gateway.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    plan = await gateway.create_plan(
        "diff", RepositoryProfile(languages=["Python"]),
        [ContextDocument(path="a.py", content="x = 1", changed=True)], focus="boundaries",
    )
    assert plan.model_used == "nvidia/model"
    assert plan.tests[0].hypothesis_id == "H1"
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_planner_requests_assertionless_bidirectional_output_examples() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    payload = {
        "hypotheses": [{"id": "H1", "description": "Risk", "affected_files": ["a.py"], "test_strategy": "Observe outputs"}],
        "tests": [{"id": "T1", "hypothesis_id": "H1", "file_path": "tests/test_examples.py", "framework": "pytest",
                   "test_code": "def test_example(): print('AEGISPR_OUTPUT=1')", "mode": "output"}],
    }
    create = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]))
    gateway.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    plan = await gateway.create_plan("diff", RepositoryProfile(languages=["Python"]), [])

    prompt = create.await_args.kwargs["messages"][1]["content"]
    assert plan.tests[0].mode == "output"
    assert "old implementation" in prompt
    assert "new implementation" in prompt
    assert "AEGISPR_OUTPUT=" in prompt
    assert "no assertions" in prompt


@pytest.mark.asyncio
async def test_planner_requests_bounded_property_api_and_security_checks_without_extra_call() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    payload = {
        "hypotheses": [{"id": "H1", "description": "Risk", "affected_files": ["api.py"], "test_strategy": "Check contract"}],
        "tests": [{"id": "T1", "hypothesis_id": "H1", "file_path": "tests/test_contract.py", "framework": "pytest",
                   "test_code": "def test_contract(): assert True", "mode": "assertion"}],
    }
    create = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]))
    gateway.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    profile = RepositoryProfile(languages=["Python"], property_frameworks=["Hypothesis"])

    await gateway.create_plan("-@login_required\n+def get_user(id): pass", profile, [])

    prompt = create.await_args.kwargs["messages"][1]["content"]
    assert "Hypothesis" in prompt and "max_examples=100" in prompt
    assert "authentication" in prompt and "input validation" in prompt
    assert "public API" in prompt
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_intent_review_asks_specific_questions_three_times_and_majority_votes() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    gateway._request = AsyncMock(side_effect=[
        {"intent": "unintended", "reason": "The PR only promises UI text."},
        {"intent": "unclear", "reason": "The description is sparse."},
        {"intent": "unintended", "reason": "The discount changed unexpectedly."},
    ])
    finding = Finding(
        hypothesis_id="H1", generated_test_id="T1", classification="BEHAVIOR_CHANGE",
        summary="Discount boundary",
        base_execution=TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.PASSED, stdout="AEGISPR_OUTPUT=0\n"),
        head_execution=TestExecution(branch="head", commit="b" * 40, status=ExecutionStatus.PASSED, stdout="AEGISPR_OUTPUT=-10\n"),
    )

    review = await gateway.classify_intent(
        finding, title="Change coupon copy", description="Update the label", commit_messages=["Update label"],
    )

    assert review.verdict == "unintended"
    assert review.votes == ["unintended", "unclear", "unintended"]
    assert gateway._request.await_count == 3
    prompts = [call.args[1][1]["content"] for call in gateway._request.await_args_list]
    assert all("Update label" in prompt and "-10" in prompt for prompt in prompts)
    assert all("intentional" in prompt and "pre-existing" in prompt for prompt in prompts)
    assert len({call.args[0] for call in gateway._request.await_args_list}) == 3


@pytest.mark.asyncio
async def test_intent_review_tie_or_invalid_vote_is_unclear() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    gateway._request = AsyncMock(side_effect=[
        {"intent": "intended", "reason": "a"},
        {"intent": "unintended", "reason": "b"},
        {"intent": "unknown", "reason": "c"},
    ])
    finding = Finding(
        hypothesis_id="H1", generated_test_id="T1", classification="BEHAVIOR_CHANGE", summary="Risk",
        base_execution=TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.PASSED, stdout="AEGISPR_OUTPUT=1\n"),
        head_execution=TestExecution(branch="head", commit="b" * 40, status=ExecutionStatus.PASSED, stdout="AEGISPR_OUTPUT=2\n"),
    )
    review = await gateway.classify_intent(finding, title="title", description="", commit_messages=[])
    assert review.verdict == "unclear"


@pytest.mark.asyncio
async def test_distinct_nemotron_models_cast_three_traceable_advisory_votes() -> None:
    models = [
        "nvidia/Nemotron-3_5-Lightning",
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    ]
    gateway = NebiusGateway("key", "https://example.invalid/v1", models[0], intent_models=models)
    gateway._request = AsyncMock(side_effect=[
        {"intent": "unintended", "reason": "Contract changed."},
        {"intent": "unintended", "reason": "Out of scope."},
        {"intent": "unintended", "reason": "Boundary changed."},
    ])
    finding = Finding(
        hypothesis_id="H1", generated_test_id="T1", classification="BEHAVIOR_CHANGE", summary="Boundary",
        base_execution=TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.PASSED, stdout="AEGISPR_OUTPUT=0\n"),
        head_execution=TestExecution(branch="head", commit="b" * 40, status=ExecutionStatus.PASSED, stdout="AEGISPR_OUTPUT=-5\n"),
    )

    review = await gateway.classify_intent(finding, title="Preserve coupon behavior", description="Refactor only", commit_messages=[])

    assert review.verdict == "unintended"
    assert review.models == models
    assert review.votes == ["unintended"] * 3
    assert [call.kwargs["model_override"] for call in gateway._request.await_args_list] == models
    assert gateway._request.await_count == 3


@pytest.mark.asyncio
async def test_cross_model_disagreement_remains_unclear_even_with_two_matching_votes() -> None:
    models = [
        "nvidia/Nemotron-3_5-Lightning",
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    ]
    gateway = NebiusGateway("key", "https://example.invalid/v1", models[0], intent_models=models)
    gateway._request = AsyncMock(side_effect=[
        {"intent": "intended", "reason": "Author says so."},
        {"intent": "intended", "reason": "Probably intended."},
        {"intent": "unintended", "reason": "Refactor claim conflicts."},
    ])
    finding = Finding(
        hypothesis_id="H1", generated_test_id="T1", classification="BEHAVIOR_CHANGE", summary="Boundary",
        base_execution=TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.PASSED, stdout="AEGISPR_OUTPUT=0\n"),
        head_execution=TestExecution(branch="head", commit="b" * 40, status=ExecutionStatus.PASSED, stdout="AEGISPR_OUTPUT=-5\n"),
    )

    review = await gateway.classify_intent(finding, title="Refactor", description="", commit_messages=[])

    assert review.verdict == "unclear"
    assert review.reason == "Models disagreed; ask the PR author or maintainer to clarify the intended behavior."


def test_intent_model_roster_requires_three_distinct_priced_nemotron_models() -> None:
    with pytest.raises(ValueError, match="three distinct"):
        NebiusGateway("key", "https://example.invalid/v1", "nvidia/Nemotron-3_5-Lightning", intent_models=["nvidia/Nemotron-3_5-Lightning"] * 3)
    with pytest.raises(ValueError, match="verified price"):
        NebiusGateway("key", "https://example.invalid/v1", "nvidia/Nemotron-3_5-Lightning", intent_models=[
            "nvidia/Nemotron-3_5-Lightning", "nvidia/nemotron-3-super-120b-a12b", "nvidia/unknown",
        ])


@pytest.mark.asyncio
async def test_refinement_preserves_test_identity_and_uses_base_error() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    gateway._request = AsyncMock(return_value={"test_code": "def test_fixed(): print('AEGISPR_OUTPUT=0')"})
    generated = GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest",
                              test_code="def test_broken(): missing_name()", mode="output")
    base = TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.FAILED, stderr="NameError: missing_name")

    refined = await gateway.refine_test(generated, base, attempt=1)

    assert refined.id == generated.id
    assert refined.mode == "output"
    assert "test_fixed" in refined.test_code
    assert "NameError" in gateway._request.await_args.args[1][1]["content"]


@pytest.mark.asyncio
async def test_refinement_rejects_empty_or_malicious_code() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    gateway._request = AsyncMock(return_value={"test_code": ""})
    generated = GeneratedTest(id="T1", hypothesis_id="H1", file_path="tests/test_x.py", framework="pytest",
                              test_code="def test_broken(): missing_name()", mode="output")
    base = TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.FAILED)
    with pytest.raises(ValueError, match="empty refined test"):
        await gateway.refine_test(generated, base, attempt=1)


@pytest.mark.asyncio
async def test_empty_model_response_is_rejected() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    create = AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))]
    ))
    gateway.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with pytest.raises(ValueError, match="empty verification plan"):
        await gateway.create_plan("", RepositoryProfile(), [])


@pytest.mark.asyncio
async def test_regression_evidence_becomes_bounded_root_cause() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    create = AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"root_cause": "The new discount path omits the zero-floor clamp."})))]
    ))
    gateway.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    finding = Finding(
        hypothesis_id="H1", generated_test_id="AEG-1", classification="REGRESSION",
        summary="Negative total", affected_file="coupon.py",
        base_execution=TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.PASSED),
        head_execution=TestExecution(branch="head", commit="b" * 40, status=ExecutionStatus.FAILED, stderr="assert 0 <= -5"),
    )

    root_cause = await gateway.analyze_root_cause(finding)

    assert root_cause == "The new discount path omits the zero-floor clamp."
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_root_cause_is_unavailable_without_nebius() -> None:
    gateway = NebiusGateway(None, "https://example.invalid/v1", "model")
    assert await gateway.analyze_root_cause(None) is None


@pytest.mark.asyncio
async def test_structured_repair_response_becomes_bounded_patch() -> None:
    gateway = NebiusGateway("key", "https://example.invalid/v1", "nvidia/model")
    payload = {
        "summary": "Clamp the total at zero.",
        "patch": (
            "diff --git a/coupon.py b/coupon.py\n"
            "--- a/coupon.py\n"
            "+++ b/coupon.py\n"
            "@@ -1 +1 @@\n"
            "-return total - discount\n"
            "+return max(total - discount, 0)\n"
        ),
    }
    create = AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    ))
    gateway.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    finding = Finding(
        hypothesis_id="H1", generated_test_id="AEG-1", classification="REGRESSION",
        summary="Negative total", affected_file="coupon.py", root_cause="Missing clamp",
        base_execution=TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.PASSED),
        head_execution=TestExecution(branch="head", commit="b" * 40, status=ExecutionStatus.FAILED),
    )

    proposal = await gateway.create_repair(finding, "diff", "return total - discount", None)

    assert proposal.summary == "Clamp the total at zero."
    assert proposal.patch.startswith("diff --git")
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_repair_requires_nebius_credentials() -> None:
    gateway = NebiusGateway(None, "https://example.invalid/v1", "model")
    finding = Finding(
        hypothesis_id="H1", generated_test_id="AEG-1", classification="REGRESSION",
        summary="Negative total",
        base_execution=TestExecution(branch="base", commit="a" * 40, status=ExecutionStatus.PASSED),
        head_execution=TestExecution(branch="head", commit="b" * 40, status=ExecutionStatus.FAILED),
    )
    with pytest.raises(ValueError, match="Nebius"):
        await gateway.create_repair(finding, "diff", "source", None)
