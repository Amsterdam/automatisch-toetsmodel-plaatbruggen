#!/usr/bin/env python3
"""MyPy wrapper with concise summary for git hooks."""

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


def handle_mypy_concise_output(result: subprocess.CompletedProcess) -> None:
    """Handle MyPy output in concise mode for git hooks."""
    # Combine stdout and stderr for analysis
    output = (result.stdout or "") + (result.stderr or "")
    lines = output.strip().split("\n") if output else []

    if result.returncode == 0:
        safe_emoji_text("✅ MYPY CHECK PASSED!", "MYPY CHECK PASSED!")
        print(colorized_status_message("No type checking issues found", is_success=True))  # noqa: T201
    else:
        safe_emoji_text("❌ MYPY CHECK FAILED", "MYPY CHECK FAILED")

        # Count errors from output
        error_lines = [line for line in lines if ": error:" in line]
        error_count = len(error_lines)
        note_lines = [line for line in lines if ": note:" in line]
        note_count = len(note_lines)

        if error_count > 0 or note_count > 0:
            print(colorized_status_message(f"Found {error_count} errors, {note_count} notes", is_success=False))  # noqa: T201
            print(  # noqa: T201
                colorized_status_message("Run the following command for detailed type checking information:", is_success=False, is_warning=True)
            )
            print(f"  {safe_arrow()}{colored_text('python scripts/run_mypy.py', Colors.CYAN, bold=True)}")  # noqa: T201
        else:
            print(  # noqa: T201
                colorized_status_message(
                    "Type checking failed - run the following command for detailed type checking information:",
                    is_success=False,
                    is_warning=True,
                )
            )
            print(f"  {safe_arrow()}{colored_text('python scripts/run_mypy.py', Colors.CYAN, bold=True)}")  # noqa: T201


def handle_mypy_detailed_output(result: subprocess.CompletedProcess) -> None:
    """Handle MyPy output in detailed mode for manual runs."""
    # In detailed mode, show full output with improved formatting
    if result.stdout:
        # Process each line to add colors
        lines = result.stdout.split("\n")
        for line in lines:
            if not line.strip():
                continue

            # Color file paths and line numbers differently from error messages
            if ": error:" in line or ": note:" in line:
                # Split line into file:line and error message
                if ": error:" in line:
                    parts = line.split(": error:", 1)
                    if len(parts) == 2:
                        file_part = parts[0]
                        error_part = parts[1]
                        print(  # noqa: T201
                            f"{(file_part)}: {colored_text('error:', Colors.RED, bold=True)}{colored_text(error_part, Colors.RED)}"
                        )
                        continue
                elif ": note:" in line:
                    parts = line.split(": note:", 1)
                    if len(parts) == 2:
                        file_part = parts[0]
                        note_part = parts[1]
                        print(  # noqa: T201
                            f"{(file_part)}: {colored_text('note:', Colors.BLUE, bold=True)}{colored_text(note_part, Colors.BLUE)}"
                        )
                        continue

            # Default case - print as is (like summary lines)
            print(line)  # noqa: T201
    if result.stderr:
        print(result.stderr, file=sys.stderr)  # noqa: T201


def run_mypy() -> int:
    """Run mypy and provide concise summary."""
    # Use the improved environment detection from test_utils
    force_concise = should_use_concise_mode()

    # Enable colors for Git environments (like Git Bash) even if detection is conservative
    if any(os.environ.get(var) for var in ["MSYSTEM", "MINGW_PREFIX", "TERM"]):
        os.environ["FORCE_COLOR"] = "1"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "."], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=project_root, check=False
        )

        if force_concise:
            handle_mypy_concise_output(result)
        else:
            handle_mypy_detailed_output(result)

    except Exception as e:
        safe_emoji_text("❌ MYPY EXECUTION FAILED", "MYPY EXECUTION FAILED")
        print(colorized_status_message(f"Error running mypy: {e}", is_success=False))  # noqa: T201
        return 1
    else:
        return result.returncode


if __name__ == "__main__":
    sys.exit(run_mypy())
