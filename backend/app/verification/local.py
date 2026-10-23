"""Conservative, token-free review of two committed Git revisions.

This module reads Git objects. It never executes repository code and its signals are
review prompts, not proof that a change is vulnerable or API-incompatible.
"""

from __future__ import annotations

import ast
import re
import statistics
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.verification import ExecutionStatus
from app.services.repository import RepositoryService
from app.services.sandbox import DockerSandbox


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
    ("auth", re.compile(r"\b(?:requireAuth|assertAuthenticated|authorize|checkPermission)\s*\(")),
    ("validation", re.compile(r"^\s*@(?:validate|validate_input|validated)\b")),
    ("validation", re.compile(r"\b(?:validateInput|assertValidInput|parseAndValidate)\s*\(")),
)


def _simple_js_exports(source: str | None) -> dict[str, str]:
    """Inspect simple named exports only; this is not a TypeScript compiler."""
    if source is None:
        return {}
    pattern = re.compile(
        r"(?m)^\s*export\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]{0,1000})\)"
    )
    return {name: re.sub(r"\s+", "", params) for name, params in pattern.findall(source)}


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
        elif path.endswith((".js", ".jsx", ".ts", ".tsx")):
            before = _simple_js_exports(_source(root, base, path))
            after = _simple_js_exports(_source(root, head, path))
            for name, signature in before.items():
                if name not in after:
                    api_risks.append(f"{path}: simple exported JS/TS function {name} removed; review compatibility (not confirmed break)")
                elif after[name] != signature:
                    api_risks.append(f"{path}: simple exported JS/TS function {name} signature changed; review compatibility (not confirmed break)")
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


def summarize_suite_outcomes(base: list[str], head: list[str]) -> str:
    if len(base) < 3 or len(head) < 3:
        return "inconclusive"
    if set(base) == {"PASSED"} and set(head) == {"FAILED"}:
        return "reproducible_regression"
    if set(base) == {"PASSED"} and set(head) == {"PASSED"}:
        return "no_failure_observed"
    if set(base) == {"FAILED"} and set(head) == {"FAILED"}:
        return "pre_existing_failure"
    if set(base) == {"FAILED"} and set(head) == {"PASSED"}:
        return "possible_improvement"
    return "inconclusive"


def execute_committed_suites(
    repository: Path, base_commit: str, head_commit: str,
    *, sandbox: DockerSandbox | None = None, repetitions: int = 3,
) -> dict:
    """Opt-in Docker comparison of the same detected test command on two commits."""
    root = Path(repository).resolve()
    RepositoryService._validate_commit(base_commit)
    RepositoryService._validate_commit(head_commit)
    if not 3 <= repetitions <= 5:
        raise LocalVerificationError("Three to five repetitions are required for a stability check")
    service = RepositoryService()
    base_profile = service.profile(root, base_commit)
    head_profile = service.profile(root, head_commit)
    command = head_profile.test_command
    if not command or command != base_profile.test_command or not DockerSandbox._is_allowed_command(command):
        raise LocalVerificationError("Base and head must have the same approved existing test command")
    runner = sandbox or DockerSandbox(300, "2g", 2.0)
    with tempfile.TemporaryDirectory(prefix="aegispr-local-") as temporary:
        paths = [("base", base_commit, Path(temporary) / "base", base_profile),
                 ("head", head_commit, Path(temporary) / "head", head_profile)]
        created: list[Path] = []
        try:
            executions = {}
            for branch, commit, checkout, profile in paths:
                service.checkout(root, commit, checkout)
                created.append(checkout)
                executions[branch] = runner.run_existing_suite(
                    checkout, commit, branch, profile, repetitions=repetitions,
                )
        finally:
            for checkout in reversed(created):
                try:
                    _git(root, "worktree", "remove", "--force", str(checkout))
                except LocalVerificationError:
                    # The temporary directory still removes the checkout. A later
                    # `git worktree prune` can clear stale administrative entries.
                    pass
    base, head = executions["base"], executions["head"]
    status = summarize_suite_outcomes(
        [item.status.value for item in base], [item.status.value for item in head],
    )
    all_passed = status == "no_failure_observed"
    performance = compare_measurements(
        [item.duration_ms for item in base] if all_passed else [],
        [item.duration_ms for item in head] if all_passed else [],
        [item.environment.get("peak_memory_bytes", 0) for item in base] if all_passed else [],
        [item.environment.get("peak_memory_bytes", 0) for item in head] if all_passed else [],
    )
    return {
        "status": status,
        "test_command": command,
        "base": [{"status": item.status.value, "duration_ms": item.duration_ms,
                  "peak_memory_bytes": item.environment.get("peak_memory_bytes")}
                 for item in base],
        "head": [{"status": item.status.value, "duration_ms": item.duration_ms,
                  "peak_memory_bytes": item.environment.get("peak_memory_bytes")}
                 for item in head],
        "performance": performance,
        "scope": "Docker-isolated existing suite; timing includes container startup and is a screening signal",
    }
