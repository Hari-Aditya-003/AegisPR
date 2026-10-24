import subprocess
import sys
import runpy
import shlex
from pathlib import Path
from pathlib import PurePosixPath
from types import SimpleNamespace

import pytest

from app.schemas.verification import GeneratedTest, RepositoryProfile
from app.services.sandbox import DockerSandbox


def mock_processes(monkeypatch, fake_run) -> None:
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(DockerSandbox, "_run_bounded", staticmethod(fake_run))


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


def test_output_examples_disable_pytest_capture_for_json_observations() -> None:
    profile = RepositoryProfile(languages=["Python"], test_framework="pytest", test_command="pytest -q")
    command = DockerSandbox._generated_command(profile, PurePosixPath("tests/test_behavior.py"), mode="output")
    assert command == "python -m pytest -q -s -- tests/test_behavior.py"


def test_output_example_without_collected_pytest_case_runs_as_script() -> None:
    profile = RepositoryProfile(languages=["Python"], test_framework="pytest", test_command="pytest -q")
    code = "from coupon import apply_coupon; print('AEGISPR_OUTPUT=' + str(apply_coupon(5, 8)))"
    command = DockerSandbox._generated_command(
        profile, PurePosixPath("tests/test_coupon_edge.py"), mode="output", code=code,
    )
    parts = shlex.split(command)
    assert parts[:2] == ["python", "-c"]
    assert "runpy.run_path('tests/test_coupon_edge.py'" in parts[2]


def test_output_example_with_pytest_case_retains_collection() -> None:
    profile = RepositoryProfile(languages=["Python"], test_framework="pytest", test_command="pytest -q")
    command = DockerSandbox._generated_command(
        profile, PurePosixPath("tests/test_coupon_edge.py"), mode="output",
        code="def test_boundary():\n    print('AEGISPR_OUTPUT=0')\n",
    )
    assert command == "python -m pytest -q -s -- tests/test_coupon_edge.py"


def test_existing_suite_reuses_one_image_for_three_isolated_measurements(tmp_path: Path, monkeypatch) -> None:
    calls = {"build": 0, "run": 0, "removed": []}
    sandbox = DockerSandbox(5, "128m", 1)
    profile = RepositoryProfile(languages=["Python"], install_command="pip install .", test_command="pytest -q")

    def build(*args):
        calls["build"] += 1
        return subprocess.CompletedProcess([], 0, "", "")

    def run(*args, **kwargs):
        calls["run"] += 1
        assert kwargs["capture_memory"] is True
        return DockerSandbox._result("base", "a" * 40, "PASSED", 0, "ok", "", 0)

    monkeypatch.setattr(sandbox, "_build_image", build)
    monkeypatch.setattr(sandbox, "_run_image", run)
    monkeypatch.setattr(sandbox, "_remove_image", lambda tag: calls["removed"].append(tag))

    executions = sandbox.run_existing_suite(tmp_path, "a" * 40, "base", profile, repetitions=3)

    assert len(executions) == 3
    assert calls["build"] == 1
    assert calls["run"] == 3
    assert len(calls["removed"]) == 1


def test_existing_suite_rejects_unapproved_command_before_build(tmp_path: Path, monkeypatch) -> None:
    sandbox = DockerSandbox(5, "128m", 1)
    monkeypatch.setattr(sandbox, "_build_image", lambda *args: pytest.fail("must not build"))
    profile = RepositoryProfile(languages=["Python"], install_command="pip install .", test_command="pytest -q; id")
    result = sandbox.run_existing_suite(tmp_path, "a" * 40, "head", profile)
    assert len(result) == 1
    assert result[0].status.value == "SKIPPED"


def test_memory_marker_is_recorded_without_changing_test_status(monkeypatch) -> None:
    seen = []

    def fake_run(args, **kwargs):
        seen.append(args)
        return subprocess.CompletedProcess(args, 0, "ok\nAEGISPR_MEMORY_PEAK_BYTES=123456\n", "")

    mock_processes(monkeypatch, fake_run)
    execution = DockerSandbox(5, "128m", 1)._run_image(
        "test-image", "pytest -q", "a" * 40, branch="base", capture_memory=True,
    )
    assert execution.status.value == "PASSED"
    assert execution.environment["peak_memory_bytes"] == 123456
    assert "AEGISPR_MEMORY_PEAK_BYTES" not in execution.stdout
    assert "/sys/fs/cgroup/memory.peak" in next(args for args in seen if args[:2] == ["docker", "run"])[-1]


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

    mock_processes(monkeypatch, fake_run)
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
    mock_processes(monkeypatch, lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))
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

    mock_processes(monkeypatch, fake_run)
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

    mock_processes(monkeypatch, fake_run)
    result = DockerSandbox(5, "128m", 1)._run_image("test-image", "pytest -q", "a" * 40)

    assert result.status.value == "TIMEOUT"
    assert result.environment["command"] == "pytest -q"
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

    mock_processes(monkeypatch, fake_run)
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

    mock_processes(monkeypatch, fake_run)
    profile = RepositoryProfile(languages=["Python"], install_command="pip install .", test_command="pytest -q")
    with pytest.raises(OSError):
        DockerSandbox(5, "128m", 1).verify_repair(tmp_path, "a" * 40, profile, generated("tests/test_failure.py"))

    build = next(args for args in calls if args[:2] == ["docker", "build"])
    assert ["docker", "image", "rm", "--force", build[build.index("--tag") + 1]] in calls


def test_generated_python_run_targets_the_exact_file(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []
    mock_processes(monkeypatch, lambda args, **kwargs: (calls.append(args) or subprocess.CompletedProcess(args, 0, "1 passed", "")))
    profile = RepositoryProfile(languages=["Python"], install_command="pip install .", test_command="pytest -q")
    result = DockerSandbox(5, "128m", 1).execute(tmp_path, "a" * 40, "base", profile, generated("tests/helper.py"))
    command = next(args for args in calls if args[:2] == ["docker", "run"])[-1]
    assert command.endswith("; python -m pytest -q -- tests/helper.py")
    assert result.environment["generated_test_path"] == "tests/helper.py"


def test_repository_dockerignore_cannot_hide_generated_test(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".dockerignore").write_text("tests/\n")
    calls = []
    mock_processes(monkeypatch, lambda args, **kwargs: (calls.append(args) or subprocess.CompletedProcess(args, 0, "other tests passed", "")))
    profile = RepositoryProfile(languages=["Python"], install_command="pip install .", test_command="pytest -q")
    result = DockerSandbox(5, "128m", 1).execute(tmp_path, "a" * 40, "head", profile, generated("tests/test_generated.py"))
    assert result.status.value == "SKIPPED"
    assert "dockerignore" in result.stderr
    assert not calls


def test_unknown_node_test_script_cannot_claim_generated_test_execution(tmp_path: Path, monkeypatch) -> None:
    mock_processes(monkeypatch, lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "nothing ran", ""))
    profile = RepositoryProfile(languages=["JavaScript"], install_command="npm ci", test_command="npm test")
    test = generated("tests/generated.test.js")
    test.framework = "custom"
    test.test_command = "npm test"
    result = DockerSandbox(5, "128m", 1).execute(tmp_path, "a" * 40, "head", profile, test)
    assert result.status.value == "SKIPPED"
    assert "runner" in result.stderr


def test_build_workspace_is_owned_by_unprivileged_installer(tmp_path: Path, monkeypatch) -> None:
    instructions = []

    def fake_run(args, **kwargs):
        instructions.append(Path(args[args.index("--file") + 1]).read_text())
        return subprocess.CompletedProcess(args, 0, "", "")

    mock_processes(monkeypatch, fake_run)
    DockerSandbox(5, "128m", 1)._build_image(tmp_path, "node:22-bookworm-slim", "npm ci --ignore-scripts", "test-image")
    assert "RUN mkdir -p /workspace && chown 10001:10001 /workspace" in instructions[0]


@pytest.mark.parametrize(
    ("install", "manifest_files", "early_copy"),
    [
        ("npm ci --ignore-scripts", {"package.json": '{"dependencies": {}}', "package-lock.json": '{"lockfileVersion": 3}'}, "COPY --chown=10001:10001 package.json package-lock.json ./"),
        ("pip install -r requirements.txt", {"requirements.txt": "pytest==8.4.2\n"}, "COPY --chown=10001:10001 requirements.txt ./"),
    ],
)
def test_safe_dependency_manifest_is_installed_before_source_copy(
    tmp_path: Path, monkeypatch, install: str, manifest_files: dict[str, str], early_copy: str,
) -> None:
    for name, content in manifest_files.items():
        (tmp_path / name).write_text(content)
    instructions = []

    def fake_build(args, **kwargs):
        instructions.append(Path(args[args.index("--file") + 1]).read_text())
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(DockerSandbox, "_run_bounded", staticmethod(fake_build))
    base = "node:22-bookworm-slim" if install.startswith("npm") else "python:3.12-slim"
    DockerSandbox(5, "128m", 1)._build_image(tmp_path, base, install, "test-image")
    dockerfile = instructions[0]
    assert dockerfile.index(early_copy) < dockerfile.index(f"RUN {install}")
    assert dockerfile.index(f"RUN {install}") < dockerfile.index("COPY --chown=10001:10001 . .")


@pytest.mark.parametrize("unsafe", [".npmrc", "node_modules", "workspace"])
def test_node_dependency_cache_falls_back_when_layout_needs_full_source(
    tmp_path: Path, monkeypatch, unsafe: str,
) -> None:
    (tmp_path / "package.json").write_text('{"workspaces": ["packages/*"]}' if unsafe == "workspace" else "{}")
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3}')
    if unsafe != "workspace":
        path = tmp_path / unsafe
        path.mkdir() if unsafe == "node_modules" else path.write_text("registry=https://example.com")
    instructions = []

    def fake_build(args, **kwargs):
        instructions.append(Path(args[args.index("--file") + 1]).read_text())
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(DockerSandbox, "_run_bounded", staticmethod(fake_build))
    DockerSandbox(5, "128m", 1)._build_image(tmp_path, "node:22-bookworm-slim", "npm ci --ignore-scripts", "test-image")
    dockerfile = instructions[0]
    assert dockerfile.index("COPY --chown=10001:10001 . .") < dockerfile.index("RUN npm ci --ignore-scripts")


@pytest.mark.parametrize("requirements", ["-r shared.txt\n", "-e .\n", "package @ file:///tmp/package.whl\n"])
def test_python_dependency_cache_falls_back_for_repository_dependent_install(
    tmp_path: Path, requirements: str,
) -> None:
    (tmp_path / "requirements.txt").write_text(requirements)
    assert DockerSandbox._cacheable_dependency_copy(tmp_path, "pip install -r requirements.txt") is None


def test_dependency_cache_rejects_symlinked_manifest(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-requirements.txt"
    outside.write_text("pytest==8.4.2\n")
    (tmp_path / "requirements.txt").symlink_to(outside)
    assert DockerSandbox._cacheable_dependency_copy(tmp_path, "pip install -r requirements.txt") is None


def test_dependency_cache_rejects_malformed_node_dependency_sections(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"dependencies": ["unexpected"]}')
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3}')
    assert DockerSandbox._cacheable_dependency_copy(tmp_path, "npm ci --ignore-scripts") is None


def test_runtime_uses_bounded_ephemeral_workspace_for_build_outputs(monkeypatch) -> None:
    calls = []
    mock_processes(monkeypatch, lambda args, **kwargs: (calls.append(args) or subprocess.CompletedProcess(args, 0, "", "")))
    DockerSandbox(5, "128m", 1)._run_image("image", "npm run build", "a" * 40)
    command = calls[0]
    assert "--read-only" in command
    assert "--tmpfs=/run/aegis:rw,exec,nosuid,nodev,size=512m,uid=10001,gid=10001" in command
    assert "--tmpfs=/tmp:rw,noexec,nosuid,size=256m" in command
    assert not any(argument.startswith("--volume") or argument == "-v" for argument in command)
    assert "--network=none" in command


def test_generated_paths_cannot_be_interpreted_as_runner_options() -> None:
    assert not DockerSandbox._is_safe_test_path(PurePosixPath("--config=tests/evil.test.js"))


@pytest.mark.parametrize("exit_code", [125, 126, 127])
def test_runtime_setup_failure_is_not_reported_as_a_test_failure(monkeypatch, exit_code: int) -> None:
    calls = []
    mock_processes(monkeypatch, lambda args, **kwargs: (calls.append(args) or subprocess.CompletedProcess(args, exit_code, "", "workspace unavailable")))
    result = DockerSandbox(5, "128m", 1)._run_image("image", "npm run build", "a" * 40)
    assert result.status.value == "ERROR"
    assert "|| exit 125" in calls[0][-1]


@pytest.mark.parametrize("generated_command", [None, "python -m pytest -q -- tests/test_generated.py"])
def test_runtime_records_actual_command_in_execution_evidence(monkeypatch, generated_command) -> None:
    mock_processes(monkeypatch, lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "passed", ""))
    execution = DockerSandbox(5, "128m", 1)._run_image(
        "image", "pytest -q", "a" * 40, generated_command=generated_command,
    )
    assert execution.environment["command"] == (generated_command or "pytest -q")


def test_process_output_has_a_hard_combined_limit_and_retains_only_a_tail() -> None:
    result = DockerSandbox._run_bounded([sys.executable, "-c", "import os; os.write(1,b'x'*2000000)"], timeout=5)
    assert result.returncode == 125
    assert len(result.stdout.encode()) <= 20_000
    assert "output limit" in result.stderr


def test_process_timeout_retains_bounded_partial_output() -> None:
    with pytest.raises(subprocess.TimeoutExpired) as error:
        DockerSandbox._run_bounded([sys.executable, "-c", "import time; print('partial',flush=True); time.sleep(10)"], timeout=1)
    assert b"partial" in error.value.stdout


@pytest.mark.parametrize("base_image", ["node:22-bookworm-slim", "python:3.12-slim"])
def test_trusted_node_installer_is_pinned_before_repository_is_loaded(
    tmp_path: Path, monkeypatch, base_image: str,
) -> None:
    instructions = []

    def fake_build(args, **kwargs):
        instructions.append(Path(args[args.index("--file") + 1]).read_text())
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(DockerSandbox, "_run_bounded", staticmethod(fake_build))
    DockerSandbox(5, "128m", 1)._build_image(tmp_path, base_image, "npm ci --ignore-scripts", "test-image")
    dockerfile = instructions[0]
    pin = "RUN npm install --global --ignore-scripts npm@12.2.0"
    if base_image.startswith("node:"):
        assert pin in dockerfile
        assert dockerfile.index(pin) < dockerfile.index("COPY --chown")
        assert dockerfile.index(pin) < dockerfile.index("USER 10001")
    else:
        assert pin not in dockerfile


def test_acceptance_failure_preserves_install_error_from_build_stdout(tmp_path: Path, monkeypatch) -> None:
    acceptance = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/sandbox-acceptance.py"))
    monkeypatch.setattr(DockerSandbox, "execute", lambda *args: SimpleNamespace(
        status=SimpleNamespace(value="ERROR"), stdout="npm error: edgesOut", stderr="docker build failed",
    ))
    with pytest.raises(RuntimeError, match="edgesOut"):
        acceptance["check"]("node", tmp_path)
