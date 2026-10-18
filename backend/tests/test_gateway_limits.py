import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.verification import RepositoryProfile
from app.services.inference_budget import InferenceBudget, current_run
from app.services.nebius import NebiusGateway, InferenceUnavailable

MODEL = "nvidia/Nemotron-3_5-Lightning"


def response():
    payload = {"hypotheses": [{"id": "H1", "description": "Risk", "test_strategy": "Boundary"}],
               "tests": [{"id": "T1", "hypothesis_id": "H1", "file_path": "tests/test_x.py", "framework": "pytest", "test_code": "def test_x(): assert True"}]}
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)), finish_reason="stop")],
                           usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50))


def setup_gateway(tmp_path, **kwargs):
    budget = InferenceBudget(tmp_path / "costs.sqlite3", **kwargs)
    gateway = NebiusGateway("test", "https://example.invalid/v1", MODEL, budget=budget)
    create = AsyncMock(return_value=response())
    gateway.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return gateway, create, budget


@pytest.mark.asyncio
async def test_exact_prompt_cache_prevents_repeated_paid_requests(tmp_path):
    gateway, create, budget = setup_gateway(tmp_path)
    token = current_run.set("r1")
    try:
        await gateway.create_plan("diff", RepositoryProfile(), [])
        await gateway.create_plan("diff", RepositoryProfile(), [])
        assert create.await_count == 1
        assert budget.summary("r1")["cache_hits"] == 1
        assert budget.summary("r1")["input_tokens"] == 100
    finally:
        current_run.reset(token)


@pytest.mark.asyncio
async def test_zero_budget_blocks_before_any_network_call(tmp_path):
    gateway, create, _ = setup_gateway(tmp_path, limit_usd="0")
    with pytest.raises(ValueError, match="limit"):
        await gateway.create_plan("diff", RepositoryProfile(), [])
    create.assert_not_awaited()


@pytest.mark.asyncio
async def test_large_input_is_bounded_and_maximum_output_is_explicit(tmp_path):
    gateway, create, _ = setup_gateway(tmp_path)
    await gateway.create_plan("x" * 200_000, RepositoryProfile(), [])
    request = create.call_args.kwargs
    assert len(json.dumps(request["messages"]).encode()) <= 32_000
    assert request["max_tokens"] <= 3072


@pytest.mark.asyncio
async def test_billing_failure_has_no_retry_and_leaks_no_provider_details(tmp_path):
    gateway, create, budget = setup_gateway(tmp_path)
    error = RuntimeError("private-provider-payload")
    error.status_code = 402
    create.side_effect = error
    with pytest.raises(InferenceUnavailable, match="credits") as captured:
        await gateway.create_plan("diff", RepositoryProfile(), [])
    assert "private-provider" not in str(captured.value)
    assert create.await_count == 1
    assert budget.summary()["accounted_cost_usd"] == 0


@pytest.mark.asyncio
async def test_truncated_response_is_not_accepted_or_retried(tmp_path):
    gateway, create, budget = setup_gateway(tmp_path)
    data = response()
    data.choices[0].finish_reason = "length"
    create.return_value = data
    with pytest.raises(InferenceUnavailable, match="truncated"):
        await gateway.create_plan("diff", RepositoryProfile(), [])
    assert create.await_count == 1
    assert budget.summary()["accounted_cost_usd"] > 0
