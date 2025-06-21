#!/usr/bin/env python
"""Fail if any test function name does not follow naming convention."""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def collect_test_functions(path: Path) -> list[tuple[str, int]]:
    """Return list of (name, line) for test functions in file."""
    functions: list[tuple[str, int]] = []
    try:
        tree = ast.parse(path.read_text())
    except Exception as exc:  # pragma: no cover - syntax errors should fail
        raise RuntimeError(f"Failed to parse {path}: {exc}") from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            functions.append((node.name, node.lineno))
    return functions


def main(paths: list[str]) -> int:
    base_paths = [Path(p) for p in paths]
    if not base_paths:
        base_paths = [Path("tests")]

    violations: list[str] = []
    for base in base_paths:
        files = [base] if base.is_file() else list(base.rglob("test_*.py"))
        for file in files:
            for name, line in collect_test_functions(file):
                if name.count("_") < 3:  # test + at least unit + scenario + result
                    violations.append(f"{file}:{line} {name}")
    if violations:
        print("Test naming violations found:")
        for v in violations:
            print(v)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
