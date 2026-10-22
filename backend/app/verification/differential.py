from __future__ import annotations

from enum import Enum
import json

from app.schemas.verification import ExecutionStatus, TestExecution


class Classification(str, Enum):
    REGRESSION = "REGRESSION"
    PRE_EXISTING = "PRE_EXISTING_FAILURE"
    NO_FAILURE_REPRODUCED = "NO_FAILURE_REPRODUCED"
    POSSIBLE_IMPROVEMENT = "POSSIBLE_IMPROVEMENT"
    INCONCLUSIVE = "INCONCLUSIVE"
    BEHAVIOR_CHANGE = "BEHAVIOR_CHANGE"


def output_observations(execution: TestExecution) -> tuple[str, ...] | None:
    observations: list[str] = []
    for line in execution.stdout.splitlines():
        line = line.lstrip()
        if not line.startswith("AEGISPR_OUTPUT="):
            continue
        try:
            value = json.loads(line.removeprefix("AEGISPR_OUTPUT="))
        except ValueError:
            return None
        try:
            observations.append(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False))
        except ValueError:
            return None
        if len(observations) > 100:
            return None
    return tuple(observations) if observations else None


def compare_executions(base: TestExecution, head: TestExecution, *, mode: str = "assertion") -> Classification:
    if base.branch != "base" or head.branch != "head":
        raise ValueError("Differential comparison requires base and head executions")
    if mode == "output":
        if base.status != ExecutionStatus.PASSED or head.status != ExecutionStatus.PASSED:
            return Classification.INCONCLUSIVE
        before, after = output_observations(base), output_observations(head)
        if before is None or after is None or len(before) != len(after):
            return Classification.INCONCLUSIVE
        return Classification.BEHAVIOR_CHANGE if before != after else Classification.NO_FAILURE_REPRODUCED
    if mode != "assertion":
        raise ValueError("Unknown generated test mode")
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

