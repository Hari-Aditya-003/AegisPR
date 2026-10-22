import pytest

from app.schemas.verification import ExecutionStatus, TestExecution
from app.verification.differential import Classification, compare_executions


def execution(branch: str, status: ExecutionStatus) -> TestExecution:
    return TestExecution(
        branch=branch,
        commit="a" * 40,
        status=status,
        exit_code=0 if status == ExecutionStatus.PASSED else 1,
        stdout="",
        stderr="",
        duration_ms=12,
    )


@pytest.mark.parametrize(
    ("base", "head", "expected"),
    [
        (ExecutionStatus.PASSED, ExecutionStatus.FAILED, Classification.REGRESSION),
        (ExecutionStatus.FAILED, ExecutionStatus.FAILED, Classification.PRE_EXISTING),
        (ExecutionStatus.PASSED, ExecutionStatus.PASSED, Classification.NO_FAILURE_REPRODUCED),
        (ExecutionStatus.FAILED, ExecutionStatus.PASSED, Classification.POSSIBLE_IMPROVEMENT),
        (ExecutionStatus.ERROR, ExecutionStatus.PASSED, Classification.INCONCLUSIVE),
    ],
)
def test_classifies_base_and_pr_results(base, head, expected) -> None:
    assert compare_executions(execution("base", base), execution("head", head)) == expected


def test_rejects_mismatched_commit_roles() -> None:
    with pytest.raises(ValueError, match="base and head"):
        compare_executions(execution("head", ExecutionStatus.PASSED), execution("base", ExecutionStatus.FAILED))


def test_output_examples_detect_behavior_change_without_claiming_regression() -> None:
    base = execution("base", ExecutionStatus.PASSED)
    head = execution("head", ExecutionStatus.PASSED)
    base.stdout = 'runner noise\nAEGISPR_OUTPUT={"total":0}\n'
    head.stdout = 'runner noise\nAEGISPR_OUTPUT={"total":-10}\n'
    assert compare_executions(base, head, mode="output") == Classification.BEHAVIOR_CHANGE


def test_output_examples_ignore_runner_noise_and_json_key_order() -> None:
    base = execution("base", ExecutionStatus.PASSED)
    head = execution("head", ExecutionStatus.PASSED)
    base.stdout = 'AEGISPR_OUTPUT={"a":1,"b":2}\n1 passed\n'
    head.stdout = 'AEGISPR_OUTPUT={"b":2,"a":1}\n2 passed\n'
    assert compare_executions(base, head, mode="output") == Classification.NO_FAILURE_REPRODUCED


@pytest.mark.parametrize("base_output,head_output", [
    ("", 'AEGISPR_OUTPUT=1\n'),
    ('AEGISPR_OUTPUT=not-json\n', 'AEGISPR_OUTPUT=1\n'),
    ('AEGISPR_OUTPUT=1\n', ''),
])
def test_output_examples_require_valid_observations_on_both_commits(base_output, head_output) -> None:
    base = execution("base", ExecutionStatus.PASSED)
    head = execution("head", ExecutionStatus.PASSED)
    base.stdout = base_output
    head.stdout = head_output
    assert compare_executions(base, head, mode="output") == Classification.INCONCLUSIVE

