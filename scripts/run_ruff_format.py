#!/usr/bin/env python3
"""Ruff format wrapper with enhanced messaging for git hooks."""

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


def setup_environment() -> bool:
    """Set up environment and determine if concise mode should be used."""
    # Use the improved environment detection from test_utils
    force_concise = should_use_concise_mode()

    # Enable colors for Git environments (like Git Bash) even if detection is conservative
    if any(os.environ.get(var) for var in ["MSYSTEM", "MINGW_PREFIX", "TERM"]):
        os.environ["FORCE_COLOR"] = "1"

    return force_concise


def extract_format_stats(lines: list[str]) -> tuple[int, int]:
    """Extract formatting statistics from ruff format output."""
    reformatted = 0
    unchanged = 0

    for line in lines:
        if "reformatted" in line.lower() and "unchanged" in line.lower():
            # Parse line like "1 file reformatted, 56 files left unchanged"
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part in {"file", "files"} and i > 0 and parts[i - 1].isdigit():
                        if "reformatted" in line[: line.index(part)]:
                            reformatted = int(parts[i - 1])
                        elif "unchanged" in line[line.index(part) :]:
                            unchanged = int(parts[i - 1])
            except (IndexError, ValueError):
                pass

    return reformatted, unchanged


def auto_commit_formatting_changes(reformatted_count: int) -> bool:
    """Automatically commit formatting changes and return success status."""
    try:
        # Stage all changes (ruff format only modifies existing files)
        subprocess.run(
            ["git", "add", "-u"],  # -u only stages modified files, not new ones
            cwd=project_root,
            check=True,
            capture_output=True,
        )

        # Commit with a clear message
        commit_msg = f"Auto-format code with ruff ({reformatted_count} file{'s' if reformatted_count != 1 else ''} reformatted)"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=project_root,
            check=True,
            capture_output=True,
        )

    except subprocess.CalledProcessError:
        return False
    else:
        return True


def show_auto_format_message(reformatted: int, force_concise: bool, result: subprocess.CompletedProcess) -> None:
    """Display auto-formatting message."""
    if force_concise:
        safe_emoji_text("🔧 AUTO-FORMATTING CODE", "AUTO-FORMATTING CODE")
        print(colorized_status_message(f"Reformatted {reformatted} file(s)", is_success=True, is_warning=True))  # noqa: T201
    else:
        if result.stdout:
            print(result.stdout)  # noqa: T201
        print()  # noqa: T201
        print(colored_text("🔧 Auto-formatting code...", Colors.YELLOW, bold=True))  # noqa: T201


def show_auto_commit_success(force_concise: bool) -> None:
    """Display auto-commit success message."""
    if force_concise:
        print(colorized_status_message("Formatting changes committed automatically", is_success=True))  # noqa: T201
        safe_emoji_text("✅ CONTINUING WITH PUSH", "CONTINUING WITH PUSH")
    else:
        print(colored_text("✅ Formatting changes committed automatically", Colors.GREEN, bold=True))  # noqa: T201
        print(colored_text("Continuing with push...", Colors.GREEN))  # noqa: T201


def show_auto_commit_failure(force_concise: bool) -> None:
    """Display auto-commit failure with manual instructions."""
    if force_concise:
        safe_emoji_text("❌ AUTO-COMMIT FAILED", "AUTO-COMMIT FAILED")
        print(colorized_status_message("Please commit formatting changes manually:", is_success=False, is_warning=True))  # noqa: T201
        print(f"  {safe_arrow()}{colored_text('git add .', Colors.CYAN, bold=True)}")  # noqa: T201
        print(f"  {safe_arrow()}{colored_text('git commit -m "Apply code formatting"', Colors.CYAN, bold=True)}")  # noqa: T201
        print(f"  {safe_arrow()}{colored_text('git push', Colors.CYAN, bold=True)}")  # noqa: T201
    else:
        print(colored_text("❌ Failed to auto-commit formatting changes", Colors.RED, bold=True))  # noqa: T201
        print(colored_text("Please commit the changes manually:", Colors.YELLOW))  # noqa: T201
        print(f"  {colored_text('git add .', Colors.CYAN)}")  # noqa: T201
        print(f"  {colored_text('git commit -m "Apply code formatting"', Colors.CYAN)}")  # noqa: T201
        print(f"  {colored_text('git push', Colors.CYAN)}")  # noqa: T201


def handle_auto_format_success(reformatted: int, force_concise: bool, result: subprocess.CompletedProcess) -> int:
    """Handle successful auto-formatting with potential auto-commit."""
    show_auto_format_message(reformatted, force_concise, result)

    # Attempt to auto-commit the changes
    if auto_commit_formatting_changes(reformatted):
        show_auto_commit_success(force_concise)
        return 0  # Success - continue with push

    # Auto-commit failed - fall back to manual instructions
    show_auto_commit_failure(force_concise)
    return 1  # Failure - stop push


def handle_concise_output(result: subprocess.CompletedProcess) -> None:
    """Handle output in concise mode for git hooks."""
    output = (result.stdout or "") + (result.stderr or "")
    lines = output.strip().split("\n") if output else []

    reformatted, _ = extract_format_stats(lines)

    # Check if files were actually reformatted (regardless of exit code)
    if reformatted > 0:
        # Files were reformatted
        safe_emoji_text("🔧 FILES REFORMATTED", "FILES REFORMATTED")
        print(colorized_status_message(f"Reformatted {reformatted} file(s)", is_success=False, is_warning=True))  # noqa: T201
        print()  # noqa: T201
        print(colorized_status_message("Files have been automatically reformatted!", is_success=False, is_warning=True))  # noqa: T201
        print(colorized_status_message("Please commit the changes and push again:", is_success=False, is_warning=True))  # noqa: T201
        print()  # noqa: T201
        print(f"  {safe_arrow()}{colored_text('git add .', Colors.CYAN, bold=True)}")  # noqa: T201
        print(f"  {safe_arrow()}{colored_text('git commit -m "Apply code formatting"', Colors.CYAN, bold=True)}")  # noqa: T201
        print(f"  {safe_arrow()}{colored_text('git push', Colors.CYAN, bold=True)}")  # noqa: T201
    elif result.returncode == 0:
        safe_emoji_text("✅ RUFF FORMAT PASSED!", "RUFF FORMAT PASSED!")
        print(colorized_status_message("Code formatting is consistent", is_success=True))  # noqa: T201
    else:
        safe_emoji_text("❌ RUFF FORMAT FAILED", "RUFF FORMAT FAILED")
        print(colorized_status_message("Code formatting failed - check the output above", is_success=False))  # noqa: T201


def run_ruff_format() -> int:
    """Run ruff format and provide enhanced messaging."""
    force_concise = setup_environment()

    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--config=.ruff.toml"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=project_root,
            check=False,
        )

        # Check if files were reformatted
        output = (result.stdout or "") + (result.stderr or "")
        lines = output.strip().split("\n") if output else []
        reformatted, _ = extract_format_stats(lines)

        if reformatted > 0 and result.returncode == 0:
            return handle_auto_format_success(reformatted, force_concise, result)

        if force_concise:
            handle_concise_output(result)
        elif result.stdout:
            print(result.stdout)  # noqa: T201

        if result.stderr:
            print(result.stderr, file=sys.stderr)  # noqa: T201

    except Exception as e:
        safe_emoji_text("❌ RUFF FORMAT EXECUTION FAILED", "RUFF FORMAT EXECUTION FAILED")
        print(f"Error running ruff format: {e}")  # noqa: T201
        return 1
    else:
        return result.returncode


if __name__ == "__main__":
    sys.exit(run_ruff_format())
