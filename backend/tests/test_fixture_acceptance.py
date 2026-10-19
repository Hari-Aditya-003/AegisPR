"""Controlled fixture receipts must never masquerade as model or PR evidence."""
import importlib
import json
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.agents.orchestrator import Orchestrator
from app.config import Settings
from app.schemas.verification import (
    ExecutionStatus, RepairCheck, RepairRequest, VerificationRun, VerificationStatus,
    TestExecution,
)
from app.services.store import VerificationStore


def module():
    return importlib.import_module("app.services.fixture_acceptance")


def sandbox(base="PASSED", head="FAILED", repair="PASSED", missing=None):
    fake = MagicMock()
    receipts = []

    def execute(checkout, commit, branch, profile, generated):
        assert re.fullmatch(r"[0-9a-f]{40}", commit)
        assert (checkout / ("coupon.py" if "Python" in profile.languages else "coupon.js")).is_file()
        assert generated.test_code
        receipts.append((checkout, commit))
        return TestExecution(
            branch=branch, commit=commit, status=base if branch == "base" else head,
            exit_code=0 if branch == "base" else 1, stdout=f"actual {branch} output",
            duration_ms=17, environment={"executor": "mock-docker"},
        )

    def verify(checkout, commit, profile, generated):
        assert generated.test_code
        names = [("existing_tests", profile.test_command), ("generated_tests", profile.test_command),
                 ("build", profile.build_command), ("lint", profile.lint_command)]
        return [RepairCheck(name=name, command=command, execution=TestExecution(
            branch="repair", commit=commit, status=repair if command else "SKIPPED",
            exit_code=0 if repair == "PASSED" and command else None,
            stdout=f"actual {name} output", duration_ms=12,
        )) for name, command in names if name != missing]

    fake.execute.side_effect = execute
    fake.verify_repair.side_effect = verify
    fake.receipts = receipts
    return fake


@pytest.mark.parametrize("language", ["python", "node"])
def test_fixture_records_real_commits_and_honest_manual_repair(language, tmp_path, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "must-not-be-in-git-environment")
    fake = sandbox()
    run = module().run_fixture_acceptance(language, fake, tmp_path)
    assert run.evidence_mode == "controlled_fixture"
    assert run.model_used == "controlled-fixture-no-model"
    assert run.status == VerificationStatus.FIX_VERIFIED
    assert run.metrics.model_calls == run.metrics.input_tokens == run.metrics.output_tokens == 0
    assert run.metrics.accounted_cost_usd == 0
    assert "not a real pull request" in run.disclaimer.lower()
    assert "no model" in run.disclaimer.lower()
    assert "controlled" in run.summary.title.lower()
    assert run.summary.base_commit != run.summary.head_commit
    assert run.findings[0].base_execution.commit == run.summary.base_commit
    assert run.findings[0].head_execution.commit == run.summary.head_commit
    assert run.findings[0].base_execution.stdout == "actual base output"
    assert run.findings[0].head_execution.duration_ms == 17
    assert run.repair.status.value == "VERIFIED"
    assert run.repair.patch.startswith("--- a/coupon.")
    assert "manual" in run.repair.summary.lower()
    assert len(fake.receipts) == 2
    assert fake.receipts[0][0] != fake.receipts[1][0]
    assert all(not path.exists() for path, _ in fake.receipts)
    store = VerificationStore(tmp_path / "results.sqlite3")
    store.save(run)
    assert store.get(run.id) == run


@pytest.mark.parametrize("base,head,expected", [
    ("ERROR", "FAILED", "INCONCLUSIVE"), ("TIMEOUT", "FAILED", "INCONCLUSIVE"),
    ("PASSED", "ERROR", "INCONCLUSIVE"), ("PASSED", "TIMEOUT", "INCONCLUSIVE"),
    ("FAILED", "FAILED", "PRE_EXISTING_FAILURE"),
    ("PASSED", "PASSED", "VERIFIED_WITHIN_SCOPE"),
])
def test_fixture_never_verifies_regression_or_repair_without_differential_evidence(base, head, expected, tmp_path):
    fake = sandbox(base=base, head=head)
    run = module().run_fixture_acceptance("python", fake, tmp_path)
    assert run.status.value == expected
    assert run.repair is None
    fake.verify_repair.assert_not_called()


@pytest.mark.parametrize("repair,missing", [("FAILED", None), ("TIMEOUT", None), ("PASSED", "generated_tests"), ("PASSED", "build")])
def test_fixture_repair_requires_generated_existing_and_configured_build_checks(repair, missing, tmp_path):
    run = module().run_fixture_acceptance("node", sandbox(repair=repair, missing=missing), tmp_path)
    assert run.status == VerificationStatus.REGRESSION_FOUND
    assert run.repair.status.value == "FAILED"


def test_fixture_reruns_have_unique_ids_and_workspaces(tmp_path):
    fake = sandbox()
    first = module().run_fixture_acceptance("python", fake, tmp_path)
    second = module().run_fixture_acceptance("python", fake, tmp_path)
    assert first.id != second.id
    assert fake.receipts[0][0] != fake.receipts[2][0]


def test_fixture_rejects_arbitrary_language_before_creating_workspace(tmp_path):
    with pytest.raises(ValueError, match="python or node"):
        module().run_fixture_acceptance("shell; curl bad", sandbox(), tmp_path / "unused")
    assert not (tmp_path / "unused").exists()


def test_git_environment_excludes_credentials_and_external_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hooksPath")
    env = module()._git_environment(tmp_path)
    assert env["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert "NEBIUS_API_KEY" not in env
    assert "GIT_CONFIG_COUNT" not in env


def test_controlled_fixture_cannot_trigger_model_repair_even_with_credentials(tmp_path):
    settings = Settings(data_path=tmp_path / "data.sqlite3", enable_sandbox=True, nebius_api_key="test-key")
    store = VerificationStore(settings.data_path)
    run = VerificationRun(pull_request_url="controlled-fixture://python", evidence_mode="controlled_fixture", status="REGRESSION_FOUND")
    store.save(run)
    with pytest.raises(ValueError, match="[Cc]ontrolled fixture"):
        Orchestrator(settings, store).create_repair(run.id, RepairRequest())


def test_cli_language_option_persists_complete_report_and_prints_id_only(tmp_path, monkeypatch, capsys):
    service = module()
    settings = Settings(data_path=tmp_path / "data.sqlite3", workspace_root=tmp_path / "work")
    monkeypatch.setattr(service, "Settings", lambda: settings)
    fake = sandbox()
    monkeypatch.setattr(service, "DockerSandbox", lambda *args: fake)
    assert service.main(["--language", "python"]) == 0
    runs = VerificationStore(settings.data_path).list()
    assert len(runs) == 1
    report = tmp_path / "judge-evidence" / f"{runs[0].id}.json"
    assert json.loads(report.read_text())["findings"][0]["head_execution"]["stdout"] == "actual head output"
    assert runs[0].id in capsys.readouterr().out


def test_legacy_pr_reports_default_to_pr_evidence():
    assert VerificationRun(pull_request_url="https://github.com/acme/store/pull/1").evidence_mode == "pr_review"
