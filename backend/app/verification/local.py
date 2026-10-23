"""Conservative, token-free review of two committed Git revisions.

This module reads Git objects. It never executes repository code and its signals are
review prompts, not proof that a change is vulnerable or API-incompatible.
"""

from __future__ import annotations

import ast
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from app.services.repository import RepositoryService


class LocalVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class LocalChangeReport:
    base_commit: str
    head_commit: str
    changed_files: list[str] = field(default_factory=list)
    api_risks: list[str] = field(default_factory=list)
    security_warnings: list[str] = field(default_factory=list)
    scope: str = "committed changes only; static review, not proof of safety"
    model_calls: int = 0


def _git(repo: Path, *args: str) -> str:
    try:
        return RepositoryService._run(["git", "-C", str(repo), *args])
    except (OSError, RuntimeError) as exc:
        raise LocalVerificationError("Local Git operation failed; check repository and base reference") from exc


def _commit(repo: Path, ref: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._/~^-]{1,200}", ref) or ref.startswith("-"):
        raise LocalVerificationError("Invalid base reference")
    commit = _git(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").strip()
    RepositoryService._validate_commit(commit)
    return commit


def _source(repo: Path, commit: str, path: str) -> str | None:
    RepositoryService._validate_relative_path(path)
    try:
        return _git(repo, "show", f"{commit}:{path}")
    except LocalVerificationError:
        return None


def _public_signatures(source: str | None) -> dict[str, str]:
    if source is None:
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    signatures: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            signatures[node.name] = f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}{ast.unparse(node.args)}"
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and not method.name.startswith("_"):
                    signatures[f"{node.name}.{method.name}"] = (
                        f"{'async ' if isinstance(method, ast.AsyncFunctionDef) else ''}{ast.unparse(method.args)}"
                    )
    return signatures


_GUARDS = (
    ("auth", re.compile(r"^\s*@(?:login_required|permission_required|require_auth|authenticated|authorize)\b")),
    ("auth", re.compile(r"\bDepends\(\s*(?:get_current_user|require_[A-Za-z_]*auth|verify_token)\b")),
    ("validation", re.compile(r"^\s*@(?:validate|validate_input|validated)\b")),
)


def _removed_guards(diff: str, path: str) -> list[str]:
    removed = [line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    added = {line[1:].strip() for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")}
    warnings: list[str] = []
    for line in removed:
        if line.strip() in added:
            continue
        for kind, pattern in _GUARDS:
            if pattern.search(line):
                warnings.append(f"{path}: removed {kind} guard; review whether access or validation weakened")
                break
    return list(dict.fromkeys(warnings))


def inspect_committed_change(repository: Path, base_ref: str = "HEAD~1") -> LocalChangeReport:
    repo = Path(repository).resolve()
    if not repo.is_dir():
        raise LocalVerificationError("Repository directory does not exist")
    root = Path(_git(repo, "rev-parse", "--show-toplevel").strip()).resolve()
    if _git(root, "status", "--porcelain", "--untracked-files=all").strip():
        raise LocalVerificationError("Repository has uncommitted or untracked changes; commit or stash before verifying")
    base = _commit(root, base_ref)
    head = _commit(root, "HEAD")
    paths = [path for path in _git(
        root, "diff", "--name-only", "--no-renames", "-z", base, head,
    ).split("\x00") if path]
    api_risks: list[str] = []
    security_warnings: list[str] = []
    for path in paths:
        try:
            RepositoryService._validate_relative_path(path)
        except ValueError as exc:
            raise LocalVerificationError("Changed path cannot be safely inspected") from exc
        if path.endswith(".py"):
            before = _public_signatures(_source(root, base, path))
            after = _public_signatures(_source(root, head, path))
            for name, signature in before.items():
                if name not in after:
                    api_risks.append(f"{path}: public Python API {name} removed; review compatibility (not confirmed break)")
                elif after[name] != signature:
                    api_risks.append(f"{path}: public Python API {name} signature changed; review compatibility (not confirmed break)")
        diff = _git(root, "diff", "--no-ext-diff", "--unified=0", base, head, "--", path)
        security_warnings.extend(_removed_guards(diff, path))
    return LocalChangeReport(base, head, paths, api_risks, security_warnings)


def compare_measurements(
    base_times_ms: list[int], head_times_ms: list[int],
    base_peaks_bytes: list[int], head_peaks_bytes: list[int], *, threshold: float = 0.30,
) -> dict[str, float | int | str | None]:
    """Compare repeated, same-command measurements; label noisy data inconclusive."""
    if not 0.05 <= threshold <= 2.0:
        raise ValueError("Performance threshold must be between 5% and 200%")

    def metric(before: list[int], after: list[int]) -> tuple[str, float | None, float | None]:
        if len(before) < 3 or len(after) < 3 or any(value <= 0 for value in before + after):
            return "inconclusive", None, None
        old, new = statistics.median(before), statistics.median(after)
        if max(before) - min(before) > old * 0.20 or max(after) - min(after) > new * 0.20:
            return "inconclusive", old, new
        return ("possible_regression" if new > old * (1 + threshold) else "no_regression_observed"), old, new

    time_status, base_time, head_time = metric(base_times_ms, head_times_ms)
    memory_status, base_memory, head_memory = metric(base_peaks_bytes, head_peaks_bytes)
    return {
        "time_status": time_status,
        "memory_status": memory_status,
        "base_median_ms": base_time,
        "head_median_ms": head_time,
        "base_median_peak_bytes": base_memory,
        "head_median_peak_bytes": head_memory,
        "threshold": threshold,
    }
