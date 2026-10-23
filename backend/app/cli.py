"""Token-free command-line entry point for committed pre-push reviews."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from app.verification.local import LocalVerificationError, execute_committed_suites, inspect_committed_change
from app.verification.gpu import GPUComparisonError, compare_gpu_artifacts, load_gpu_artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aegispr", description="Evidence-first checks for committed changes")
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify", help="review committed changes before a push; no model calls")
    verify.add_argument("--repo", type=Path, default=Path.cwd(), help="local Git repository")
    verify.add_argument("--base", default="HEAD~1", help="trusted base ref or commit")
    verify.add_argument("--json", action="store_true", help="machine-readable result")
    verify.add_argument(
        "--docker-tests", action="store_true",
        help="opt in to three isolated base/head test runs (may download dependencies during image build)",
    )
    gpu = commands.add_parser("compare-gpu", help="compare caller-supplied CUDA result files; does not run kernels")
    gpu.add_argument("--base", type=Path, required=True, help="base CUDA result JSON")
    gpu.add_argument("--head", type=Path, required=True, help="changed CUDA result JSON")
    gpu.add_argument("--json", action="store_true", help="machine-readable result")
    args = parser.parse_args(argv)
    if args.command == "compare-gpu":
        try:
            result = compare_gpu_artifacts(load_gpu_artifact(args.base), load_gpu_artifact(args.head))
        except GPUComparisonError as exc:
            print(f"AegisPR could not compare GPU results: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"GPU numeric comparison: {result['numeric_status']}")
            for name in result["different_cases"]:
                print(f"OUTPUT DIFFERENCE: {name}")
            for name, timing in result["performance"].items():
                print(f"GPU timing {name}: {timing['status']}")
            print(result["scope"])
        return 1 if result["different_cases"] or any(
            timing["status"] == "possible_regression" for timing in result["performance"].values()
        ) else 0
    try:
        report = inspect_committed_change(args.repo, args.base)
        docker = execute_committed_suites(args.repo, report.base_commit, report.head_commit) if args.docker_tests else None
    except LocalVerificationError as exc:
        print(f"AegisPR could not verify: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("AegisPR could not verify: Docker or a local runtime dependency is unavailable", file=sys.stderr)
        return 2
    payload = asdict(report)
    if docker:
        payload["docker_tests"] = docker
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"AegisPR: {report.base_commit[:12]} → {report.head_commit[:12]}")
        print(f"Reviewed {len(report.changed_files)} committed files. No model calls.")
        if docker:
            print("Repository tests were executed inside isolated Docker containers.")
        else:
            print("Static review did not execute repository code.")
        for risk in report.api_risks:
            print(f"API REVIEW: {risk}")
        for warning in report.security_warnings:
            print(f"SECURITY REVIEW: {warning}")
        if docker:
            print(f"DOCKER TESTS: {docker['status']} ({docker['test_command']})")
            print(f"PERFORMANCE: time={docker['performance']['time_status']}, memory={docker['performance']['memory_status']}")
        print(report.scope)
    if docker and docker["status"] == "inconclusive":
        return 2
    if docker and (
        docker["status"] == "reproducible_regression"
        or "possible_regression" in {docker["performance"]["time_status"], docker["performance"]["memory_status"]}
    ):
        return 1
    return 1 if report.api_risks or report.security_warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
