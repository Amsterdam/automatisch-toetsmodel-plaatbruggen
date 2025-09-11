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
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

# Set UTF-8 encoding for Windows compatibility
if sys.platform == "win32":
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

        elif "Tests" in name:
            # Parse test output for failure/error counts (works for pytest and unittest)
            # Look for pytest format first
            pytest_failed = re.search(r"(\d+) failed", output)
            pytest_error = re.search(r"(\d+) error", output)
            pytest_passed = re.search(r"(\d+) passed", output)
            pytest_collected = re.search(r"(\d+) collected", output)

            if pytest_failed:
                error_count = int(pytest_failed.group(1))
                error_details = "test failures"
            if pytest_error:
                error_count = max(error_count, 0) + int(pytest_error.group(1))
                error_details = error_details if error_details else "test errors"

            # For pytest, try to get total and passed counts for better error details
            if pytest_collected and (pytest_failed or pytest_error):
                total_tests = int(pytest_collected.group(1))
                passed_tests = int(pytest_passed.group(1)) if pytest_passed else 0
                if error_details:
                    error_details = f"{passed_tests}/{total_tests} passed, {error_details}"

            # Fallback to unittest format if pytest didn't find anything
            if error_count == 0:
                if "FAILED" in output:
                    failed_match = re.search(r"(\d+) failed", output)
                    if failed_match:
                        error_count = int(failed_match.group(1))
                        error_details = "test failures"
                if "ERROR" in output:
                    error_match = re.search(r"(\d+) error", output)
                    if error_match:
                        error_count = max(error_count, 0) + int(error_match.group(1))
                        error_details = error_details if error_details else "test errors"

                # For unittest, try to get total count
                unittest_total = re.search(r"Ran (\d+) test", output)
                if unittest_total and error_count > 0:
                    total_tests = int(unittest_total.group(1))
                    passed_tests = total_tests - error_count
                    if error_details:
                        error_details = f"{passed_tests}/{total_tests} passed, {error_details}"

    return error_count, error_details


def run_command(command: str, capture_output: bool = True) -> tuple[int, str]:
    """Run a shell command and return exit code and output."""
    try:
        if capture_output:
            # Enhanced capture for viktor-cli to prevent subprocess leaks
            if "viktor-cli" in command:
                # Use most aggressive capture possible for viktor-cli
                # Create a completely isolated environment
                env = dict(os.environ)
                env.update(
                    {
                        "PYTHONUNBUFFERED": "1",
                        "GIT_TERMINAL_PROMPT": "0",  # Disable git prompts
                        "GIT_ASKPASS": "echo",  # Disable git password prompts
                    }
                )

                # Additional isolation (Unix only - Windows doesn't support setsid)
                if os.name != "nt" and hasattr(os, "setsid"):
                    result = subprocess.run(  # noqa: UP022
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,  # Capture stderr separately first
                        stdin=subprocess.DEVNULL,  # Prevent any input
                        text=True,
                        cwd=Path.cwd(),
                        check=False,
                        encoding="utf-8",
                        errors="replace",
                        env=env,
                        preexec_fn=os.setsid,
                    )
                else:
                    result = subprocess.run(  # noqa: UP022
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,  # Capture stderr separately first
                        stdin=subprocess.DEVNULL,  # Prevent any input
                        text=True,
                        cwd=Path.cwd(),
                        check=False,
                        encoding="utf-8",
                        errors="replace",
                        env=env,
                    )
                # Combine all output
                combined_output = (result.stdout or "") + (result.stderr or "")
                return result.returncode, combined_output
            # Standard capture for other commands
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


def safe_input(prompt: str, max_attempts: int = 3) -> str:
    """Safely get user input with retry logic for different terminals."""

    def _attempt_input() -> str:
        """Single input attempt."""
        # Ensure clean state before prompting
        sys.stdout.flush()
        sys.stderr.flush()

        # Clear any remaining spinner artifacts
        print("\r" + " " * 80 + "\r", end="", flush=True)

        # Use traditional input() which works better across terminals (direct return fixes RET504)
        return input(prompt).strip()

    def _handle_attempt(attempt_num: int) -> str | None:
        """Handle a single input attempt. Returns result or None to continue."""
        try:
            return _attempt_input()
        except (EOFError, KeyboardInterrupt):
            if attempt_num < max_attempts - 1:
                print(f"\n{Colors.YELLOW}[!] Input interrupted, retrying... (Ctrl+C again to cancel){Colors.RESET}")
                time.sleep(0.5)
                return None  # Continue to next attempt
            print(f"\n{Colors.YELLOW}[!] Input cancelled, proceeding with default behavior{Colors.RESET}")
            return ""
        except Exception as e:
            if attempt_num < max_attempts - 1:
                print(f"\n{Colors.YELLOW}[!] Input error ({e}), retrying...{Colors.RESET}")
                time.sleep(0.5)
                return None  # Continue to next attempt
            print(f"\n{Colors.YELLOW}[!] Input failed, proceeding with default behavior{Colors.RESET}")
            return ""

    # Try each attempt separately to avoid PERF203
    for attempt in range(max_attempts):
        result = _handle_attempt(attempt)
        if result is not None:
            return result

    return ""


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


def run_quality_check_with_progress(name: str, command: str, can_auto_fix: bool = False) -> CheckResult:
    """Run a single quality check with live progress indication."""
    import itertools
    import threading
    import time

    print(f"{Colors.CYAN}[>] Running {name}...{Colors.RESET}", end="", flush=True)
    start_time = time.time()

    # Progress indicator for longer operations
    spinner = itertools.cycle(["|", "/", "-", "\\"])
    stop_spinner = threading.Event()

    def show_spinner() -> None:
        """Show animated spinner while operation is running."""
        # Test encoding support once before the loop (PERF203 fix)
        use_colors = True
        use_spinner = True
        try:
            print(f"\r{Colors.CYAN}[>] Running {name}... |{Colors.RESET}", end="", flush=True)
        except UnicodeEncodeError:
            use_colors = False

        # Test spinner support once before the loop
        try:
            test_spinner_char = next(spinner)
            if use_colors:
                print(f"\r{Colors.CYAN}[>] Running {name}... {test_spinner_char}{Colors.RESET}", end="", flush=True)
            else:
                print(f"\r[>] Running {name}... {test_spinner_char}", end="", flush=True)
        except (UnicodeEncodeError, Exception):
            use_spinner = False

        while not stop_spinner.is_set():
            if use_spinner:
                try:
                    spinner_char = next(spinner)
                    if use_colors:
                        print(f"\r{Colors.CYAN}[>] Running {name}... {spinner_char}{Colors.RESET}", end="", flush=True)
                    else:
                        print(f"\r[>] Running {name}... {spinner_char}", end="", flush=True)
                except StopIteration:
                    # Reset spinner if it runs out
                    spinner_char = next(spinner)
                    if use_colors:
                        print(f"\r{Colors.CYAN}[>] Running {name}... {spinner_char}{Colors.RESET}", end="", flush=True)
                    else:
                        print(f"\r[>] Running {name}... {spinner_char}", end="", flush=True)
            else:
                # Fallback to simple output if any encoding or other issues
                print(f"\r[>] Running {name}...", end="", flush=True)
            time.sleep(0.2)

    # Start spinner for tests (which take longer)
    if "Tests" in name:
        spinner_thread = threading.Thread(target=show_spinner)
        spinner_thread.daemon = True
        spinner_thread.start()

    try:
        # For VIKTOR tests, add extra debugging
        if "VIKTOR Tests" in name:
            # Flush all output streams before running
            sys.stdout.flush()
            sys.stderr.flush()

        exit_code, output = run_command(command)

        # For VIKTOR tests, check for any leaked output
        if "VIKTOR Tests" in name and output:
            # Check if output contains git-related content that shouldn't be there
            git_keywords = ["Enumerating objects", "Counting objects", "Compressing objects", "Writing objects", "remote:", "To https://github.com"]
            leaked_git_output = any(keyword in output for keyword in git_keywords)
            if leaked_git_output:
                # This shouldn't happen with proper capture, but let's log it
                print(f"\n{Colors.YELLOW}[DEBUG] Detected git output in VIKTOR tests: {output[:200]}...{Colors.RESET}")

    finally:
        if "Tests" in name:
            stop_spinner.set()
            # Clear the spinner line and flush
            print(f"\r{Colors.CYAN}[>] Running {name}...{Colors.RESET}", end="", flush=True)
            sys.stdout.flush()

    passed = exit_code == 0
    duration = time.time() - start_time

    # Parse error details
    error_count, error_details = parse_error_details(name, output)

    if passed:
        status = f" {Colors.GREEN}[+] PASSED"
        if duration > 1.0:  # Show duration for longer operations
            status += f" ({duration:.1f}s)"
        # For tests, try to extract and show test count if available
        if "Tests" in name and output:
            # Look for test count patterns in output (pytest format)
            test_count_match = re.search(r"(\d+) collected", output)
            if test_count_match:
                test_count = test_count_match.group(1)
                # Try to get passed count for "X/Y passed" format
                passed_match = re.search(r"(\d+) passed", output)
                if passed_match:
                    passed_count = passed_match.group(1)
                    if passed_count == test_count:
                        status += f" - {test_count} tests"
                    else:
                        status += f" - {passed_count}/{test_count} tests"
                else:
                    status += f" - {test_count} tests"
            else:
                # Look for unittest format (e.g., "Ran 45 tests")
                unittest_match = re.search(r"Ran (\d+) test", output)
                if unittest_match:
                    test_count = int(unittest_match.group(1))
                    # For unittest, also try to get failure/error counts
                    failed_match = re.search(r"(\d+) failed", output)
                    error_match = re.search(r"(\d+) error", output)
                    if failed_match or error_match:
                        failed_count = int(failed_match.group(1)) if failed_match else 0
                        error_count = int(error_match.group(1)) if error_match else 0
                        passed_count = test_count - failed_count - error_count
                        if passed_count == test_count:
                            status += f" - {test_count} tests"
                        else:
                            status += f" - {passed_count}/{test_count} tests"
                    else:
                        status += f" - {test_count} tests"
    else:
        status = f" {Colors.RED}[X] FAILED"
        if error_count > 0:
            status += f" - Found {error_count} error{'s' if error_count != 1 else ''}"
            if error_details:
                status += f" ({error_details})"

        # For failed tests, also try to show test count information
        if "Tests" in name and output:
            # Look for test count patterns in output (pytest format)
            test_count_match = re.search(r"(\d+) collected", output)
            if test_count_match:
                test_count = int(test_count_match.group(1))
                status += f" - {test_count} tests"
            else:
                # Look for unittest format (e.g., "Ran 45 tests")
                unittest_match = re.search(r"Ran (\d+) test", output)
                if unittest_match:
                    test_count = int(unittest_match.group(1))
                    status += f" - {test_count} tests"
            # Don't add confusing file count estimates from error output

    print(f"{status}{Colors.RESET}")

    return CheckResult(
        name=name, passed=passed, can_auto_fix=can_auto_fix, command=command, output=output, error_count=error_count, error_details=error_details
    )


def run_quality_check(name: str, command: str, can_auto_fix: bool = False) -> CheckResult:
    """Run a single quality check and return the result."""
    # Use progress indicator for longer operations
    return run_quality_check_with_progress(name, command, can_auto_fix)


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
            # For tests, try to show test count in final report
            if "Tests" in check.name and check.output:
                test_count_match = re.search(r"(\d+) collected", check.output)
                if test_count_match:
                    test_count = int(test_count_match.group(1))
                    status += f" - {test_count} tests"
                else:
                    unittest_match = re.search(r"Ran (\d+) test", check.output)
                    if unittest_match:
                        test_count = int(unittest_match.group(1))
                        status += f" - {test_count} tests"
        else:
            status = f"{Colors.RED}[X] FAILED"
            if check.error_count > 0:
                status += f" - Found {check.error_count} error{'s' if check.error_count != 1 else ''}"
                if check.error_details:
                    status += f" ({check.error_details})"

            # For failed tests, also try to show test count in final report
            if "Tests" in check.name and check.output:
                test_count_match = re.search(r"(\d+) collected", check.output)
                if test_count_match:
                    test_count = int(test_count_match.group(1))
                    status += f" - {test_count} tests"
                else:
                    unittest_match = re.search(r"Ran (\d+) test", check.output)
                    if unittest_match:
                        test_count = int(unittest_match.group(1))
                        status += f" - {test_count} tests"
                # Don't add confusing file count estimates from error output

            failed_checks.append(check)

        print(f"  {check.name}: {status}{Colors.RESET}")

    return failed_checks


def _handle_uncommitted_changes(args: argparse.Namespace) -> bool:
    """Handle uncommitted changes and return success status."""
    if check_git_status():
        print(f"{Colors.YELLOW}[!] Uncommitted changes detected{Colors.RESET}")
        if not args.dry_run:
            # Stop any active spinners before prompting for input
            print()  # Ensure clean line

            response = safe_input(f"{Colors.CYAN}Commit all changes before quality checks? (y/N): {Colors.RESET}").lower()

            if response in ("y", "yes"):
                commit_message = safe_input(f"{Colors.CYAN}Enter commit message: {Colors.RESET}")
                print(f"{Colors.YELLOW}[*] Processing commit...{Colors.RESET}", flush=True)
                if not commit_message:
                    commit_message = "Manual changes before quality checks"
                if not commit_changes(commit_message):
                    return False
            elif response in ("n", "no", ""):
                print(f"{Colors.YELLOW}[i] Proceeding with uncommitted changes (only auto-fixes will be committed){Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}[i] Unrecognized response '{response}', treating as 'no'{Colors.RESET}")
                print(f"{Colors.YELLOW}[i] Proceeding with uncommitted changes (only auto-fixes will be committed){Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}[DRY RUN] Would prompt to commit uncommitted changes{Colors.RESET}")
    return True


def _run_quality_checks_iteration(
    tool_python: str, iteration: int, args: argparse.Namespace
) -> tuple[bool, CheckResult, CheckResult, CheckResult, CheckResult, CheckResult]:
    """Run one iteration of quality checks and return results."""
    print(f"\n{Colors.BOLD}>> Iteration {iteration}{Colors.RESET}")
    print("-" * 40)

    # Track if we made any auto-fixes this iteration
    made_fixes = False

    # Get git diff hash before running Ruff
    diff_hash_before = get_git_diff_hash()

    # 1. Run Ruff style check (can auto-fix)
    ruff_check = run_quality_check("Ruff Style Check", f"{tool_python} scripts/run_ruff_check.py", can_auto_fix=True)

    # 2. Run Ruff formatter (can auto-fix)
    ruff_format = run_quality_check("Ruff Formatter", f"{tool_python} scripts/run_ruff_format.py", can_auto_fix=True)

    # Get git diff hash after running Ruff
    diff_hash_after = get_git_diff_hash()

    # If the diff hash changed, it means Ruff made changes
    if diff_hash_before != diff_hash_after:
        print(f"{Colors.YELLOW}[!] Ruff made auto-fixes{Colors.RESET}")
        made_fixes = True

        if not args.dry_run:
            if not commit_changes(f"Auto-fix: Ruff style and formatting (iteration {iteration})"):
                # Create default CheckResult objects for error case
                default_result = CheckResult("", False, False, "", "", 0, "")
                return False, ruff_check, ruff_format, default_result, default_result, default_result
        else:
            print(f"{Colors.YELLOW}[DRY RUN] Would commit Ruff auto-fixes{Colors.RESET}")

    # 3. Run MyPy (cannot auto-fix)
    mypy_check = run_quality_check("MyPy Type Check", f"{tool_python} scripts/run_mypy.py", can_auto_fix=False)

    # 4. Run tests using RUFT venv; get test count and use consistent label
    def _get_test_count_and_label(py_exe: str) -> tuple[str, str]:
        """Get test count and determine label for tests."""
        # Try to get test count by running a dry collection with pytest first
        count_cmd = f"{py_exe} -m pytest --collect-only -q tests"
        code, output = run_command(count_cmd)

        if code == 0:
            # Parse test count from pytest output
            lines = output.strip().split("\n")
            test_count = 0
            for line in lines:
                if line.strip() and line.endswith(" collected"):
                    try:
                        test_count = int(line.split()[0])
                        break
                    except (ValueError, IndexError):
                        pass

            if test_count > 0:
                return f"Tests ({test_count} tests)", f"{py_exe} scripts/run_enhanced_tests.py"

        # If pytest collection failed, try with more verbose output to see what's wrong
        if code != 0:
            # Try with import mode to see if it's an import issue
            import_cmd = f"{py_exe} -m pytest --collect-only --import-mode=importlib tests"
            import_code, import_output = run_command(import_cmd)
            if import_code == 0:
                # Parse test count from import mode output
                lines = import_output.strip().split("\n")
                test_count = 0
                for line in lines:
                    if line.strip() and line.endswith(" collected"):
                        try:
                            test_count = int(line.split()[0])
                            break
                        except (ValueError, IndexError):
                            pass

                if test_count > 0:
                    return f"Tests ({test_count} tests)", f"{py_exe} scripts/run_enhanced_tests.py"

            # Try with basic discovery to see if it's a configuration issue
            basic_cmd = f"{py_exe} -m pytest --collect-only --tb=no tests"
            basic_code, basic_output = run_command(basic_cmd)
            if basic_code == 0:
                # Parse test count from basic output
                lines = basic_output.strip().split("\n")
                test_count = 0
                for line in lines:
                    if line.strip() and line.endswith(" collected"):
                        try:
                            test_count = int(line.split()[0])
                            break
                        except (ValueError, IndexError):
                            pass

                if test_count > 0:
                    return f"Tests ({test_count} tests)", f"{py_exe} scripts/run_enhanced_tests.py"

        # Fallback: try to get test count from unittest discovery
        try:
            discover_cmd = f"{py_exe} -m unittest discover --list tests"
            code, output = run_command(discover_cmd)
            if code == 0:
                # Count test methods (lines ending with test method names)
                test_lines = [line for line in output.split("\n") if line.strip() and "." in line and line.endswith(")")]
                if test_lines:
                    return f"Tests ({len(test_lines)} tests)", f"{py_exe} scripts/run_enhanced_tests.py"
        except Exception:
            pass

        # Try one more approach: run a quick test to see how many tests we have
        try:
            quick_cmd = f"{py_exe} -m pytest --collect-only -q tests 2>/dev/null | tail -1"
            code, output = run_command(quick_cmd)
            if code == 0 and output.strip():
                # Look for "X collected" pattern
                collected_match = re.search(r"(\d+) collected", output.strip())
                if collected_match:
                    test_count = int(collected_match.group(1))
                    return f"Tests ({test_count} tests)", f"{py_exe} scripts/run_enhanced_tests.py"
        except Exception:
            pass

        # Try to get test count from the actual test runner output
        try:
            # Run a minimal test to see what output we get
            test_cmd = f"{py_exe} scripts/run_enhanced_tests.py --help"
            code, output = run_command(test_cmd)
            if code == 0:
                # Look for any test count patterns in the help output
                help_match = re.search(r"(\d+) tests?", output, re.IGNORECASE)
                if help_match:
                    test_count = int(help_match.group(1))
                    return f"Tests ({test_count} tests)", f"{py_exe} scripts/run_enhanced_tests.py"
        except Exception:
            pass

        # Try to count test files directly from the tests directory
        try:
            import os

            tests_dir = Path("tests")
            if tests_dir.exists():
                test_files = []
                for root, dirs, files in os.walk(tests_dir):
                    for file in files:
                        if file.startswith("test_") and file.endswith(".py"):
                            # Store the full path relative to tests directory
                            rel_path = Path(root) / file
                            test_files.append(rel_path)
                if test_files:
                    # Count actual test methods by reading the files
                    total_methods = 0
                    unreadable_files = []

                    def read_test_file(file_path: Path) -> tuple[int, str | None]:
                        """Read a test file and return test method count and error info."""
                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read()
                                # Count test methods (def test_*)
                                test_methods = len(re.findall(r"def test_", content))
                                return test_methods, None
                        except Exception as e:
                            # Track files we can't read - this shouldn't happen normally
                            # Add some debug info to understand the issue
                            return 0, f"{file_path} ({type(e).__name__})"

                    for test_file_path in test_files:
                        test_methods, error_info = read_test_file(test_file_path)
                        total_methods += test_methods
                        if error_info:
                            unreadable_files.append(error_info)

                    if unreadable_files:
                        # If we can't read some files, we can't give an exact count
                        return (
                            f"Tests ({total_methods}+ tests, {len(unreadable_files)} files unreadable)",
                            f"{py_exe} scripts/run_enhanced_tests.py",
                        )
                    # Exact count - we read all files successfully
                    return f"Tests ({total_methods} tests)", f"{py_exe} scripts/run_enhanced_tests.py"
        except Exception:
            pass

        # Final fallback: just return "Tests" without count
        return "Tests", f"{py_exe} scripts/run_enhanced_tests.py"

    tests_label, test_command = _get_test_count_and_label(tool_python)
    test_check = run_quality_check(tests_label, test_command, can_auto_fix=False)

    # 5. Run VIKTOR tests (cannot auto-fix)
    viktor_test_check = run_quality_check("VIKTOR Tests", f"{tool_python} scripts/run_viktor_tests.py", can_auto_fix=False)

    return made_fixes, ruff_check, ruff_format, mypy_check, test_check, viktor_test_check


def _handle_push(args: argparse.Namespace) -> int:
    """Handle pushing changes and return exit code."""
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

    # Handle uncommitted changes
    if not _handle_uncommitted_changes(args):
        return 1

    # Prepare a dedicated RUFT venv so developers can just run a single command
    def get_tool_python() -> str:
        """Create or reuse a local venv for tools and return its python path."""
        venv_dir = Path(".ruft_venv")
        py_path = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        if not py_path.exists():
            print(f"{Colors.CYAN}[>] Creating RUFT virtual environment...{Colors.RESET}")
            code, output = run_command(f"{sys.executable} -m venv {venv_dir}")
            if code != 0:
                print(f"{Colors.YELLOW}[!] Failed to create RUFT venv, falling back to system interpreter{Colors.RESET}")
                print(f"{Colors.YELLOW}[DEBUG] Venv creation error: {output[:200]}...{Colors.RESET}")
                return sys.executable

        # Ensure base/runtime and dev requirements are installed
        base_req = Path("requirements.txt")
        dev_req = Path("requirements_dev.txt")
        if base_req.exists():
            print(f"{Colors.CYAN}[>] Ensuring runtime dependencies are installed in RUFT venv...{Colors.RESET}")
            code, output = run_command(f"{py_path} -m pip install -r {base_req}")
            if code != 0:
                print(f"{Colors.YELLOW}[DEBUG] Runtime deps install error: {output[:200]}...{Colors.RESET}")
        if dev_req.exists():
            print(f"{Colors.CYAN}[>] Ensuring dev dependencies are installed in RUFT venv...{Colors.RESET}")
            code, output = run_command(f"{py_path} -m pip install -r {dev_req}")
            if code != 0:
                print(f"{Colors.YELLOW}[DEBUG] Dev deps install error: {output[:200]}...{Colors.RESET}")

        # Verify critical tools are properly installed with executables
        print(f"{Colors.CYAN}[>] Verifying tool installations in RUFT venv...{Colors.RESET}")

        # Test ruff installation
        ruff_test_code, ruff_test_output = run_command(f"{py_path} -m ruff --version")
        if ruff_test_code != 0:
            print(f"{Colors.YELLOW}[!] Ruff executable missing, attempting to reinstall...{Colors.RESET}")
            # Force reinstall ruff to ensure executable is created
            reinstall_code, reinstall_output = run_command(f"{py_path} -m pip install --force-reinstall --no-cache-dir ruff==0.11.7")
            if reinstall_code != 0:
                print(f"{Colors.YELLOW}[DEBUG] Ruff reinstall error: {reinstall_output[:200]}...{Colors.RESET}")
                print(f"{Colors.YELLOW}[!] Falling back to system interpreter for ruff{Colors.RESET}")
                return sys.executable
            # Test again after reinstall
            ruff_retest_code, _ = run_command(f"{py_path} -m ruff --version")
            if ruff_retest_code != 0:
                print(f"{Colors.YELLOW}[!] Ruff still not working after reinstall, falling back to system interpreter{Colors.RESET}")
                return sys.executable

        # Test mypy installation
        mypy_test_code, mypy_test_output = run_command(f"{py_path} -m mypy --version")
        if mypy_test_code != 0:
            print(f"{Colors.YELLOW}[!] MyPy executable missing, attempting to reinstall...{Colors.RESET}")
            # Force reinstall mypy to ensure executable is created
            reinstall_code, reinstall_output = run_command(f"{py_path} -m pip install --force-reinstall --no-cache-dir mypy==1.15.0")
            if reinstall_code != 0:
                print(f"{Colors.YELLOW}[DEBUG] MyPy reinstall error: {reinstall_output[:200]}...{Colors.RESET}")
                print(f"{Colors.YELLOW}[!] Falling back to system interpreter for mypy{Colors.RESET}")
                return sys.executable

        # Verify the python path works
        test_code, test_output = run_command(f"{py_path} --version")
        if test_code != 0:
            print(f"{Colors.YELLOW}[DEBUG] Python path test failed: {test_output}{Colors.RESET}")
            return sys.executable

        return str(py_path)

    tool_python = get_tool_python()

    max_iterations = 3  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        made_fixes, ruff_check, ruff_format, mypy_check, test_check, viktor_test_check = _run_quality_checks_iteration(tool_python, iteration, args)

        if not made_fixes:
            print(f"{Colors.CYAN}[i] No auto-fixes applied this iteration, proceeding to final report{Colors.RESET}")
            break

        print(f"{Colors.YELLOW}[!] Auto-fixes applied, running checks again...{Colors.RESET}")

    # Final status report
    all_checks = [ruff_check, ruff_format, mypy_check, test_check, viktor_test_check]
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

    # Handle push
    return _handle_push(args)


if __name__ == "__main__":
    sys.exit(main())
