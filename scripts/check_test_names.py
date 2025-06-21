#!/usr/bin/env python3
"""Ensure test functions follow naming convention."""
from __future__ import annotations
import re
from pathlib import Path
import sys

PATTERN = re.compile(r"^(async\s+def|def)\s+(test_[A-Za-z0-9_]+)\(")

errors = []
for path in Path("tests").rglob("test_*.py"):
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        m = PATTERN.match(line.strip())
        if m:
            name = m.group(2)
            parts = name.split("_")[1:]
            if len(parts) < 3:
                errors.append(
                    f"{path}:{i}: '{name}' should follow "
                    "test_<unit>_<scenario>_<expected>"
                )

if errors:
    print("Test naming violations detected:\n" + "\n".join(errors))
    sys.exit(1)
