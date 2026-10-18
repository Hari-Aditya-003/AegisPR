import subprocess
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("repair", [False, True])
def test_generated_test_rejects_symlinked_parent_without_writing_outside_checkout(
    tmp_path: Path, monkeypatch, repair: bool,
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (checkout / "tests").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))
    profile = RepositoryProfile(languages=["Python"], install_command="pip install .", test_command="pytest -q")
    sandbox = DockerSandbox(5, "128m", 1)

    if repair:
        result = sandbox.verify_repair(checkout, "a" * 40, profile, generated("tests/test_escape.py"))[1].execution
    else:
        result = sandbox.execute(checkout, "a" * 40, "head", profile, generated("tests/test_escape.py"))

    assert result.status.value == "SKIPPED"
    assert not (outside / "test_escape.py").exists()


def test_build_does_not_follow_repository_controlled_dockerfile_symlink(tmp_path: Path, monkeypatch) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    outside = tmp_path / "important.txt"
    outside.write_text("preserve me")
    (checkout / ".aegispr.Dockerfile").symlink_to(outside)
    dockerfiles: list[str] = []

    def fake_run(args, **kwargs):
        if args[:2] == ["docker", "build"]:
            dockerfiles.append(Path(args[args.index("--file") + 1]).read_text())
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    sandbox = DockerSandbox(5, "128m", 1)
    sandbox._build_image(checkout, "python:3.12-slim", "pip install .", "test-image")

    assert outside.read_text() == "preserve me"
    assert (checkout / ".aegispr.Dockerfile").is_symlink()
    assert dockerfiles
    assert dockerfiles[0].index("USER 10001") < dockerfiles[0].index("RUN pip install .")


@pytest.mark.parametrize("command", ["npm run arbitrary", "pytest --override-ini=x", "npx jest unexpected", "pytest -q; id"])
def test_command_policy_rejects_unrecognized_arguments(command: str) -> None:
    assert not DockerSandbox._is_allowed_command(command)


def test_timed_out_runtime_force_removes_named_container(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["docker", "run"]:
            raise subprocess.TimeoutExpired(args, 5, output=b"partial output", stderr=b"partial error")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DockerSandbox(5, "128m", 1)._run_image("test-image", "pytest -q", "a" * 40)

    assert result.status.value == "TIMEOUT"
    run_command = next(args for args in calls if args[:2] == ["docker", "run"])
    name = run_command[run_command.index("--name") + 1]
    assert ["docker", "container", "rm", "--force", name] in calls


def test_runtime_rejects_install_command_injection() -> None:
    assert DockerSandbox._runtime(RepositoryProfile(languages=["Python"], install_command="pip install .\nRUN unsafe")) == (None, None)


@pytest.mark.parametrize("build_number", [1, 2])
def test_repair_build_timeout_is_recorded_and_all_images_are_cleaned(
    tmp_path: Path, monkeypatch, build_number: int,
) -> None:
    calls: list[list[str]] = []
    builds = 0

    def fake_run(args, **kwargs):
        nonlocal builds
        calls.append(args)
        if args[:2] == ["docker", "build"]:
            builds += 1
            if builds == build_number:
                raise subprocess.TimeoutExpired(args, 5, output=b"build output")
        return subprocess.CompletedProcess(args, 0, "passed", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    profile = RepositoryProfile(languages=["Python"], install_command="pip install .", test_command="pytest -q")
    checks = DockerSandbox(5, "128m", 1).verify_repair(
        tmp_path, "a" * 40, profile, generated("tests/test_timeout.py"),
    )

    timeout = next(check.execution for check in checks if check.execution.status.value == "TIMEOUT")
    assert timeout.stdout == "build output"
    assert timeout.environment["phase"] == "build"
    if build_number == 2:
        assert checks[0].execution.status.value == "PASSED"
    built_tags = [args[args.index("--tag") + 1] for args in calls if args[:2] == ["docker", "build"]]
    assert all(["docker", "image", "rm", "--force", tag] in calls for tag in built_tags)


def test_repair_unexpected_baseline_failure_still_cleans_image(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["docker", "run"]:
            raise OSError("Docker daemon unavailable")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    profile = RepositoryProfile(languages=["Python"], install_command="pip install .", test_command="pytest -q")
    with pytest.raises(OSError):
        DockerSandbox(5, "128m", 1).verify_repair(tmp_path, "a" * 40, profile, generated("tests/test_failure.py"))

    build = next(args for args in calls if args[:2] == ["docker", "build"])
    assert ["docker", "image", "rm", "--force", build[build.index("--tag") + 1]] in calls
