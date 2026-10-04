from __future__ import annotations

import subprocess
import time
from pathlib import Path, PurePosixPath

from app.schemas.verification import ExecutionStatus, GeneratedTest, RepositoryProfile, TestExecution


class DockerSandbox:
    ALLOWED_COMMAND_PREFIXES = ("npm test", "npm run", "npx vitest", "npx jest", "pytest", "python -m pytest")

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
        command = generated_test.test_command or profile.test_command
        if not command or not command.startswith(self.ALLOWED_COMMAND_PREFIXES):
            return self._skipped(branch, commit, "No supported test command was detected")
        if not generated_test.file_path or not generated_test.test_code:
            return self._skipped(branch, commit, "Nemotron test generation was unavailable")
        relative = PurePosixPath(generated_test.file_path)
        if relative.is_absolute() or ".." in relative.parts:
            return self._skipped(branch, commit, "Generated test path was rejected")
        target = checkout.joinpath(*relative.parts)
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
        tag = f"aegispr-run-{commit[:12]}-{generated_test.id.lower()}".replace("_", "-")
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

