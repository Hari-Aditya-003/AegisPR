from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path, PurePosixPath

from app.schemas.verification import ImpactEdge, ImpactNode, RepositoryProfile
from app.services.context_ranker import ContextDocument


class RepositoryService:
    def __init__(self, max_diff_characters: int = 120_000) -> None:
        self.max_diff_characters = max_diff_characters

    def clone(self, clone_url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._run(["git", "clone", "--filter=blob:none", "--no-checkout", clone_url, str(destination)])

    def fetch_commits(self, repository: Path, base_commit: str, head_commit: str) -> None:
        self._run(["git", "-C", str(repository), "fetch", "origin", base_commit, head_commit])

    def changed_files(self, repository: Path, base_commit: str, head_commit: str) -> list[str]:
        output = self._run(
            ["git", "-C", str(repository), "diff", "--name-only", base_commit, head_commit]
        )
        return [line for line in output.splitlines() if line and not line.startswith("../")]

    def diff(self, repository: Path, base_commit: str, head_commit: str) -> str:
        output = self._run(
            ["git", "-C", str(repository), "diff", "--unified=30", base_commit, head_commit]
        )
        return output[: self.max_diff_characters]

    def file_content(self, repository: Path, commit: str, file_path: str) -> str:
        self._validate_relative_path(file_path)
        return self._run(["git", "-C", str(repository), "show", f"{commit}:{file_path}"])[
            : self.max_diff_characters
        ]

    def apply_patch(
        self, checkout: Path, patch: str, allowed_paths: set[str] | None = None
    ) -> None:
        if not patch or len(patch) > 50_000 or "\x00" in patch or "GIT binary patch" in patch:
            raise ValueError("Repair patch was rejected by the safety policy")
        paths: list[str] = []
        for line in patch.splitlines():
            if line.startswith("diff --git "):
                parts = line.split()
                if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
                    raise ValueError("Repair patch contains an invalid file header")
                paths.extend((parts[2][2:], parts[3][2:]))
            elif line.startswith(("--- ", "+++ ")):
                value = line[4:].split("\t", 1)[0]
                if value != "/dev/null":
                    if not value.startswith(("a/", "b/")):
                        raise ValueError("Repair patch contains an invalid file path")
                    paths.append(value[2:])
        if not paths:
            raise ValueError("Repair patch did not contain a unified diff")
        for path in paths:
            self._validate_relative_path(path)
            if allowed_paths is not None and path not in allowed_paths:
                raise ValueError("Repair patch modifies a file outside the pull request scope")

        patch_file = checkout / ".aegispr-repair.patch"
        patch_file.write_text(patch, encoding="utf-8")
        try:
            self._run(["git", "-C", str(checkout), "apply", "--check", str(patch_file)])
            self._run(["git", "-C", str(checkout), "apply", str(patch_file)])
        finally:
            patch_file.unlink(missing_ok=True)

    def checkout(self, repository: Path, commit: str, destination: Path) -> None:
        self._run(["git", "-C", str(repository), "worktree", "add", "--detach", str(destination), commit])

    def profile(self, repository: Path, commit: str) -> RepositoryProfile:
        files = self._run(["git", "-C", str(repository), "ls-tree", "-r", "--name-only", commit]).splitlines()
        file_set = set(files)
        languages: list[str] = []
        for language, extensions in {
            "TypeScript": (".ts", ".tsx"),
            "JavaScript": (".js", ".jsx", ".mjs", ".cjs"),
            "Python": (".py",),
        }.items():
            if any(path.endswith(extensions) for path in files):
                languages.append(language)

        if "package.json" in file_set:
            package = json.loads(self._run(["git", "-C", str(repository), "show", f"{commit}:package.json"]))
            scripts = package.get("scripts", {})
            all_dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
            install = "npm ci" if "package-lock.json" in file_set else "npm install --ignore-scripts"
            return RepositoryProfile(
                languages=languages,
                framework="Next.js" if "next" in all_dependencies else None,
                package_manager="npm",
                test_framework=next((name for name in ("vitest", "jest", "mocha") if name in all_dependencies), None),
                install_command=install,
                test_command=(
                    "npm test -- --run"
                    if "test" in scripts and "vitest" in all_dependencies
                    else "npm test -- --runInBand"
                    if "test" in scripts and "jest" in all_dependencies
                    else "npm test"
                    if "test" in scripts
                    else None
                ),
                build_command="npm run build" if "build" in scripts else None,
                lint_command="npm run lint" if "lint" in scripts else None,
                important_files=sorted(file_set.intersection({"package.json", "package-lock.json", "tsconfig.json"})),
            )

        if "pyproject.toml" in file_set or "requirements.txt" in file_set:
            return RepositoryProfile(
                languages=languages or ["Python"],
                package_manager="pip",
                test_framework="pytest" if any("pytest" in path for path in files) else None,
                install_command="pip install -r requirements.txt" if "requirements.txt" in file_set else "pip install .",
                test_command="pytest -q",
                important_files=sorted(file_set.intersection({"pyproject.toml", "requirements.txt", "pytest.ini"})),
            )
        return RepositoryProfile(languages=languages)

    def context_documents(
        self, repository: Path, commit: str, changed_files: list[str], limit: int = 100
    ) -> list[ContextDocument]:
        candidates = list(changed_files)
        tree = self._run(["git", "-C", str(repository), "ls-tree", "-r", "--name-only", commit]).splitlines()
        candidates.extend(
            path
            for path in tree
            if path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")) and path not in changed_files
        )
        documents: list[ContextDocument] = []
        for path in candidates[:limit]:
            try:
                content = self._run(["git", "-C", str(repository), "show", f"{commit}:{path}"])
            except RuntimeError:
                continue
            documents.append(
                ContextDocument(path=path, content=content[:20_000], changed=path in changed_files)
            )
        return documents

    def impact_graph(self, changed_files: list[str], documents: list[ContextDocument]) -> tuple[list[ImpactNode], list[ImpactEdge]]:
        nodes: dict[str, ImpactNode] = {
            path: ImpactNode(id=path, label=Path(path).name, changed=True, reason="Modified by the pull request")
            for path in changed_files
        }
        edges: list[ImpactEdge] = []
        for document in documents:
            if document.path in nodes:
                continue
            for changed in changed_files:
                stem = Path(changed).stem
                if stem and stem.lower() in document.content.lower():
                    nodes.setdefault(
                        document.path,
                        ImpactNode(
                            id=document.path,
                            label=Path(document.path).name,
                            reason=f"References {stem}",
                        ),
                    )
                    edges.append(ImpactEdge(source=changed, target=document.path, reason="reference"))
        return list(nodes.values()), edges[:200]

    @staticmethod
    def _run(args: list[str]) -> str:
        environment = os.environ.copy()
        environment["GIT_TERMINAL_PROMPT"] = "0"
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout)[-4000:])
        return result.stdout

    @staticmethod
    def _validate_relative_path(file_path: str) -> None:
        path = PurePosixPath(file_path)
        if (
            not file_path
            or path.is_absolute()
            or ".." in path.parts
            or path.parts[0] in {".git", ".aegispr"}
            or "\\" in file_path
        ):
            raise ValueError("Repair patch contains an unsafe path")
