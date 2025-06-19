#!/usr/bin/env python3
"""
Quality Check and Push Script - RUFT (Ruff-based Universal Fixer Tool).

This script replaces pre-commit hooks with a transparent workflow:
1. Runs all quality checks (Ruff, MyPy, tests)
2. Auto-fixes what it can (Ruff formatting/style)
3. Re-commits any fixes
4. Repeats until no more auto-fixes are possible
5. Shows final status and pushes if everything passes

Usage:
    python ruft.py [--dry-run] [--no-push]
"""

import subprocess
import sys
from pathlib import Path

# Run the main script
script_path = Path(__file__).parent / "scripts" / "quality_check_and_push.py"
cmd = [sys.executable, str(script_path)] + sys.argv[1:]
sys.exit(subprocess.call(cmd))
