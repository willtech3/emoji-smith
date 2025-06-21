#!/usr/bin/env python
"""Verify pytest test names follow the required convention."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

PATTERN = re.compile(r"^test_[a-z0-9]+_[a-z0-9]+_[a-z0-9_]+$")


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError as exc:  # pragma: no cover - malformed test file
        errors.append(f"{path}:{exc.lineno}: syntax error")
        return errors

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if name.startswith("test_") and not PATTERN.fullmatch(name):
                errors.append(
                    f"{path}:{node.lineno} invalid test name '{name}'"
                )
    return errors


def main() -> int:
    root = Path("tests")
    failures: list[str] = []
    for file in root.rglob("test_*.py"):
        failures.extend(validate_file(file))
    if failures:
        for failure in failures:
            print(failure)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
