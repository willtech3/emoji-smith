"""Pytest configuration for the Emoji Smith test-suite.

This file ensures that the *src*-layout package is importable when the project
is tested without being installed in editable/development mode.  It adjusts
``sys.path`` at collection time so that ``import emojismith`` works regardless
of whether the caller remembered to run ``pip install -e .`` first.

The logic is intentionally *very* small to avoid masking real import errors --
it only prepends the absolute path to the *src* directory if it is not already
on ``sys.path``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"

# Prepend to sys.path (keeping any editable-install entries untouched)
src_str = str(SRC_PATH)
if src_str not in sys.path:
    sys.path.insert(0, src_str)

# Nothing to expose as fixtures - the sole purpose is import side-effects.
