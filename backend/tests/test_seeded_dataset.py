from pathlib import Path

import pytest

from app.evaluation.seeded_dataset import load_cases, observe_case, validate_cases


DATASET = Path(__file__).resolve().parents[2] / "evals" / "seeded-prs" / "cases.json"


def test_seeded_dataset_has_balanced_review_cases() -> None:
    cases = load_cases(DATASET)
    assert 10 <= len(cases) <= 20
    assert len({case.id for case in cases}) == len(cases)
    assert {case.language for case in cases} == {"python", "node"}
    assert {case.intent for case in cases} == {"unintended", "intended", "no_change"}
    assert {case.category for case in cases} >= {
        "off_by_one", "boundary", "null_handling", "async_race",
    }


@pytest.mark.parametrize("case_id", [
    "py-coupon-floor", "py-page-boundary", "py-null-name", "py-stock-limit",
    "py-tax-rounding", "py-age-policy", "py-currency-format", "py-refactor",
    "js-list-boundary", "js-null-name", "js-sort-order", "js-async-race",
])
def test_seeded_case_observations_match_committed_ground_truth(case_id: str) -> None:
    cases = {case.id: case for case in load_cases(DATASET)}
    assert case_id in cases
    case = cases[case_id]
    assert observe_case(case, "base") == case.expected_base
    assert observe_case(case, "head") == case.expected_head


def test_dataset_validation_reports_fixture_counts_not_model_accuracy() -> None:
    summary = validate_cases(load_cases(DATASET))
    assert summary == {
        "cases": 12,
        "unintended": 8,
        "intended": 3,
        "no_change": 1,
        "fixtures_verified": 12,
        "model_runs": 0,
    }
