"""Validate trusted synthetic PR-like examples without network or provider calls.

The fixture source is committed with the repository and must not be accepted
from API users. It executes locally in a temporary directory, not the hardened
Docker sandbox used for AI-generated tests.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal


Intent = Literal["unintended", "intended", "no_change"]
Language = Literal["python", "node"]


@dataclass(frozen=True)
class SeededCase:
    id: str
    language: Language
    category: str
    intent: Intent
    title: str
    description: str
    base_source: str
    head_source: str
    arguments: list[list[Any]]
    expected_base: list[Any]
    expected_head: list[Any]


def load_cases(path: Path) -> list[SeededCase]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("dataset_id") != "aegispr-seeded-prs-v1" or not isinstance(document.get("cases"), list):
        raise ValueError("Unrecognized seeded dataset")
    result: list[SeededCase] = []
    seen: set[str] = set()
    for item in document["cases"]:
        if not isinstance(item, dict):
            raise ValueError("Seeded case must be an object")
        case = SeededCase(**item)
        if (not re.fullmatch(r"[a-z0-9-]{3,64}", case.id) or case.id in seen
                or case.language not in {"python", "node"}
                or case.intent not in {"unintended", "intended", "no_change"}
                or not case.category or not case.title or not case.description
                or not 1 <= len(case.base_source) <= 5000
                or not 1 <= len(case.head_source) <= 5000
                or "\x00" in case.base_source or "\x00" in case.head_source
                or not isinstance(case.arguments, list) or not 1 <= len(case.arguments) <= 20
                or any(not isinstance(arguments, list) for arguments in case.arguments)
                or len(case.expected_base) != len(case.arguments)
                or len(case.expected_head) != len(case.arguments)):
            raise ValueError(f"Invalid seeded case: {case.id}")
        if (case.expected_base == case.expected_head) != (case.intent == "no_change"):
            raise ValueError(f"Intent and expected outputs disagree: {case.id}")
        seen.add(case.id)
        result.append(case)
    if not 10 <= len(result) <= 20:
        raise ValueError("Seeded dataset requires 10–20 cases")
    return result


def observe_case(case: SeededCase, branch: Literal["base", "head"]) -> list[Any]:
    """Run only reviewed repository fixtures, never arbitrary PR/model content."""
    if branch not in {"base", "head"}:
        raise ValueError("Branch must be base or head")
    source = case.base_source if branch == "base" else case.head_source
    with TemporaryDirectory(prefix="aegispr-seeded-") as temporary:
        workspace = Path(temporary)
        arguments_json = json.dumps(case.arguments, ensure_ascii=False)
        if case.language == "python":
            (workspace / "target.py").write_text(source, encoding="utf-8")
            probe = (
                "import json, runpy\n"
                "evaluate = runpy.run_path('target.py')['evaluate']\n"
                f"for arguments in {repr(case.arguments)}:\n"
                "    try:\n"
                "        value = evaluate(*arguments)\n"
                "    except Exception as exc:\n"
                "        value = 'ERROR:' + type(exc).__name__\n"
                "    print('AEGISPR_OUTPUT=' + json.dumps(value, sort_keys=True))\n"
            )
            (workspace / "probe.py").write_text(probe, encoding="utf-8")
            command = [sys.executable, "-I", "-B", "probe.py"]
        else:
            node = shutil.which("node")
            if not node:
                raise RuntimeError("Node.js is required to validate the JavaScript fixtures")
            (workspace / "target.mjs").write_text(source, encoding="utf-8")
            probe = (
                "import { evaluate } from './target.mjs';\n"
                f"for (const args of {arguments_json}) {{\n"
                "  let value;\n"
                "  try { value = await evaluate(...args); }\n"
                "  catch (error) { value = 'ERROR:' + error.constructor.name; }\n"
                "  console.log('AEGISPR_OUTPUT=' + JSON.stringify(value));\n"
                "}\n"
            )
            (workspace / "probe.mjs").write_text(probe, encoding="utf-8")
            command = [node, "probe.mjs"]
        environment = {
            "PATH": os.defpath, "HOME": temporary, "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
        }
        execution = subprocess.run(
            command, cwd=workspace, env=environment, capture_output=True, text=True, timeout=5,
        )
        if execution.returncode != 0 or len(execution.stdout) > 20_000 or len(execution.stderr) > 20_000:
            raise ValueError(f"Fixture execution failed: {case.id} {branch}")
        observations = []
        for line in execution.stdout.splitlines():
            if not line.startswith("AEGISPR_OUTPUT="):
                raise ValueError(f"Fixture emitted unlabeled output: {case.id} {branch}")
            observations.append(json.loads(line.removeprefix("AEGISPR_OUTPUT=")))
        if len(observations) != len(case.arguments):
            raise ValueError(f"Fixture observation count changed: {case.id} {branch}")
        return observations


def validate_cases(cases: list[SeededCase]) -> dict[str, int]:
    for case in cases:
        if observe_case(case, "base") != case.expected_base or observe_case(case, "head") != case.expected_head:
            raise ValueError(f"Fixture ground truth changed: {case.id}")
    counts = Counter(case.intent for case in cases)
    return {
        "cases": len(cases), "unintended": counts["unintended"],
        "intended": counts["intended"], "no_change": counts["no_change"],
        "fixtures_verified": len(cases), "model_runs": 0,
    }
