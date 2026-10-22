from pathlib import Path

import pytest

from app.evaluation.seeded_dataset import load_cases, main, materialize_cases, observe_case, validate_cases


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


def test_dataset_materializes_local_base_and_head_git_commits_without_labels_in_repos(tmp_path: Path) -> None:
    output = tmp_path / "seeded-prs"
    index = materialize_cases(load_cases(DATASET), output)
    assert len(index["cases"]) == 12
    assert output.joinpath("index.json").is_file()
    for item in index["cases"]:
        repository = output / item["id"]
        assert repository.joinpath(".git").is_dir()
        assert item["base_commit"] != item["head_commit"]
        assert len(item["base_commit"]) == len(item["head_commit"]) == 40
        assert not repository.joinpath("labels.json").exists()


def test_dataset_materialization_never_overwrites_existing_directory(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("user content")
    with pytest.raises(FileExistsError):
        materialize_cases(load_cases(DATASET), output)
    assert marker.read_text() == "user content"


def test_seeded_dataset_cli_validates_and_materializes(tmp_path: Path, capsys) -> None:
    assert main(["validate"]) == 0
    assert '"model_runs": 0' in capsys.readouterr().out
    output = tmp_path / "benchmark-repos"
    assert main(["materialize", "--output", str(output)]) == 0
    assert output.joinpath("index.json").exists()
