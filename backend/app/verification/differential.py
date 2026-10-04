from __future__ import annotations

from enum import Enum

from app.schemas.verification import ExecutionStatus, TestExecution


class Classification(str, Enum):
    REGRESSION = "REGRESSION"
    PRE_EXISTING = "PRE_EXISTING_FAILURE"
    NO_FAILURE_REPRODUCED = "NO_FAILURE_REPRODUCED"
    POSSIBLE_IMPROVEMENT = "POSSIBLE_IMPROVEMENT"
    INCONCLUSIVE = "INCONCLUSIVE"


def compare_executions(base: TestExecution, head: TestExecution) -> Classification:
    if base.branch != "base" or head.branch != "head":
        raise ValueError("Differential comparison requires base and head executions")
    pair = (base.status, head.status)
    if pair == (ExecutionStatus.PASSED, ExecutionStatus.FAILED):
        return Classification.REGRESSION
    if pair == (ExecutionStatus.FAILED, ExecutionStatus.FAILED):
        return Classification.PRE_EXISTING
    if pair == (ExecutionStatus.PASSED, ExecutionStatus.PASSED):
        return Classification.NO_FAILURE_REPRODUCED
    if pair == (ExecutionStatus.FAILED, ExecutionStatus.PASSED):
        return Classification.POSSIBLE_IMPROVEMENT
    return Classification.INCONCLUSIVE

