from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.services.inference_budget import BudgetExceeded, InferenceBudget

MODEL = "nvidia/Nemotron-3_5-Lightning"


def ledger(tmp_path: Path, **kwargs) -> InferenceBudget:
    return InferenceBudget(tmp_path / "budget.sqlite3", **kwargs)


def test_budget_survives_restart_and_accounts_reported_usage(tmp_path):
    budget = ledger(tmp_path)
    ticket = budget.reserve("run1", "plan", MODEL, 1000, 1000)
    budget.complete(ticket, 500, 200, "fingerprint", {"result": "ok"})
    reopened = ledger(tmp_path)
    assert reopened.summary("run1")["input_tokens"] == 500
    assert reopened.summary("run1")["output_tokens"] == 200
    assert reopened.cached("fingerprint") == {"result": "ok"}
    assert reopened.summary("run1")["accounted_cost_usd"] > 0


def test_reservations_enforce_global_and_per_run_caps_before_call(tmp_path):
    budget = ledger(tmp_path, limit_usd="0.0003", per_run_usd="0.0003")
    budget.reserve("run1", "plan", MODEL, 1000, 1000)
    with pytest.raises(BudgetExceeded):
        budget.reserve("run2", "plan", MODEL, 1000, 1000)
    with pytest.raises(BudgetExceeded):
        budget.reserve("run1", "plan", MODEL, 1000, 1000)


def test_concurrent_requests_cannot_reserve_the_same_remaining_budget(tmp_path):
    budget = ledger(tmp_path, limit_usd="0.0003", per_run_usd="1")
    def reserve(index):
        try:
            budget.reserve(str(index), "plan", MODEL, 1000, 1000)
            return True
        except BudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(reserve, range(6))) == 1


def test_missing_usage_and_uncertain_failure_keep_full_reservation(tmp_path):
    budget = ledger(tmp_path)
    ticket = budget.reserve("run1", "plan", MODEL, 1000, 1000)
    reserved = budget.summary("run1")["accounted_cost_usd"]
    budget.complete(ticket, None, None, "x", {"ok": True})
    assert budget.summary("run1")["accounted_cost_usd"] == reserved
    ticket2 = budget.reserve("run1", "repair", MODEL, 1000, 1000)
    budget.fail(ticket2, definitely_unbilled=False)
    assert budget.summary("run1")["accounted_cost_usd"] == 2 * reserved


def test_known_unbilled_failure_releases_money_but_counts_attempt(tmp_path):
    budget = ledger(tmp_path, max_calls_per_run=1)
    ticket = budget.reserve("run1", "plan", MODEL, 1000, 1000)
    budget.fail(ticket, definitely_unbilled=True)
    assert budget.summary("run1")["accounted_cost_usd"] == 0
    with pytest.raises(BudgetExceeded):
        budget.reserve("run1", "plan", MODEL, 1000, 1000)


def test_unpriced_model_fails_closed_and_cache_hit_is_not_a_paid_call(tmp_path):
    budget = ledger(tmp_path)
    with pytest.raises(ValueError, match="price"):
        budget.reserve("run1", "plan", "unpriced/model", 1000, 1000)
    budget.record_cache_hit("run1", "plan", MODEL)
    assert budget.summary("run1")["cache_hits"] == 1
    assert budget.summary("run1")["calls"] == 0
    assert budget.summary("run1")["accounted_cost_usd"] == 0


@pytest.mark.parametrize("invalid", ["-0.0000001", "NaN", "Infinity", "not-money"])
def test_invalid_budget_values_fail_closed(tmp_path, invalid):
    with pytest.raises(ValueError):
        ledger(tmp_path, limit_usd=invalid)
