from __future__ import annotations

import subprocess
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
    ALLOWED_COMMAND_PREFIXES = ("npm test", "npm run", "npx vitest", "npx jest", "pytest", "python -m pytest")
    FORBIDDEN_SHELL_TOKENS = (";", "&", "|", "`", "$", "\n", "\r", ">", "<")

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
        target = checkout.joinpath(*relative.parts)
        if target.exists():
            return self._skipped(branch, commit, "Generated test cannot replace an existing file")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(generated_test.test_code, encoding="utf-8")

        base_image, install = self._runtime(profile)
        if not base_image or not install:
            return self._skipped(branch, commit, "Unsupported project runtime")
        dockerfile = checkout / ".aegispr.Dockerfile"
        dockerfile.write_text(
            "\n".join(
                [
                    f"FROM {base_image}",
                    "WORKDIR /workspace",
                    "COPY . .",
                    f"RUN {install}",
                    "RUN useradd -r -u 10001 aegis || true",
                    "USER 10001",
                ]
            ),
            encoding="utf-8",
        )
        tag = f"aegispr-run-{commit[:12]}-{uuid4().hex[:10]}"
        started = time.monotonic()
        try:
            build = subprocess.run(
                ["docker", "build", "--file", str(dockerfile), "--tag", tag, str(checkout)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            if build.returncode != 0:
                return self._result(branch, commit, ExecutionStatus.ERROR, build.returncode, build.stdout, build.stderr, started)
            run = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network=none",
                    "--read-only",
                    "--tmpfs=/tmp:rw,noexec,nosuid,size=256m",
                    f"--memory={self.memory}",
                    f"--cpus={self.cpus}",
                    "--pids-limit=256",
                    "--security-opt=no-new-privileges",
                    "--cap-drop=ALL",
                    tag,
                    "/bin/sh",
                    "-lc",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            status = ExecutionStatus.PASSED if run.returncode == 0 else ExecutionStatus.FAILED
            return self._result(branch, commit, status, run.returncode, run.stdout, run.stderr, started)
        except subprocess.TimeoutExpired as exc:
            return self._result(branch, commit, ExecutionStatus.TIMEOUT, None, exc.stdout or "", exc.stderr or "", started)
        finally:
            subprocess.run(["docker", "image", "rm", "--force", tag], capture_output=True, text=True)
            dockerfile.unlink(missing_ok=True)

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
            and not checkout.joinpath(*relative.parts).exists()
        )
        generated_tag = f"aegispr-repair-{commit[:12]}-{suffix}-generated"
        try:
            if safe_path and generated_command:
                target = checkout.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(generated_test.test_code, encoding="utf-8")
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
        dockerfile = checkout / ".aegispr.Dockerfile"
        dockerfile.write_text(
            "\n".join(
                [
                    f"FROM {base_image}",
                    "WORKDIR /workspace",
                    "COPY . .",
                    f"RUN {install}",
                    "RUN useradd -r -u 10001 aegis || true",
                    "USER 10001",
                ]
            ),
            encoding="utf-8",
        )
        try:
            return subprocess.run(
                ["docker", "build", "--file", str(dockerfile), "--tag", tag, str(checkout)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        finally:
            dockerfile.unlink(missing_ok=True)

    def _run_image(self, tag: str, command: str, commit: str) -> TestExecution:
        if not self._is_allowed_command(command):
            return self._skipped("repair", commit, "Command was rejected by the safety policy")
        started = time.monotonic()
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm", "--network=none", "--read-only",
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
                "repair", commit, status, result.returncode, result.stdout, result.stderr, started
            )
        except subprocess.TimeoutExpired as exc:
            return self._result(
                "repair", commit, ExecutionStatus.TIMEOUT, None, exc.stdout or "", exc.stderr or "", started
            )

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
        subprocess.run(["docker", "image", "rm", "--force", tag], capture_output=True, text=True)

    @classmethod
    def _is_allowed_command(cls, command: str) -> bool:
        return not any(token in command for token in cls.FORBIDDEN_SHELL_TOKENS) and any(
            command == prefix or command.startswith(f"{prefix} ")
            for prefix in cls.ALLOWED_COMMAND_PREFIXES
        )

    @staticmethod
    def _is_safe_test_path(path: PurePosixPath) -> bool:
        if path.is_absolute() or ".." in path.parts or not path.parts:
            return False
        if path.parts[0].startswith(".") or "\\" in str(path):
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
        if "Python" in profile.languages:
            return "python:3.12-slim", profile.install_command
        if any(language in profile.languages for language in ("TypeScript", "JavaScript")):
            return "node:22-bookworm-slim", profile.install_command
        return None, None

    @staticmethod
    def _result(branch, commit, status, exit_code, stdout, stderr, started) -> TestExecution:
        return TestExecution(
            branch=branch,
            commit=commit,
            status=status,
            exit_code=exit_code,
            stdout=(stdout or "")[-20_000:],
            stderr=(stderr or "")[-20_000:],
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

