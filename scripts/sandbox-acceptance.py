"""Backward-compatible entry point for the shared credential-free acceptance CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.schemas.verification import GeneratedTest, RepositoryProfile, TestExecution
from app.services.fixture_acceptance import main, run_fixture_acceptance
from app.services.sandbox import DockerSandbox


class _LegacyAcceptanceSandbox(DockerSandbox):
    def execute(
        self,
        checkout: Path,
        commit: str,
        branch: str,
        profile: RepositoryProfile,
        generated_test: GeneratedTest,
    ) -> TestExecution:
        execution = super().execute(checkout, commit, branch, profile, generated_test)
        if execution.status.value not in {"PASSED", "FAILED"}:
            raise RuntimeError(
                f"{execution.status.value}\nstdout:\n{execution.stdout[-4000:]}"
                f"\nstderr:\n{execution.stderr[-1500:]}"
            )
        return execution


def check(language: Literal["python", "node"], root: Path) -> dict[str, str | dict[str, str]]:
    """Retain the original diagnostic helper while sharing the real runner."""
    run = run_fixture_acceptance(language, _LegacyAcceptanceSandbox(180, "1g", 1), root)
    if run.status.value != "FIX_VERIFIED":
        raise RuntimeError(f"Controlled acceptance was not verified: {run.status.value}")
    assert run.repair is not None
    finding = run.findings[0]
    return {
        "base": finding.base_execution.status.value,
        "head": finding.head_execution.status.value,
        "manual_repair": {item.name: item.execution.status.value for item in run.repair.checks},
    }


if __name__ == "__main__":
    raise SystemExit(main())
