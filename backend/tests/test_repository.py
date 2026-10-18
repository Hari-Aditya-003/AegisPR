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


def test_applies_safe_unified_patch_and_rejects_traversal(tmp_path: Path) -> None:
    repo, _, head = create_repository(tmp_path)
    service = RepositoryService()
    assert service.file_content(repo, head, "coupon.ts") == "export const total = -50\n"
    patch = (
        "diff --git a/coupon.ts b/coupon.ts\n"
        "--- a/coupon.ts\n"
        "+++ b/coupon.ts\n"
        "@@ -1 +1 @@\n"
        "-export const total = -50\n"
        "+export const total = 0\n"
    )

    service.apply_patch(repo, patch)
    assert (repo / "coupon.ts").read_text() == "export const total = 0\n"

    unsafe = "diff --git a/coupon.ts b/../escape.ts\n--- a/coupon.ts\n+++ b/../escape.ts\n"
    with pytest.raises(ValueError, match="unsafe path"):
        service.apply_patch(repo, unsafe)

    with pytest.raises(ValueError, match="outside the pull request scope"):
        service.apply_patch(repo, patch, {"checkout.ts"})


def test_repair_patch_does_not_follow_internal_patch_file_symlink(tmp_path: Path) -> None:
    repo, _, _ = create_repository(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("preserve me")
    (repo / ".aegispr-repair.patch").symlink_to(outside)
    patch = "--- a/coupon.ts\n+++ b/coupon.ts\n@@ -1 +1 @@\n-export const total = -50\n+export const total = 0\n"

    RepositoryService().apply_patch(repo, patch, {"coupon.ts"})

    assert outside.read_text() == "preserve me"
    assert (repo / ".aegispr-repair.patch").is_symlink()


@pytest.mark.parametrize("operation", ["rename", "copy"])
def test_repair_rejects_extended_headers_that_hide_an_unapproved_target(
    tmp_path: Path, operation: str,
) -> None:
    repo, _, _ = create_repository(tmp_path)
    patch = (
        "diff --git a/coupon.ts b/coupon.ts\n"
        "similarity index 100%\n"
        f"{operation} from coupon.ts\n"
        f"{operation} to unapproved.ts\n"
    )

    with pytest.raises(ValueError, match="metadata"):
        RepositoryService().apply_patch(repo, patch, {"coupon.ts"})

    assert (repo / "coupon.ts").read_text() == "export const total = -50\n"
    assert not (repo / "unapproved.ts").exists()


@pytest.mark.parametrize("header", [
    "old mode 100644", "new mode 100755", "new file mode 100755",
    "deleted file mode 100644",
])
def test_repair_rejects_mode_metadata_before_starting_git(
    tmp_path: Path, monkeypatch, header: str,
) -> None:
    calls = []
    monkeypatch.setattr(RepositoryService, "_run", lambda self, args: calls.append(args))
    patch = f"diff --git a/coupon.ts b/coupon.ts\n{header}\n"

    with pytest.raises(ValueError, match="metadata"):
        RepositoryService().apply_patch(tmp_path, patch, {"coupon.ts"})

    assert not calls


@pytest.mark.parametrize("path", ["tests/.git/config", "a/.aegispr/token", "./.git/config", "test\x00.py", "test\n.py"])
def test_repair_paths_reject_nested_metadata_and_control_characters(path: str) -> None:
    with pytest.raises(ValueError, match="unsafe path"):
        RepositoryService._validate_relative_path(path)


@pytest.mark.parametrize("url", ["file:///etc", "ssh://github.com/acme/store.git", "https://localhost/private.git", "https://github.com/acme/store.git?x=1"])
def test_clone_rejects_noncanonical_remote_without_starting_git(tmp_path: Path, monkeypatch, url: str) -> None:
    calls = []
    monkeypatch.setattr(RepositoryService, "_run", lambda self, args: calls.append(args))
    with pytest.raises(ValueError, match="clone URL"):
        RepositoryService().clone(url, tmp_path / "checkout")
    assert not calls


def test_git_child_environment_excludes_application_secrets_and_disables_external_helpers(monkeypatch) -> None:
    monkeypatch.setenv("NEBIUS_API_KEY", "test-only-secret")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert RepositoryService._run(["git", "status"]) == "ok"
    assert "NEBIUS_API_KEY" not in captured["env"]
    assert "GIT_CONFIG_COUNT" not in captured["env"]
    assert captured["env"]["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert "protocol.ext.allow=never" in captured["args"]


def test_fetch_rejects_revision_option_injection_before_starting_git(tmp_path: Path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(RepositoryService, "_run", lambda self, args: calls.append(args))
    with pytest.raises(ValueError, match="commit"):
        RepositoryService().fetch_commits(tmp_path, "--upload-pack=anything", "b" * 40)
    assert not calls
