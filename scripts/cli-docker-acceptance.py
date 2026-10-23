"""Credential-free acceptance for the optional local Docker verification path.

The fixture is deliberately tiny and controlled. This does not evaluate a real PR,
generated Nemotron test, GPU kernel, or model quality.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from app.cli import main


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="aegispr-cli-acceptance-") as temporary:
        repo = Path(temporary) / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "AegisPR CI fixture")
        git(repo, "config", "user.email", "fixture@example.invalid")
        (repo / "requirements.txt").write_text("pytest==9.1.1\n", encoding="utf-8")
        (repo / "target.py").write_text("def compute(value):\n    return value + 1\n", encoding="utf-8")
        (repo / "test_target.py").write_text(
            "from target import compute\n\ndef test_compute():\n    assert compute(1) == 2\n",
            encoding="utf-8",
        )
        git(repo, "add", "requirements.txt", "target.py", "test_target.py")
        git(repo, "commit", "-qm", "passing base")
        base = git(repo, "rev-parse", "HEAD")
        (repo / "target.py").write_text("def compute(value):\n    return value + 2\n", encoding="utf-8")
        git(repo, "add", "target.py")
        git(repo, "commit", "-qm", "deliberate regression")
        head = git(repo, "rev-parse", "HEAD")
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["verify", "--repo", str(repo), "--base", base, "--docker-tests", "--json"])
        report = json.loads(output.getvalue())
        assert exit_code == 1, (exit_code, report)
        assert report["base_commit"] == base and report["head_commit"] == head
        assert report["model_calls"] == 0
        assert report["docker_tests"]["status"] == "reproducible_regression", report
        assert [run["status"] for run in report["docker_tests"]["base"]] == ["PASSED"] * 3
        assert [run["status"] for run in report["docker_tests"]["head"]] == ["FAILED"] * 3
        assert report["docker_tests"]["performance"]["time_status"] == "inconclusive"
        print("Local CLI Docker acceptance: 3 base PASS / 3 head FAIL; no model calls")


if __name__ == "__main__":
    run()
