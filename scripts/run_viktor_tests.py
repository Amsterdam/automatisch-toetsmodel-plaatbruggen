#!/usr/bin/env python3
"""VIKTOR test runner with enhanced output and error reporting."""

import os
import subprocess
import sys
from pathlib import Path

# Add the project root to Python path to access test utils
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_utils import (  # noqa: E402
    Colors,
    colored_text,
    colorized_status_message,
    safe_arrow,
    safe_emoji_text,
    should_use_concise_mode,
)


def handle_viktor_concise_output(result: subprocess.CompletedProcess) -> None:
    """Handle VIKTOR test output in concise mode for git hooks."""
    # Combine stdout and stderr for analysis
    output = (result.stdout or "") + (result.stderr or "")
    lines = output.strip().split("\n") if output else []

    if result.returncode == 0:
        safe_emoji_text("✅ VIKTOR TESTS PASSED!", "VIKTOR TESTS PASSED!")
        print(colorized_status_message("All VIKTOR view tests completed successfully", is_success=True))  # noqa: T201
    else:
        safe_emoji_text("❌ VIKTOR TESTS FAILED", "VIKTOR TESTS FAILED")

        # Try to extract test failure information
        failed_tests = [line for line in lines if "FAILED" in line or "ERROR" in line]
        if failed_tests:
            print(colorized_status_message(f"Found {len(failed_tests)} failed VIKTOR tests", is_success=False))  # noqa: T201
        else:
            print(colorized_status_message("VIKTOR test execution failed", is_success=False))  # noqa: T201

        print(colorized_status_message("Run the following command for detailed VIKTOR test information:", is_success=False, is_warning=True))  # noqa: T201
        print(f"  {safe_arrow()}{colored_text('viktor-cli test', Colors.CYAN, bold=True)}")  # noqa: T201


def handle_viktor_detailed_output(result: subprocess.CompletedProcess) -> None:
    """Handle VIKTOR test output in detailed mode for manual runs."""
    # In detailed mode, show full output
    if result.stdout:
        print(result.stdout)  # noqa: T201
    if result.stderr:
        print(result.stderr, file=sys.stderr)  # noqa: T201


def run_viktor_tests() -> int:
    """Run VIKTOR tests and provide enhanced output."""
    # Use the improved environment detection from test_utils
    force_concise = should_use_concise_mode()

    # Enable colors for Git environments (like Git Bash) even if detection is conservative
    if any(os.environ.get(var) for var in ["MSYSTEM", "MINGW_PREFIX", "TERM"]):
        os.environ["FORCE_COLOR"] = "1"

    try:
        result = subprocess.run(
            ["viktor-cli", "test"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=project_root,
            check=False,
        )

        if force_concise:
            handle_viktor_concise_output(result)
        else:
            handle_viktor_detailed_output(result)

    except FileNotFoundError:
        safe_emoji_text("❌ VIKTOR-CLI NOT FOUND", "VIKTOR-CLI NOT FOUND")
        print(colorized_status_message("viktor-cli command not found. Please install VIKTOR CLI:", is_success=False))  # noqa: T201
        print(f"  {safe_arrow()}{colored_text('viktor-cli install', Colors.CYAN, bold=True)}")  # noqa: T201
        return 1
    except Exception as e:
        safe_emoji_text("❌ VIKTOR TEST EXECUTION FAILED", "VIKTOR TEST EXECUTION FAILED")
        print(colorized_status_message(f"Error running VIKTOR tests: {e}", is_success=False))  # noqa: T201
        return 1
    else:
        return result.returncode


if __name__ == "__main__":
    sys.exit(run_viktor_tests())
