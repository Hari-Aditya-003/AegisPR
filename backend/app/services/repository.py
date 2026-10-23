from __future__ import annotations

import ast
import json
import os
import posixpath
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from app.github.parser import parse_pull_request_url
from app.schemas.verification import ImpactEdge, ImpactNode, RepositoryProfile
from app.services.context_ranker import ContextDocument
from app.verification.mutation import changed_python_lines, mutate_python_line


class RepositoryService:
    def __init__(self, max_diff_characters: int = 120_000) -> None:
        self.max_diff_characters = max_diff_characters

    def clone(self, clone_url: str, destination: Path) -> None:
        try:
            if not clone_url.endswith(".git"):
                raise ValueError("Invalid suffix")
            parse_pull_request_url(f"{clone_url[:-4]}/pull/1")
        except ValueError as exc:
            raise ValueError("Repository clone URL must be canonical HTTPS GitHub") from exc
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._run(["git", "clone", "--filter=blob:none", "--no-checkout", "--no-recurse-submodules", "--", clone_url, str(destination)])

    def fetch_commits(self, repository: Path, base_commit: str, head_commit: str) -> None:
        self._validate_commit(base_commit)
        self._validate_commit(head_commit)
        self._run(["git", "-C", str(repository), "fetch", "--no-recurse-submodules", "origin", base_commit, head_commit])

    def changed_files(self, repository: Path, base_commit: str, head_commit: str) -> list[str]:
        self._validate_commit(base_commit)
        self._validate_commit(head_commit)
        output = self._run(
            ["git", "-C", str(repository), "diff", "--name-only", base_commit, head_commit]
        )
        return [line for line in output.splitlines() if line and not line.startswith("../")]

    def diff(self, repository: Path, base_commit: str, head_commit: str) -> str:
        self._validate_commit(base_commit)
        self._validate_commit(head_commit)
        output = self._run(
            ["git", "-C", str(repository), "diff", "--no-ext-diff", "--unified=30", base_commit, head_commit]
        )
        return output[: self.max_diff_characters]

    def file_content(self, repository: Path, commit: str, file_path: str) -> str:
        self._validate_commit(commit)
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
            if line.startswith((
                "rename from ", "rename to ", "copy from ", "copy to ",
                "old mode ", "new mode ", "new file mode ", "deleted file mode ",
            )):
                # Git honors these paths/modes independently of diff headers.
                # The MVP supports textual repairs only, not filesystem metadata.
                raise ValueError("Repair patch contains unsupported filesystem metadata")
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

        with tempfile.TemporaryDirectory(prefix="aegispr-patch-") as temporary:
            patch_file = Path(temporary) / "repair.patch"
            patch_file.write_text(patch, encoding="utf-8")
            self._run(["git", "-C", str(checkout), "apply", "--check", str(patch_file)])
            self._run(["git", "-C", str(checkout), "apply", str(patch_file)])

    def checkout(self, repository: Path, commit: str, destination: Path) -> None:
        self._validate_commit(commit)
        self._run(["git", "-C", str(repository), "worktree", "add", "--detach", str(destination), commit])

    def mutate_changed_python_line(
        self, checkout: Path, diff: str, changed_files: list[str]
    ) -> tuple[str, str] | None:
        """Create one bounded mutation in an isolated checkout, never in the user repository."""
        root = checkout.resolve()
        allowed = set(changed_files)
        for relative, line_numbers in changed_python_lines(diff).items():
            if relative not in allowed or any(part.lower() in {"test", "tests", "__tests__"} for part in PurePosixPath(relative).parts):
                continue
            try:
                self._validate_relative_path(relative)
                target = checkout / relative
                if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root):
                    continue
                source = target.read_text(encoding="utf-8")
                if len(source) > 200_000:
                    continue
                for line_number in line_numbers:
                    mutation = mutate_python_line(source, line_number)
                    if mutation:
                        target.write_text(mutation.source, encoding="utf-8")
                        return relative, mutation.operator
            except (OSError, UnicodeError, ValueError):
                continue
        return None

    def profile(self, repository: Path, commit: str) -> RepositoryProfile:
        self._validate_commit(commit)
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
                property_frameworks=["fast-check"] if "fast-check" in all_dependencies else [],
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
            requirements = (
                self._run(["git", "-C", str(repository), "show", f"{commit}:requirements.txt"])
                if "requirements.txt" in file_set else ""
            )
            return RepositoryProfile(
                languages=languages if "Python" in languages else ["Python", *languages],
                package_manager="pip",
                test_framework="pytest" if any("pytest" in path for path in files) else None,
                property_frameworks=["Hypothesis"] if re.search(
                    r"(?im)^\s*hypothesis(?:\[[^\]]+\])?\s*(?:[=<>~!]|$)", requirements
                ) else [],
                install_command="pip install -r requirements.txt" if "requirements.txt" in file_set else "pip install .",
                test_command="pytest -q",
                important_files=sorted(file_set.intersection({"pyproject.toml", "requirements.txt", "pytest.ini"})),
            )
        return RepositoryProfile(languages=languages)

    def context_documents(
        self, repository: Path, commit: str, changed_files: list[str], limit: int = 100
    ) -> list[ContextDocument]:
        self._validate_commit(commit)
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
            imports = self._import_targets(document)
            for changed in changed_files:
                if changed in imports:
                    nodes.setdefault(
                        document.path,
                        ImpactNode(
                            id=document.path,
                            label=Path(document.path).name,
                            reason=f"Imports {Path(changed).name}",
                        ),
                    )
                    edges.append(ImpactEdge(source=changed, target=document.path, reason="import"))
        return list(nodes.values()), edges[:200]

    @staticmethod
    def _import_targets(document: ContextDocument) -> set[str]:
        """Resolve direct local imports conservatively; unknown aliases add no edge."""
        path = PurePosixPath(document.path)
        targets: set[str] = set()
        if path.suffix == ".py":
            try:
                tree = ast.parse(document.content)
            except SyntaxError:
                return targets
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                    root = ""
                elif isinstance(node, ast.ImportFrom):
                    root = path.parent.as_posix()
                    if node.level:
                        for _ in range(node.level - 1):
                            root = posixpath.dirname(root)
                    else:
                        root = ""
                    prefix = node.module or ""
                    modules.append(prefix)
                    modules.extend(f"{prefix}.{alias.name}" if prefix else alias.name for alias in node.names if alias.name != "*")
                else:
                    continue
                for module in modules:
                    if not module:
                        continue
                    module_path = module.replace(".", "/")
                    resolved = posixpath.normpath(posixpath.join(root, module_path))
                    if resolved != ".." and not resolved.startswith("../"):
                        targets.add(f"{resolved}.py")
                        targets.add(f"{resolved}/__init__.py")
            return targets
        if path.suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            return targets
        pattern = re.compile(
            r"^\s*(?:import|export)\b[^\n;]*?\bfrom\s*['\"](\.[^'\"]+)['\"]|^\s*import\s*['\"](\.[^'\"]+)['\"]",
            re.MULTILINE,
        )
        for match in pattern.finditer(document.content):
            imported = match.group(1) or match.group(2)
            resolved = posixpath.normpath(posixpath.join(path.parent.as_posix(), imported))
            if resolved == ".." or resolved.startswith("../"):
                continue
            if PurePosixPath(resolved).suffix in {".js", ".jsx", ".ts", ".tsx"}:
                targets.add(resolved)
            else:
                for extension in (".js", ".jsx", ".ts", ".tsx"):
                    targets.add(f"{resolved}{extension}")
                    targets.add(f"{resolved}/index{extension}")
        return targets

    @staticmethod
    def _run(args: list[str]) -> str:
        environment = {
            key: value for key, value in os.environ.items()
            if key in {"PATH", "LANG", "LC_ALL", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR"}
        }
        environment.update({
            "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
        })
        args = [
            args[0], "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
            "-c", "protocol.ext.allow=never", "-c", f"core.hooksPath={os.devnull}",
            "-c", "http.followRedirects=false", *args[1:],
        ]
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
            or not path.parts
            or path.is_absolute()
            or ".." in path.parts
            or any(part.lower() in {".git", ".aegispr"} for part in path.parts)
            or "\\" in file_path
            or any(ord(character) < 32 or ord(character) == 127 for character in file_path)
        ):
            raise ValueError("Repair patch contains an unsafe path")

    @staticmethod
    def _validate_commit(commit: str) -> None:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
            raise ValueError("A full Git commit SHA is required")
