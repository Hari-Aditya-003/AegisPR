import json
import subprocess
from pathlib import Path

import pytest

from app.services.context_ranker import ContextDocument
from app.services.repository import RepositoryService


def run(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def create_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(repo, "init", "-b", "main")
    run(repo, "config", "user.email", "test@example.com")
    run(repo, "config", "user.name", "Test")
    (repo / "package.json").write_text(json.dumps({
        "scripts": {"test": "vitest run", "build": "next build"},
        "dependencies": {"next": "15.5.27"}, "devDependencies": {"vitest": "3.2.4"},
    }))
    (repo / "package-lock.json").write_text("{}")
    (repo / "coupon.ts").write_text("export const total = 100\n")
    (repo / "checkout.ts").write_text("import { total } from './coupon'\n")
    run(repo, "add", ".")
    run(repo, "commit", "-m", "base")
    base = run(repo, "rev-parse", "HEAD")
    (repo / "coupon.ts").write_text("export const total = -50\n")
    run(repo, "add", "coupon.ts")
    run(repo, "commit", "-m", "change")
    return repo, base, run(repo, "rev-parse", "HEAD")


def test_repository_profile_diff_context_and_impact(tmp_path: Path) -> None:
    repo, base, head = create_repository(tmp_path)
    service = RepositoryService()

    profile = service.profile(repo, head)
    assert profile.framework == "Next.js"
    assert profile.test_framework == "vitest"
    assert profile.test_command == "npm test -- --run"
    assert service.changed_files(repo, base, head) == ["coupon.ts"]
    assert "-export const total = 100" in service.diff(repo, base, head)

    documents = service.context_documents(repo, head, ["coupon.ts"])
    assert documents[0].path == "coupon.ts"
    nodes, edges = service.impact_graph(["coupon.ts"], documents)
    assert any(node.id == "checkout.ts" for node in nodes)
    assert edges[0].source == "coupon.ts"


def test_repository_command_failure_is_bounded() -> None:
    with pytest.raises(RuntimeError):
        RepositoryService._run(["git", "definitely-not-a-command"])
