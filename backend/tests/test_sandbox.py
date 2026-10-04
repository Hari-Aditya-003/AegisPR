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


def test_runtime_selection_is_narrow() -> None:
    assert DockerSandbox._runtime(RepositoryProfile(languages=["Python"], install_command="pip install ."))[0] == "python:3.12-slim"
    assert DockerSandbox._runtime(RepositoryProfile(languages=["TypeScript"], install_command="npm ci"))[0] == "node:22-bookworm-slim"
    assert DockerSandbox._runtime(RepositoryProfile(languages=["Rust"])) == (None, None)
