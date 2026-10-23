from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.verification.local import (
    LocalVerificationError,
    compare_measurements,
    inspect_committed_change,
)
from app.cli import main


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
