from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path, PurePosixPath
from uuid import uuid4

from app.schemas.verification import (
    ExecutionStatus,
    GeneratedTest,
    RepairCheck,
    RepositoryProfile,
    TestExecution,
)


class DockerSandbox:
    ALLOWED_COMMANDS = frozenset({
        "npm test", "npm test -- --run", "npm test -- --runInBand",
        "npm run build", "npm run lint", "npx vitest run", "npx jest --runInBand",
        "pytest", "pytest -q", "python -m pytest",
    })

    def __init__(self, timeout_seconds: int, memory: str, cpus: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.memory = memory
        self.cpus = cpus

    def execute(
        self,
        checkout: Path,
        commit: str,
        branch: str,
        profile: RepositoryProfile,
        generated_test: GeneratedTest,
    ) -> TestExecution:
        if generated_test.test_command and generated_test.test_command != profile.test_command:
            return self._skipped(branch, commit, "Model-provided test command was rejected")
        command = profile.test_command
        if not command or not self._is_allowed_command(command):
            return self._skipped(branch, commit, "No supported test command was detected")
        if not generated_test.file_path or not generated_test.test_code:
            return self._skipped(branch, commit, "Nemotron test generation was unavailable")
        relative = PurePosixPath(generated_test.file_path)
        if not self._is_safe_test_path(relative):
            return self._skipped(branch, commit, "Generated test path was rejected")
        base_image, install = self._runtime(profile)
        if not base_image or not install:
            return self._skipped(branch, commit, "Unsupported project runtime")
        if not self._write_generated_test(checkout, relative, generated_test.test_code):
            return self._skipped(branch, commit, "Generated test path was rejected or already exists")
        tag = f"aegispr-run-{commit[:12]}-{uuid4().hex[:10]}"
        started = time.monotonic()
        try:
            build = self._build_image(checkout, base_image, install, tag)
            if build.returncode != 0:
                return self._result(branch, commit, ExecutionStatus.ERROR, build.returncode, build.stdout, build.stderr, started)
            return self._run_image(tag, command, commit, branch=branch)
        except subprocess.TimeoutExpired as exc:
            return self._result(branch, commit, ExecutionStatus.TIMEOUT, None, exc.stdout or "", exc.stderr or "", started)
        finally:
            self._remove_image(tag)

    def verify_repair(
        self,
        checkout: Path,
        commit: str,
        profile: RepositoryProfile,
        generated_test: GeneratedTest,
    ) -> list[RepairCheck]:
        base_image, install = self._runtime(profile)
        commands = self._repair_commands(profile)
        if not base_image or not install:
            checks = [
                RepairCheck(
                    name=name,
                    command=command,
                    execution=self._skipped("repair", commit, "Unsupported project runtime"),
                )
                for name, command in commands
            ]
            checks.insert(
                1,
                RepairCheck(
                    name="generated_tests",
                    command=profile.test_command,
                    execution=self._skipped("repair", commit, "Unsupported project runtime"),
                ),
            )
            return checks

        suffix = uuid4().hex[:10]
        baseline_tag = f"aegispr-repair-{commit[:12]}-{suffix}-baseline"
        baseline_build = self._build_image(checkout, base_image, install, baseline_tag)
        checks = [
            RepairCheck(
                name=name,
                command=command,
                execution=(
                    self._run_image(baseline_tag, command, commit)
                    if baseline_build.returncode == 0 and command
                    else self._skipped("repair", commit, "No supported command was detected")
                    if not command
                    else self._build_error(commit, baseline_build)
                ),
            )
            for name, command in commands
        ]

        command_rejected = bool(
            generated_test.test_command and generated_test.test_command != profile.test_command
        )
        generated_command = None if command_rejected else profile.test_command
        generated_execution = self._skipped(
            "repair",
            commit,
            "Model-provided test command was rejected"
            if command_rejected
            else "Generated test path was rejected",
        )
        relative = PurePosixPath(generated_test.file_path)
        safe_path = (
            generated_test.file_path
            and generated_test.test_code
            and self._is_safe_test_path(relative)
        )
        generated_tag = f"aegispr-repair-{commit[:12]}-{suffix}-generated"
        try:
            if safe_path and generated_command:
                if self._write_generated_test(checkout, relative, generated_test.test_code):
                    generated_build = self._build_image(checkout, base_image, install, generated_tag)
                    generated_execution = (
                        self._run_image(generated_tag, generated_command, commit)
                        if generated_build.returncode == 0
                        else self._build_error(commit, generated_build)
                    )
            elif safe_path:
                generated_execution = self._skipped(
                    "repair", commit, "No supported test command was detected"
                )
        finally:
            self._remove_image(baseline_tag)
            self._remove_image(generated_tag)
        checks.insert(
            1,
            RepairCheck(
                name="generated_tests",
                command=generated_command,
                execution=generated_execution,
            ),
        )
        return checks

    @staticmethod
    def _repair_commands(profile: RepositoryProfile) -> list[tuple[str, str | None]]:
        return [
            ("existing_tests", profile.test_command),
            ("build", profile.build_command),
            ("lint", profile.lint_command),
        ]

    def _build_image(
        self, checkout: Path, base_image: str, install: str, tag: str
    ) -> subprocess.CompletedProcess[str]:
        # Build instructions must never be written through repository-controlled paths.
        with tempfile.TemporaryDirectory(prefix="aegispr-build-") as temporary:
            dockerfile = Path(temporary) / "Dockerfile"
            dockerfile.write_text("\n".join(
                [
                    f"FROM {base_image}",
                    "RUN useradd --create-home -u 10001 aegis",
                    "ENV PATH=/home/aegis/.local/bin:$PATH",
                    "WORKDIR /workspace",
                    "COPY --chown=10001:10001 . .",
                    "USER 10001",
                    f"RUN {install}",
                ]
            ), encoding="utf-8")
            return subprocess.run(
                ["docker", "build", "--file", str(dockerfile), "--tag", tag, str(checkout)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

    def _run_image(self, tag: str, command: str, commit: str, branch: str = "repair") -> TestExecution:
        if not self._is_allowed_command(command):
            return self._skipped("repair", commit, "Command was rejected by the safety policy")
        started = time.monotonic()
        container_name = f"aegispr-test-{uuid4().hex}"
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--name", container_name, "--rm", "--network=none", "--read-only",
                    "--tmpfs=/tmp:rw,noexec,nosuid,size=256m", f"--memory={self.memory}",
                    f"--cpus={self.cpus}", "--pids-limit=256",
                    "--security-opt=no-new-privileges", "--cap-drop=ALL", tag,
                    "/bin/sh", "-lc", command,
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            status = ExecutionStatus.PASSED if result.returncode == 0 else ExecutionStatus.FAILED
            return self._result(
                branch, commit, status, result.returncode, result.stdout, result.stderr, started
            )
        except subprocess.TimeoutExpired as exc:
            return self._result(
                branch, commit, ExecutionStatus.TIMEOUT, None, exc.stdout or "", exc.stderr or "", started
            )
        finally:
            # A killed Docker CLI does not reliably stop its daemon-managed container.
            self._cleanup(["docker", "container", "rm", "--force", container_name])

    @staticmethod
    def _build_error(commit: str, result: subprocess.CompletedProcess[str]) -> TestExecution:
        return TestExecution(
            branch="repair",
            commit=commit,
            status=ExecutionStatus.ERROR,
            exit_code=result.returncode,
            stdout=(result.stdout or "")[-20_000:],
            stderr=(result.stderr or "")[-20_000:],
            environment={"executor": "docker", "phase": "build"},
        )

    @staticmethod
    def _remove_image(tag: str) -> None:
        DockerSandbox._cleanup(["docker", "image", "rm", "--force", tag])

    @staticmethod
    def _cleanup(command: list[str]) -> None:
        try:
            subprocess.run(command, capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            logging.getLogger(__name__).warning("Sandbox resource cleanup could not complete")

    @classmethod
    def _is_allowed_command(cls, command: str) -> bool:
        return command in cls.ALLOWED_COMMANDS

    @staticmethod
    def _is_safe_test_path(path: PurePosixPath) -> bool:
        if path.is_absolute() or ".." in path.parts or not path.parts:
            return False
        if any(part.startswith(".") for part in path.parts) or "\\" in str(path):
            return False
        if any(ord(character) < 32 or ord(character) == 127 for character in str(path)):
            return False
        if path.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx"}:
            return False
        lowered_parts = [part.lower() for part in path.parts]
        return (
            any(part in {"test", "tests", "__tests__"} for part in lowered_parts[:-1])
            or "test" in path.stem.lower()
            or "spec" in path.stem.lower()
        )

    @staticmethod
    def _runtime(profile: RepositoryProfile) -> tuple[str | None, str | None]:
        if "Python" in profile.languages and profile.install_command in {"pip install .", "pip install -r requirements.txt"}:
            return "python:3.12-slim", profile.install_command
        if any(language in profile.languages for language in ("TypeScript", "JavaScript")) and profile.install_command in {"npm ci", "npm ci --ignore-scripts", "npm install --ignore-scripts"}:
            return "node:22-bookworm-slim", "npm ci --ignore-scripts" if profile.install_command == "npm ci" else profile.install_command
        return None, None

    @staticmethod
    def _write_generated_test(checkout: Path, relative: PurePosixPath, code: str) -> bool:
        # Directory descriptors and O_NOFOLLOW prevent symlink swaps between validation
        # and writing. The final file is created exclusively and cannot replace a file.
        descriptor = os.open(checkout, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for component in relative.parts[:-1]:
                try:
                    os.mkdir(component, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            target = os.open(relative.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=descriptor)
            with os.fdopen(target, "w", encoding="utf-8") as stream:
                stream.write(code)
            return True
        except OSError:
            return False
        finally:
            os.close(descriptor)

    @staticmethod
    def _result(branch, commit, status, exit_code, stdout, stderr, started) -> TestExecution:
        return TestExecution(
            branch=branch,
            commit=commit,
            status=status,
            exit_code=exit_code,
            stdout=(stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else stdout or "")[-20_000:],
            stderr=(stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else stderr or "")[-20_000:],
            duration_ms=int((time.monotonic() - started) * 1000),
            environment={"executor": "docker", "network": "none", "privileged": False},
        )

    @staticmethod
    def _skipped(branch: str, commit: str, reason: str) -> TestExecution:
        return TestExecution(
            branch=branch,
            commit=commit,
            status=ExecutionStatus.SKIPPED,
            stderr=reason,
            environment={"executor": "docker"},
        )

