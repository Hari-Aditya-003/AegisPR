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

