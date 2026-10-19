"""Fixed local Git fixtures executed by the real sandbox, never by an LLM.

Imports neither provider SDKs nor application startup. Only trusted, prewritten
Python/Node source is constructed. This is not an arbitrary-code endpoint.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from app.config import Settings
from app.schemas.verification import (
    ExecutionStatus, Finding, GeneratedTest, Hypothesis, PullRequestSummary,
    RepairResult, RepairStatus, RepositoryProfile, StageState, VerificationRun,
    VerificationStage, VerificationStatus,
)
from app.services.sandbox import DockerSandbox
from app.services.store import VerificationStore
from app.verification.differential import Classification, compare_executions


DISCLAIMER = (
    "Controlled fixture: this is not a real pull request and no model, Nebius inference, "
    "GPU ranking, or AI-generated repair was used. The fixed hypothesis, boundary test, "
    "and manual repair were prewritten. Git commits and Docker execution receipts are "
    "real for this run. Passing these checks does not prove general correctness or security."
)


def _git_environment(home: Path) -> dict[str, str]:
    return {
        "PATH": os.defpath, "HOME": str(home), "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
    }


def _git(repository: Path, home: Path, *args: str, strip: bool = True) -> str:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=AegisPR Controlled Fixture",
         "-c", "user.email=controlled-fixture@example.invalid", "-c", "commit.gpgSign=false",
         "-c", "init.defaultBranch=main", "-C", str(repository), *args],
        env=_git_environment(home), capture_output=True, text=True, timeout=20, check=True,
    )
    return result.stdout.strip() if strip else result.stdout


def _scaffold(language: str, repository: Path) -> tuple[RepositoryProfile, GeneratedTest, str, str, str]:
    if language == "python":
        profile = RepositoryProfile(
            languages=["Python"], test_framework="pytest", package_manager="pip",
            install_command="pip install -r requirements.txt", test_command="pytest -q",
        )
        (repository / "requirements.txt").write_text("pytest==9.1.1\n", encoding="utf-8")
        (repository / "test_existing.py").write_text(
            "from coupon import coupon\ndef test_normal(): assert coupon(20,5)==15\n", encoding="utf-8",
        )
        generated = GeneratedTest(
            id="T1", hypothesis_id="H1", framework="pytest", file_path="test_generated.py",
            test_code="from coupon import coupon\ndef test_floor(): assert coupon(10,20)==0\n",
        )
        return profile, generated, "coupon.py", "def coupon(t,d): return max(0,t-d)\n", "def coupon(t,d): return t-d\n"
    profile = RepositoryProfile(
        languages=["JavaScript"], test_framework="vitest", package_manager="npm",
        install_command="npm install --ignore-scripts", test_command="npm test -- --run",
        build_command="npm run build",
    )
    (repository / "package.json").write_text(json.dumps({
        "name": "aegispr-controlled-fixture", "private": True, "type": "module",
        "scripts": {"test": "vitest", "build": "node -e \"require('node:fs').mkdirSync('dist',{recursive:true})\""},
        "devDependencies": {"vitest": "5.0.3"},
    }), encoding="utf-8")
    (repository / "existing.test.js").write_text(
        "import {test,expect} from 'vitest'; import {coupon} from './coupon.js'; "
        "test('normal',()=>expect(coupon(20,5)).toBe(15));\n", encoding="utf-8",
    )
    generated = GeneratedTest(
        id="T1", hypothesis_id="H1", framework="vitest", file_path="generated.test.js",
        test_code="import {test,expect} from 'vitest'; import {coupon} from './coupon.js'; "
                  "test('floor',()=>expect(coupon(10,20)).toBe(0));\n",
    )
    return profile, generated, "coupon.js", "export const coupon=(t,d)=>Math.max(0,t-d);\n", "export const coupon=(t,d)=>t-d;\n"


def _checkout(repository: Path, home: Path, commit: str, target: Path) -> None:
    # Only fixed filenames from our own local repository; no hooks/remotes/config.
    target.mkdir()
    for name in _git(repository, home, "ls-tree", "--name-only", commit).splitlines():
        (target / name).write_text(_git(repository, home, "show", f"{commit}:{name}", strip=False), encoding="utf-8")


def run_fixture_acceptance(
    language: Literal["python", "node"], sandbox: DockerSandbox, workspace: Path,
) -> VerificationRun:
    """Return actual sandbox receipts for a known, fixed local regression.

    Each invocation owns one temporary directory. The caller saves/exports the
    returned report. Only the invocation's unique temporary tree is removed.
    """
    if language not in {"python", "node"}:
        raise ValueError("Controlled fixture language must be python or node")
    workspace.mkdir(parents=True, exist_ok=True)
    run = VerificationRun(
        pull_request_url=f"controlled-fixture://{language}", evidence_mode="controlled_fixture",
        model_used="controlled-fixture-no-model", status=VerificationStatus.RUNNING, disclaimer=DISCLAIMER,
    )
    started = time.monotonic()
    with TemporaryDirectory(prefix=f"controlled-{language}-{run.id}-", dir=workspace) as temporary:
        root = Path(temporary)
        repository, home, template = root / "repository", root / "git-home", root / "git-template"
        for directory in (repository, home, template):
            directory.mkdir()
        profile, generated, source, good, bad = _scaffold(language, repository)
        run.repository_profile = profile
        run.changed_files = [source]
        run.hypotheses = [Hypothesis(
            id="H1", description="Prewritten hypothesis: a discount exceeding the total must not yield a negative charge.",
            affected_files=[source], test_strategy="Prewritten boundary test: coupon(10,20) must equal zero.",
        )]
        run.generated_tests = [generated]
        run.metrics.files_analyzed = run.metrics.hypotheses_generated = run.metrics.generated_tests = 1
        run.metrics.context_accelerator = "not_used"
        (repository / source).write_text(good, encoding="utf-8")
        _git(repository, home, "init", f"--template={template}")
        _git(repository, home, "add", "--all")
        _git(repository, home, "commit", "-m", "Controlled fixture base: clamp negative coupon totals")
        base_commit = _git(repository, home, "rev-parse", "HEAD")
        (repository / source).write_text(bad, encoding="utf-8")
        _git(repository, home, "add", "--", source)
        _git(repository, home, "commit", "-m", "Controlled fixture head: deliberately remove coupon clamp")
        head_commit = _git(repository, home, "rev-parse", "HEAD")
        run.summary = PullRequestSummary(
            owner="controlled-fixture", repository=f"coupon-{language}", number=0,
            title=f"Controlled {language} fixture — prewritten test and manual repair, no model",
            html_url=run.pull_request_url, clone_url="", base_ref="fixture-base", head_ref="fixture-head",
            base_commit=base_commit, head_commit=head_commit, changed_files=1, additions=1, deletions=1,
        )
        executions = []
        for branch, commit in (("base", base_commit), ("head", head_commit)):
            checkout = root / branch
            _checkout(repository, home, commit, checkout)
            execution = sandbox.execute(checkout, commit, branch, profile, generated)
            executions.append(execution)
            run.stages.append(VerificationStage(
                key=branch, label=f"Controlled {branch} executed",
                state=StageState.COMPLETE if execution.status in {ExecutionStatus.PASSED, ExecutionStatus.FAILED} else StageState.ERROR,
                detail=execution.status.value, timestamp=datetime.now(timezone.utc),
            ))
        classification = compare_executions(*executions)
        finding = Finding(
            hypothesis_id="H1", generated_test_id="T1", classification=classification.value,
            summary="Controlled coupon boundary comparison from actual sandbox receipts", affected_file=source,
            base_execution=executions[0], head_execution=executions[1],
        )
        run.findings = [finding]
        status_by_classification = {
            Classification.REGRESSION: VerificationStatus.REGRESSION_FOUND,
            Classification.PRE_EXISTING: VerificationStatus.PRE_EXISTING_FAILURE,
            Classification.NO_FAILURE_REPRODUCED: VerificationStatus.VERIFIED_WITHIN_SCOPE,
        }
        run.status = status_by_classification.get(classification, VerificationStatus.INCONCLUSIVE)
        if classification == Classification.REGRESSION:
            run.metrics.regressions_found = 1
            repair = root / "manual-repair"
            _checkout(repository, home, head_commit, repair)
            patch = "".join(difflib.unified_diff(
                bad.splitlines(keepends=True), good.splitlines(keepends=True),
                fromfile=f"a/{source}", tofile=f"b/{source}",
            ))
            (repair / source).write_text(good, encoding="utf-8")
            checks = sandbox.verify_repair(repair, head_commit, profile, generated)
            required = {"existing_tests", "generated_tests"}
            if profile.build_command:
                required.add("build")
            if profile.lint_command:
                required.add("lint")
            passed = {check.name for check in checks if check.execution.status == ExecutionStatus.PASSED}
            verified = required.issubset(passed) and all(
                check.execution.status == ExecutionStatus.PASSED
                for check in checks if check.name in required or check.command
            )
            run.repair = RepairResult(
                finding_id=finding.id, status=RepairStatus.VERIFIED if verified else RepairStatus.FAILED,
                patch=patch, summary="Prewritten manual repair restoring the coupon clamp; not model-generated.",
                checks=checks, error=None if verified else "Manual repair did not pass every required check",
            )
            if verified:
                run.status = VerificationStatus.FIX_VERIFIED
        run.metrics.sandbox_duration_ms = sum(item.duration_ms for item in executions)
        if run.repair:
            run.metrics.sandbox_duration_ms += sum(check.execution.duration_ms for check in run.repair.checks)
    run.completed_at = datetime.now(timezone.utc)
    run.metrics.analysis_duration_ms = int((time.monotonic() - started) * 1000)
    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute fixed Docker fixtures without provider credentials or model calls")
    parser.add_argument("--language", choices=("all", "python", "node"), default="all")
    args = parser.parse_args(argv)
    settings = Settings()
    store = VerificationStore(settings.data_path)
    destination = settings.data_path.parent / "judge-evidence"
    destination.mkdir(parents=True, exist_ok=True)
    sandbox = DockerSandbox(settings.sandbox_timeout_seconds, settings.sandbox_memory, settings.sandbox_cpus)
    succeeded = True
    for language in (("python", "node") if args.language == "all" else (args.language,)):
        run = run_fixture_acceptance(language, sandbox, settings.workspace_root)
        store.save(run)
        output = destination / f"{run.id}.json"
        with output.open("x", encoding="utf-8") as stream:
            stream.write(run.model_dump_json(indent=2))
        print(json.dumps({
            "language": language, "run_id": run.id, "status": run.status.value,
            "evidence_mode": run.evidence_mode, "report": str(output),
            "local_report_url": f"http://127.0.0.1:3300/verifications/{run.id}",
            "notice": "Controlled fixture only; prewritten test/manual repair; no model or Nebius inference.",
        }), flush=True)
        succeeded = succeeded and run.status == VerificationStatus.FIX_VERIFIED
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
