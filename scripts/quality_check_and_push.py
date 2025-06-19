#!/usr/bin/env python3
"""
Quality Check and Push Script.

This script replaces pre-commit hooks with a transparent workflow:
1. Runs all quality checks (Ruff, MyPy, tests)
2. Auto-fixes what it can (Ruff formatting/style)
3. Re-commits any fixes
4. Repeats until no more auto-fixes are possible
5. Shows final status and pushes if everything passes

Usage:
    python scripts/quality_check_and_push.py [--dry-run] [--no-push]
"""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# Set UTF-8 encoding for Windows compatibility
if sys.platform == "win32":
    import os

    os.environ["PYTHONIOENCODING"] = "utf-8"


class CheckResult(NamedTuple):
    """Result of running a quality check."""

    name: str
    passed: bool
    can_auto_fix: bool
    command: str
    output: str
    error_count: int = 0
    error_details: str = ""


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[1;31m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[1;34m"
    CYAN = "\033[1;36m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def parse_error_details(name: str, output: str) -> tuple[int, str]:
    """Parse error details from command output to get count and summary."""
    error_count = 0
    error_details = ""

    if "Ruff" in name:
        # Parse Ruff output for error count
        # Look for "Found X errors" pattern first (most reliable)
        found_match = re.search(r"Found (\d+) errors?", output)
        if found_match:
            error_count = int(found_match.group(1))
        else:
            # Fallback: count individual error lines
            error_lines = [
                line
                for line in output.split("\n")
                if line.strip() and ".py:" in line and ("error" in line.lower() or "E" in line or "F" in line or "I" in line or "W" in line)
            ]
            error_count = len(error_lines)

        # Look for additional info about fixable errors
        if error_count > 0:
            # Look for patterns like "Found 5 errors (3 fixed, 2 remaining)" or "Found 10 errors"
            fixed_remaining_match = re.search(r"Found \d+ errors \((\d+) fixed, (\d+) remaining\)", output)
            if fixed_remaining_match:
                fixed_count = int(fixed_remaining_match.group(1))
                remaining_count = int(fixed_remaining_match.group(2))
                error_details = f"{fixed_count} auto-fixed, {remaining_count} remaining"
            else:
                # Look for "X fixable with ruff check --fix" pattern
                fixable_match = re.search(r"(\d+) fixable", output)
                if fixable_match:
                    fixable_count = int(fixable_match.group(1))
                    if fixable_count > 0:
                        error_details = "all auto-fixable" if fixable_count == error_count else f"{fixable_count} auto-fixable"

    elif "MyPy" in name:
        # Parse MyPy output for error count
        error_lines = [line for line in output.split("\n") if "error:" in line]
        error_count = len(error_lines)

        if error_count > 0:
            # Get first few error types as summary
            error_types = set()
            for line in error_lines[:3]:  # Show up to 3 different error types
                if "error:" in line:
                    error_part = line.split("error:")[1].strip()
                    # Extract error type in brackets [error-type] or first meaningful words
                    bracket_match = re.search(r"\[([^\]]+)\]", error_part)
                    error_type = bracket_match.group(1) if bracket_match else error_part.split(".")[0].split("(")[0].strip()
                    error_types.add(error_type)
            error_details = ", ".join(list(error_types)[:2])  # Show up to 2 error types

    elif "Unit Tests" in name:
        # Parse test output for failure count
        if "FAILED" in output:
            failed_match = re.search(r"(\d+) failed", output)
            if failed_match:
                error_count = int(failed_match.group(1))
                error_details = "test failures"
        elif "ERROR" in output:
            error_match = re.search(r"(\d+) error", output)
            if error_match:
                error_count = int(error_match.group(1))
                error_details = "test errors"

    return error_count, error_details


def run_command(command: str, capture_output: bool = True) -> tuple[int, str]:
    """Run a shell command and return exit code and output."""
    try:
        if capture_output:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                check=False,
                encoding="utf-8",
                errors="replace",
            )
            return result.returncode, result.stdout + result.stderr
        # For commands we want to show live output
        result = subprocess.run(command, shell=True, cwd=Path.cwd(), check=False, text=True)
        return result.returncode, ""
    except Exception as e:
        return 1, f"Error running command: {e}"


def check_git_status() -> bool:
    """Check if there are uncommitted changes."""
    exit_code, output = run_command("git status --porcelain")
    return len(output.strip()) > 0


def commit_changes(message: str) -> bool:
    """Commit all changes with the given message."""
    print(f"{Colors.BLUE}[*] Committing changes: {message}{Colors.RESET}")

    # Add all changes
    print(f"{Colors.CYAN}[>] Staging changes...{Colors.RESET}")
    exit_code, _ = run_command("git add .")
    if exit_code != 0:
        print(f"{Colors.RED}[X] Failed to stage changes{Colors.RESET}")
        return False

    # Commit changes - use subprocess list to avoid shell quote issues
    print(f"{Colors.CYAN}[>] Creating commit...{Colors.RESET}")
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        exit_code = result.returncode
        output = result.stdout + result.stderr
    except Exception as e:
        print(f"{Colors.RED}[X] Failed to commit changes{Colors.RESET}")
        print(f"{Colors.RED}    Error: {e}{Colors.RESET}")
        return False

    if exit_code != 0:
        print(f"{Colors.RED}[X] Failed to commit changes{Colors.RESET}")
        print(f"{Colors.RED}    Error: {output.strip()}{Colors.RESET}")
        return False

    print(f"{Colors.GREEN}[+] Changes committed successfully{Colors.RESET}")
    return True


def run_quality_check(name: str, command: str, can_auto_fix: bool = False) -> CheckResult:
    """Run a single quality check and return the result."""
    print(f"{Colors.CYAN}[>] Running {name}...{Colors.RESET}")
    exit_code, output = run_command(command)
    passed = exit_code == 0

    # Parse error details
    error_count, error_details = parse_error_details(name, output)

    if passed:
        status = f"{Colors.GREEN}[+] PASSED"
    else:
        status = f"{Colors.RED}[X] FAILED"
        if error_count > 0:
            status += f" - Found {error_count} error{'s' if error_count != 1 else ''}"
            if error_details:
                status += f" ({error_details})"

    print(f"    {status}{Colors.RESET}")

    return CheckResult(
        name=name, passed=passed, can_auto_fix=can_auto_fix, command=command, output=output, error_count=error_count, error_details=error_details
    )


def get_git_diff_hash() -> str:
    """Get a hash of the current git diff to detect changes."""
    exit_code, diff_output = run_command("git diff")
    if exit_code != 0:
        return ""
    return hashlib.md5(diff_output.encode()).hexdigest()


def print_final_status_report(all_checks: list[CheckResult]) -> list[CheckResult]:
    """Print the final status report and return failed checks."""
    print(f"\n{Colors.BOLD}>> Final Status Report{Colors.RESET}")
    print("=" * 60)

    failed_checks = []

    for check in all_checks:
        if check.passed:
            status = f"{Colors.GREEN}[+] PASSED"
        else:
            status = f"{Colors.RED}[X] FAILED"
            if check.error_count > 0:
                status += f" - Found {check.error_count} error{'s' if check.error_count != 1 else ''}"
                if check.error_details:
                    status += f" ({check.error_details})"
            failed_checks.append(check)

        print(f"  {check.name}: {status}{Colors.RESET}")

    return failed_checks


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(description="Run quality checks and push")
    parser.add_argument("--dry-run", action="store_true", help="Don't commit or push, just show what would happen")
    parser.add_argument("--no-push", action="store_true", help="Run checks and commit fixes, but don't push")
    args = parser.parse_args()

    print(f"{Colors.BOLD}>> Starting Quality Check and Push Workflow{Colors.RESET}")
    print("=" * 60)

    # Check if we're in a git repository
    exit_code, _ = run_command("git rev-parse --git-dir")
    if exit_code != 0:
        print(f"{Colors.RED}[X] Not in a git repository{Colors.RESET}")
        return 1

    # Check for uncommitted changes
    if check_git_status():
        print(f"{Colors.YELLOW}[!] Uncommitted changes detected{Colors.RESET}")
        if not args.dry_run:
            response = input(f"{Colors.CYAN}Commit all changes before quality checks? (y/N): {Colors.RESET}").strip().lower()
            if response in ("y", "yes"):
                commit_message = input(f"{Colors.CYAN}Enter commit message: {Colors.RESET}").strip()
                print(f"{Colors.YELLOW}[*] Processing commit...{Colors.RESET}", flush=True)
                if not commit_message:
                    commit_message = "Manual changes before quality checks"
                if not commit_changes(commit_message):
                    return 1
            else:
                print(f"{Colors.YELLOW}[i] Proceeding with uncommitted changes (only auto-fixes will be committed){Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}[DRY RUN] Would prompt to commit uncommitted changes{Colors.RESET}")

    max_iterations = 3  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n{Colors.BOLD}>> Iteration {iteration}{Colors.RESET}")
        print("-" * 40)

        # Track if we made any auto-fixes this iteration
        made_fixes = False

        # Get git diff hash before running Ruff
        diff_hash_before = get_git_diff_hash()

        # 1. Run Ruff style check (can auto-fix)
        ruff_check = run_quality_check("Ruff Style Check", "python scripts/run_ruff_check.py", can_auto_fix=True)

        # 2. Run Ruff formatter (can auto-fix)
        ruff_format = run_quality_check("Ruff Formatter", "python scripts/run_ruff_format.py", can_auto_fix=True)

        # Get git diff hash after running Ruff
        diff_hash_after = get_git_diff_hash()

        # If the diff hash changed, it means Ruff made changes
        if diff_hash_before != diff_hash_after:
            print(f"{Colors.YELLOW}[!] Ruff made auto-fixes{Colors.RESET}")
            made_fixes = True

            if not args.dry_run:
                if not commit_changes(f"Auto-fix: Ruff style and formatting (iteration {iteration})"):
                    return 1
            else:
                print(f"{Colors.YELLOW}[DRY RUN] Would commit Ruff auto-fixes{Colors.RESET}")

        # 3. Run MyPy (cannot auto-fix)
        mypy_check = run_quality_check("MyPy Type Check", "python scripts/run_mypy.py", can_auto_fix=False)

        # 4. Run unit tests (cannot auto-fix)
        test_check = run_quality_check("Unit Tests", "python scripts/run_enhanced_tests.py", can_auto_fix=False)

        # If no auto-fixes were made, we're done with iterations
        if not made_fixes:
            print(f"{Colors.CYAN}[i] No auto-fixes applied this iteration, proceeding to final report{Colors.RESET}")
            break

        print(f"{Colors.YELLOW}[!] Auto-fixes applied, running checks again...{Colors.RESET}")

    # Final status report
    all_checks = [ruff_check, ruff_format, mypy_check, test_check]
    failed_checks = print_final_status_report(all_checks)

    # If there are failures that can't be auto-fixed
    if failed_checks:
        print(f"\n{Colors.RED}[X] Some checks failed and cannot be auto-fixed:{Colors.RESET}")
        print(f"{Colors.YELLOW}To investigate and fix manually, run:{Colors.RESET}")
        for check in failed_checks:
            print(f"  {Colors.CYAN}{check.command}{Colors.RESET}  # Fix {check.name}")
        print(f"\n{Colors.YELLOW}Fix these issues and run this script again.{Colors.RESET}")
        return 1

    # All checks passed!
    print(f"\n{Colors.GREEN}[+] All quality checks passed!{Colors.RESET}")

    # Push changes
    if not args.no_push and not args.dry_run:
        print(f"{Colors.BLUE}[>] Pushing changes...{Colors.RESET}")
        exit_code, output = run_command("git push", capture_output=False)
        if exit_code != 0:
            print(f"{Colors.RED}[X] Failed to push changes{Colors.RESET}")
            return 1
        print(f"{Colors.GREEN}[+] Changes pushed successfully!{Colors.RESET}")
    elif args.dry_run:
        print(f"{Colors.YELLOW}[DRY RUN] Would push changes{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}[*] Changes ready to push (use 'git push' manually){Colors.RESET}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
