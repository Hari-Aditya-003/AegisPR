from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass


@dataclass(frozen=True)
class Mutation:
    source: str
    operator: str


_FLIPS = {">": ">=", ">=": ">", "<": "<=", "<=": "<", "==": "!=", "!=": "=="}
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def changed_python_lines(diff: str) -> dict[str, list[int]]:
    changes: dict[str, list[int]] = {}
    path: str | None = None
    line_number: int | None = None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            path = None
            line_number = None
        elif line.startswith("+++ b/"):
            candidate = line[6:]
            path = candidate if candidate.endswith(".py") else None
            if path:
                changes.setdefault(path, [])
        elif line.startswith("@@ "):
            match = _HUNK.match(line)
            line_number = int(match.group(1)) if match else None
        elif path and line_number is not None:
            if line.startswith("+") and not line.startswith("+++"):
                changes[path].append(line_number)
                line_number += 1
            elif line.startswith(" "):
                line_number += 1
    return {path: lines for path, lines in changes.items() if lines}


def mutate_python_line(source: str, line_number: int) -> Mutation | None:
    lines = source.splitlines(keepends=True)
    if line_number < 1 or line_number > len(lines):
        return None
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.start[0] != line_number or token.type != tokenize.OP or token.string not in _FLIPS:
                continue
            replacement = _FLIPS[token.string]
            old = lines[line_number - 1]
            lines[line_number - 1] = old[: token.start[1]] + replacement + old[token.end[1]:]
            return Mutation("".join(lines), f"{token.string} to {replacement}")
    except (tokenize.TokenError, IndentationError):
        return None
    return None
