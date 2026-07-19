from __future__ import annotations

import os
import sys
from pathlib import Path

# Add vendored back-end dependency directory to sys.path so tests and app imports work
CURRENT_DIR = Path(__file__).resolve().parent
DEPS_DIR = CURRENT_DIR / "deps"
if DEPS_DIR.exists() and str(DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(DEPS_DIR))
