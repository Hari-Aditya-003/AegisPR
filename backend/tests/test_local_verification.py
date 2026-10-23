from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.verification.local import (
    LocalVerificationError,
    compare_measurements,
    execute_committed_suites,
    inspect_committed_change,
)
from app.cli import main
from app.schemas.verification import ExecutionStatus, TestExecution


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def initialized_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "project"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "AegisPR fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "api.py").write_text(
        "@login_required\ndef public_total(amount, discount=0):\n"
        "    return amount - discount\n", encoding="utf-8",
    )
    git(repo, "add", "api.py")
    git(repo, "commit", "-qm", "baseline")
    return repo, git(repo, "rev-parse", "HEAD")


def test_local_scan_reports_public_api_and_removed_auth_guard(tmp_path: Path) -> None:
    repo, base = initialized_repo(tmp_path)
    (repo / "api.py").write_text(
        "def public_total(amount, discount, user):\n"
        "    return amount - discount\n", encoding="utf-8",
    )
    git(repo, "add", "api.py")
    git(repo, "commit", "-qm", "change public API and guard")

    report = inspect_committed_change(repo, base)

    assert report.base_commit == base
    assert report.head_commit == git(repo, "rev-parse", "HEAD")
    assert report.changed_files == ["api.py"]
    assert any("public_total" in risk for risk in report.api_risks)
    assert any("auth" in warning.lower() for warning in report.security_warnings)
    assert report.scope == "committed changes only; static review, not proof of safety"


def test_local_scan_does_not_run_uncommitted_code(tmp_path: Path) -> None:
    repo, base = initialized_repo(tmp_path)
    (repo / "api.py").write_text("raise RuntimeError('uncommitted')\n", encoding="utf-8")
    with pytest.raises(LocalVerificationError, match="uncommitted"):
        inspect_committed_change(repo, base)


def test_local_scan_rejects_option_shaped_git_ref(tmp_path: Path) -> None:
    repo, _ = initialized_repo(tmp_path)
    with pytest.raises(LocalVerificationError, match="base reference"):
        inspect_committed_change(repo, "--upload-pack=evil")


def test_local_scan_does_not_call_a_changed_default_a_confirmed_break(tmp_path: Path) -> None:
    repo, base = initialized_repo(tmp_path)
    (repo / "api.py").write_text(
        "@login_required\ndef public_total(amount, discount=1):\n"
        "    return amount - discount\n", encoding="utf-8",
    )
    git(repo, "add", "api.py")
    git(repo, "commit", "-qm", "change default")
    report = inspect_committed_change(repo, base)
    assert any("review compatibility" in risk.lower() for risk in report.api_risks)
    assert report.security_warnings == []


def test_cli_json_reports_scope_and_exits_nonzero_for_review_risk(tmp_path: Path, capsys) -> None:
    repo, base = initialized_repo(tmp_path)
    (repo / "api.py").write_text("def public_total(amount):\n    return amount\n", encoding="utf-8")
    git(repo, "add", "api.py")
    git(repo, "commit", "-qm", "remove guard")

    assert main(["verify", "--repo", str(repo), "--base", base, "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["base_commit"] == base
    assert payload["security_warnings"]
    assert payload["model_calls"] == 0


def test_performance_comparison_requires_repeated_stable_samples() -> None:
    result = compare_measurements(
        [100, 110, 90], [150, 160, 155],
        [100_000_000] * 3, [145_000_000] * 3, threshold=0.30,
    )
    assert result["time_status"] == "possible_regression"
    assert result["memory_status"] == "possible_regression"
    assert result["base_median_ms"] == 100
    assert result["head_median_ms"] == 155


def test_performance_comparison_is_inconclusive_without_three_valid_samples() -> None:
    result = compare_measurements([100, 102], [150, 151], [], [], threshold=0.30)
    assert result["time_status"] == "inconclusive"
    assert result["memory_status"] == "inconclusive"


def test_committed_suite_comparison_requires_all_three_head_failures(tmp_path: Path) -> None:
    repo, _ = initialized_repo(tmp_path)
    (repo / "requirements.txt").write_text("pytest==8.4.0\n", encoding="utf-8")
    (repo / "test_api.py").write_text("def test_api(): assert True\n", encoding="utf-8")
    git(repo, "add", "requirements.txt", "test_api.py")
    git(repo, "commit", "-qm", "add tests")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "api.py").write_text("def public_total(amount): return amount\n", encoding="utf-8")
    git(repo, "add", "api.py")
    git(repo, "commit", "-qm", "change implementation")
    head = git(repo, "rev-parse", "HEAD")

    class FakeSandbox:
        def __init__(self):
            self.paths = []

        def run_existing_suite(self, checkout, commit, branch, profile, repetitions=3):
            self.paths.append(checkout)
            status = ExecutionStatus.PASSED if branch == "base" else ExecutionStatus.FAILED
            return [TestExecution(branch=branch, commit=commit, status=status,
                                  duration_ms=100, environment={"peak_memory_bytes": 100})
                    for _ in range(repetitions)]

    sandbox = FakeSandbox()
    report = execute_committed_suites(repo, base, head, sandbox=sandbox, repetitions=3)
    assert report["status"] == "reproducible_regression"
    assert report["test_command"] == "pytest -q"
    assert report["performance"]["time_status"] == "inconclusive"
    assert all(not path.exists() for path in sandbox.paths)


def test_mixed_head_outcomes_are_inconclusive_not_a_confirmed_regression() -> None:
    from app.verification.local import summarize_suite_outcomes

    assert summarize_suite_outcomes(["PASSED"] * 3, ["FAILED", "PASSED", "FAILED"]) == "inconclusive"


def test_local_scan_flags_changed_exported_js_signature_and_removed_auth_call(tmp_path: Path) -> None:
    repo, base = initialized_repo(tmp_path)
    (repo / "api.ts").write_text(
        "export function getAccount(id: string) {\n"
        "  requireAuth();\n  return id;\n}\n", encoding="utf-8",
    )
    git(repo, "add", "api.ts")
    git(repo, "commit", "-qm", "public API baseline")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "api.ts").write_text(
        "export function getAccount(id: string, role: string) {\n"
        "  return id;\n}\n", encoding="utf-8",
    )
    git(repo, "add", "api.ts")
    git(repo, "commit", "-qm", "change exported API")

    report = inspect_committed_change(repo, base)
    assert any("getAccount" in risk for risk in report.api_risks)
    assert any("auth" in warning.lower() for warning in report.security_warnings)


def test_cli_reports_docker_runtime_failure_without_traceback(tmp_path: Path, capsys) -> None:
    repo, base = initialized_repo(tmp_path)
    with patch("app.cli.execute_committed_suites", side_effect=OSError("docker unavailable")):
        assert main(["verify", "--repo", str(repo), "--base", base, "--docker-tests"]) == 2
    output = capsys.readouterr()
    assert "could not verify" in output.err.lower()
    assert "Traceback" not in output.err


def test_cli_docker_output_does_not_claim_no_code_execution(tmp_path: Path, capsys) -> None:
    repo, base = initialized_repo(tmp_path)
    docker_result = {
        "status": "no_failure_observed", "test_command": "pytest -q",
        "performance": {"time_status": "inconclusive", "memory_status": "inconclusive"},
    }
    with patch("app.cli.execute_committed_suites", return_value=docker_result):
        assert main(["verify", "--repo", str(repo), "--base", base, "--docker-tests"]) == 0
    assert "No repository code execution" not in capsys.readouterr().out
