import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.verification import ExecutionStatus, Finding, RepositoryProfile, TestExecution
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
