import subprocess
from pathlib import Path

from app.schemas.verification import GeneratedTest, RepositoryProfile
from app.services.sandbox import DockerSandbox


def generated(path: str = "") -> GeneratedTest:
    return GeneratedTest(
        id="AEG-1", hypothesis_id="H1", file_path=path,
        framework="pytest", test_code="def test_x(): assert True", test_command="pytest -q",
    )


def test_skips_missing_and_unsafe_generated_test_paths(tmp_path: Path) -> None:
    sandbox = DockerSandbox(5, "128m", 1)
    profile = RepositoryProfile(languages=["Python"], test_command="pytest -q", install_command="pip install .")
    missing = generated("")
    missing.test_code = ""
    assert sandbox.execute(tmp_path, "a" * 40, "base", profile, missing).status.value == "SKIPPED"
    assert sandbox.execute(tmp_path, "a" * 40, "base", profile, generated("../escape.py")).status.value == "SKIPPED"
    assert sandbox.execute(tmp_path, "a" * 40, "base", profile, generated("package.json")).status.value == "SKIPPED"


def test_rejects_model_command_that_only_matches_an_allowed_prefix(tmp_path: Path) -> None:
    sandbox = DockerSandbox(5, "128m", 1)
    profile = RepositoryProfile(
        languages=["Python"], test_command="pytest -q", install_command="pip install ."
    )
    untrusted = generated("tests/test_generated.py")
    untrusted.test_command = "pytest -q; touch /tmp/escaped"

    result = sandbox.execute(tmp_path, "a" * 40, "head", profile, untrusted)

    assert result.status.value == "SKIPPED"
    assert "rejected" in result.stderr


def test_runtime_selection_is_narrow() -> None:
    assert DockerSandbox._runtime(RepositoryProfile(languages=["Python"], install_command="pip install ."))[0] == "python:3.12-slim"
    assert DockerSandbox._runtime(RepositoryProfile(languages=["TypeScript"], install_command="npm ci"))[0] == "node:22-bookworm-slim"
    assert DockerSandbox._runtime(RepositoryProfile(languages=["Rust"])) == (None, None)


def test_repair_commands_record_optional_checks_separately() -> None:
    profile = RepositoryProfile(
        test_command="pytest -q",
        build_command="npm run build",
        lint_command=None,
    )
    assert DockerSandbox._repair_commands(profile) == [
        ("existing_tests", "pytest -q"),
        ("build", "npm run build"),
        ("lint", None),
    ]


def test_repair_verification_runs_existing_generated_and_configured_checks(
    tmp_path: Path, monkeypatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="passed", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    sandbox = DockerSandbox(5, "128m", 1)
    profile = RepositoryProfile(
        languages=["Python"],
        install_command="pip install .",
        test_command="pytest -q",
        build_command="python -m pytest",
    )

    checks = sandbox.verify_repair(tmp_path, "b" * 40, profile, generated("tests/test_fix.py"))

    assert [check.name for check in checks] == [
        "existing_tests", "generated_tests", "build", "lint",
    ]
    assert [check.execution.status.value for check in checks] == [
        "PASSED", "PASSED", "PASSED", "SKIPPED",
    ]
    assert (tmp_path / "tests/test_fix.py").read_text() == "def test_x(): assert True"
    assert sum(args[:2] == ["docker", "build"] for args in calls) == 2
    assert sum(args[:2] == ["docker", "run"] for args in calls) == 3
