"""Token-free command-line entry point for committed pre-push reviews."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from app.verification.local import LocalVerificationError, inspect_committed_change


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aegispr", description="Evidence-first checks for committed changes")
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify", help="review committed changes before a push; no model calls")
    verify.add_argument("--repo", type=Path, default=Path.cwd(), help="local Git repository")
    verify.add_argument("--base", default="HEAD~1", help="trusted base ref or commit")
    verify.add_argument("--json", action="store_true", help="machine-readable result")
    args = parser.parse_args(argv)
    try:
        report = inspect_committed_change(args.repo, args.base)
    except LocalVerificationError as exc:
        print(f"AegisPR could not verify: {exc}", file=sys.stderr)
        return 2
    payload = asdict(report)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"AegisPR: {report.base_commit[:12]} → {report.head_commit[:12]}")
        print(f"Reviewed {len(report.changed_files)} committed files. No model calls or repository code execution.")
        for risk in report.api_risks:
            print(f"API REVIEW: {risk}")
        for warning in report.security_warnings:
            print(f"SECURITY REVIEW: {warning}")
        print(report.scope)
    return 1 if report.api_risks or report.security_warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
