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
    assert request["max_tokens"] == 8192
    prompt = request["messages"][1]["content"]
    assert "exactly one test file" in prompt
    assert "both old-code and new-code" in prompt
    assert "at most eight" in prompt


@pytest.mark.asyncio
async def test_nemotron_does_not_force_unadvertised_json_mode_or_hidden_reasoning(tmp_path):
    gateway, create, _ = setup_gateway(tmp_path)
    await gateway.create_plan("diff", RepositoryProfile(), [])
    request = create.call_args.kwargs
    assert "response_format" not in request
    assert request["reasoning_effort"] == "none"


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


@pytest.mark.asyncio
async def test_malformed_plan_gets_one_budgeted_correction_request(tmp_path):
    gateway, create, budget = setup_gateway(tmp_path)
    broken = response()
    broken.choices[0].message.content = "{not json"
    create.side_effect = [broken, response()]
    token = current_run.set("corrected")
    try:
        plan = await gateway.create_plan("diff", RepositoryProfile(), [])
        assert plan.tests[0].id == "T1"
        assert create.await_count == 2
        assert budget.summary("corrected")["calls"] == 2
        assert "invalid" in create.await_args.kwargs["messages"][1]["content"].lower()
    finally:
        current_run.reset(token)


@pytest.mark.asyncio
async def test_oversized_plan_correction_requests_one_test_object_with_imports(tmp_path):
    gateway, create, budget = setup_gateway(tmp_path)
    oversized = response()
    payload = json.loads(oversized.choices[0].message.content)
    payload["tests"] = [dict(payload["tests"][0], id=f"T{index}") for index in range(1, 9)]
    oversized.choices[0].message.content = json.dumps(payload)
    create.side_effect = [oversized, response()]
    token = current_run.set("oversized")
    try:
        plan = await gateway.create_plan("diff", RepositoryProfile(languages=["Python"]), [])
        assert len(plan.tests) == 1
        assert create.await_count == 2
        assert budget.summary("oversized")["calls"] == 2
        first_prompt = create.await_args_list[0].kwargs["messages"][1]["content"]
        correction = create.await_args_list[1].kwargs["messages"][1]["content"]
        assert "tests array must contain exactly one object" in first_prompt
        assert "exactly one test object" in correction
        assert "single test_code" in correction
        assert "imports" in correction
    finally:
        current_run.reset(token)


@pytest.mark.asyncio
async def test_plan_correction_respects_one_attempt_run_limit(tmp_path):
    gateway, create, budget = setup_gateway(tmp_path, max_calls_per_run=1)
    broken = response()
    broken.choices[0].message.content = "{not json"
    create.return_value = broken
    token = current_run.set("limited")
    try:
        with pytest.raises(ValueError, match="limit"):
            await gateway.create_plan("diff", RepositoryProfile(), [])
        assert create.await_count == 1
        assert budget.summary("limited")["calls"] == 1
    finally:
        current_run.reset(token)


@pytest.mark.asyncio
async def test_invalid_plan_reference_gets_one_correction_request(tmp_path):
    gateway, create, _ = setup_gateway(tmp_path)
    broken = response()
    payload = json.loads(broken.choices[0].message.content)
    payload["tests"][0]["hypothesis_id"] = "missing"
    broken.choices[0].message.content = json.dumps(payload)
    create.side_effect = [broken, response()]
    plan = await gateway.create_plan("diff", RepositoryProfile(), [])
    assert plan.tests[0].hypothesis_id == "H1"
    assert create.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["unsafe_id", "orphan", "duplicate", "too_many"])
async def test_generated_plan_references_and_scope_are_validated(tmp_path, mutation):
    gateway, create, _ = setup_gateway(tmp_path)
    data = response()
    payload = json.loads(data.choices[0].message.content)
    if mutation == "unsafe_id":
        payload["tests"][0]["id"] = "../../outside"
    elif mutation == "orphan":
        payload["tests"][0]["hypothesis_id"] = "missing"
    elif mutation == "duplicate":
        payload["tests"].append(payload["tests"][0])
    else:
        payload["hypotheses"] *= 3
    data.choices[0].message.content = json.dumps(payload)
    create.return_value = data
    with pytest.raises(ValueError):
        await gateway.create_plan("diff", RepositoryProfile(), [])
