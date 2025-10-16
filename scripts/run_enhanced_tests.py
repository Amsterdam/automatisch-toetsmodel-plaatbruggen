#!/usr/bin/env python3
"""Enhanced test runner with colorful output and detailed failure reporting."""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import TextTestResult

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_utils import (  # noqa: E402
    Colors,
    EnhancedTestResult,
    colored_text,
    colorized_status_message,
    safe_arrow,
    safe_emoji_text,
    should_use_concise_mode,
)


def print_concise_summary(result: TextTestResult) -> None:
    """Print a concise summary for git hooks."""
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors

    # Always show a summary line for git hooks
    if failures == 0 and errors == 0:
        safe_emoji_text("✅ ALL TESTS PASSED!", "ALL TESTS PASSED!")
        print(colorized_status_message(f"All {total_tests} tests passed successfully", is_success=True))

        # Overall status message - more generic since other checks might have failed
        print("\n" + "=" * 60)
        print(colorized_status_message("ALL CHECKS COMPLETED", is_success=False, is_warning=True))
        print(colorized_status_message("Check the logs above.", is_success=False, is_warning=True))
        print("=" * 60)
    else:
        safe_emoji_text("❌ TESTS FAILED", "TESTS FAILED")
        print(colorized_status_message(f"Test results: {passed}/{total_tests} passed, {failures} failed, {errors} errors", is_success=False))
        print(colorized_status_message("Run the following command for detailed test error information:", is_success=False, is_warning=True))
        print(f"  {safe_arrow()}{colored_text('python run_enhanced_tests.py', Colors.CYAN, bold=True)}")

        # Don't show final "CHECKS FAILED" message here - let the hook system handle overall status


def print_detailed_summary(result: TextTestResult) -> None:
    """Print detailed summary for manual runs."""
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors

    if failures == 0 and errors == 0:
        safe_emoji_text("🎉 ALL TESTS PASSED! 🎉", "ALL TESTS PASSED!")
        print(colorized_status_message(f"All {total_tests} tests passed successfully! 🎯", is_success=True))
    else:
        safe_emoji_text("❌ SOME TESTS FAILED", "SOME TESTS FAILED")
        print(colorized_status_message(f"Test results: {passed}/{total_tests} passed, {failures} failed, {errors} errors", is_success=False))

        print("\n" + "=" * 60)
        print(colorized_status_message("DETAILED ERROR INFORMATION:", is_success=False))
        print("=" * 60)

        # Show detailed failures
        if result.failures:
            print(colorized_status_message(f"\nFAILURES ({len(result.failures)}):", is_success=False))
            for i, (test, traceback) in enumerate(result.failures, 1):
                test_name = f"{test.__class__.__name__}.{test._testMethodName}"  # noqa: SLF001
                print(f"\n{i}. {colorized_status_message(test_name, is_success=False)}")
                print(traceback)

        # Show detailed errors
        if result.errors:
            print(colorized_status_message(f"\nERRORS ({len(result.errors)}):", is_success=False))
            for i, (test, traceback) in enumerate(result.errors, 1):
                test_name = f"{test.__class__.__name__}.{test._testMethodName}"  # noqa: SLF001
                print(f"\n{i}. {colorized_status_message(test_name, is_success=False)}")
                print(traceback)

        print("\n" + "=" * 60)
        print(colorized_status_message("TIP: Focus on fixing errors first, then failures", is_success=False, is_warning=True))
        print("=" * 60)


def main() -> None:
    """
    Run all tests with enhanced reporting.

    Prefer pytest (collects both pytest-style and unittest-style tests). If pytest
    isn't available, fall back to unittest discovery with enhanced output.
    """
    # Enable colors for Git environments (like Git Bash) even if detection is conservative
    if any(os.environ.get(var) for var in ["MSYSTEM", "MINGW_PREFIX", "TERM"]):
        os.environ["FORCE_COLOR"] = "1"

    # Use the improved environment detection from test_utils
    concise_mode = should_use_concise_mode()

    # Try pytest first to ensure complete test coverage
    try:
        import pytest  # type: ignore[import-untyped]

        pytest_args: list[str] = ["tests"]
        # Use verbose output to show test counts clearly
        if not concise_mode:
            pytest_args.insert(0, "-v")
        else:
            pytest_args.insert(0, "-q")

        # Suppress the pkg_resources deprecation warning from docxcompose
        pytest_args.extend(["-W", "ignore:pkg_resources is deprecated:UserWarning:docxcompose.properties"])

        # Run pytest and exit with its status code
        exit_code = pytest.main(pytest_args)
        sys.exit(exit_code)
    except ImportError:
        # Attempt to install pytest or dev requirements automatically, then retry
        req_file = Path("requirements_dev.txt")
        install_cmd = [sys.executable, "-m", "pip", "install", "pytest"]
        if req_file.exists():
            install_cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]

        try:
            subprocess.run(install_cmd, check=False, cwd=Path.cwd())
            import importlib

            if importlib.util.find_spec("pytest") is not None:
                import pytest  # type: ignore[import-untyped]

                pytest_args2: list[str] = ["tests"]
                if not concise_mode:
                    pytest_args2.insert(0, "-v")
                else:
                    pytest_args2.insert(0, "-q")

                # Suppress the pkg_resources deprecation warning from docxcompose
                pytest_args2.extend(["-W", "ignore:pkg_resources is deprecated:UserWarning:docxcompose.properties"])

                sys.exit(pytest.main(pytest_args2))
        except Exception:
            # Fall back to unittest runner below
            pass

    # In concise mode, don't show startup message
    if not concise_mode:
        print("Running enhanced test suite...")
        print("=" * 60)

    # Discover all tests (unittest-only fallback)
    loader = unittest.TestLoader()
    test_suite = loader.discover("tests", pattern="test_*.py")

    # Create enhanced test runner with minimal output in concise mode
    verbosity = 0  # Always use minimal verbosity for both modes
    runner = unittest.TextTestRunner(resultclass=EnhancedTestResult, verbosity=verbosity, stream=sys.stdout)  # type: ignore[arg-type]

    # Run tests
    result = runner.run(test_suite)

    # Print appropriate summary
    if concise_mode:
        print_concise_summary(result)
    else:
        print_detailed_summary(result)

    # Exit with appropriate code
    if result.failures or result.errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
