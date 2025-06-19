"""Test utilities for enhanced error reporting and colorful output."""

import functools
import os
import sys
import traceback
import unittest
from collections.abc import Callable
from typing import Any, TextIO


def is_git_hook_environment() -> bool:
    """Detect if we're running in a git hook or CI environment where emojis might not work."""
    # Check for actual git hook environment variables (not just VS Code Git tools)
    git_hook_indicators = ["GIT_DIR", "GIT_INDEX_FILE", "GIT_AUTHOR_NAME", "CI", "GITHUB_ACTIONS", "GITLAB_CI"]

    # Also check if we're in a pre-commit hook (common environment)
    if any(os.environ.get(indicator) for indicator in git_hook_indicators):
        return True

    # Check if running under pre-commit (multiple possible indicators) - but be specific
    pre_commit_indicators = ["PRE_COMMIT", "PRE_COMMIT_HOME", "_PRE_COMMIT_HOOK_ID", "PRE_COMMIT_COLOR"]
    if any(os.environ.get(indicator) for indicator in pre_commit_indicators):
        return True

    # Check for pre-commit specific environment patterns - but exclude VS Code patterns
    for env_var in os.environ:
        if "PRE_COMMIT" in env_var and "VSCODE" not in env_var:
            return True

    # Check if parent process looks like a git operation
    try:
        import psutil

        current = psutil.Process()
        for parent in current.parents():
            if any(keyword in parent.name().lower() for keyword in ["git", "pre-commit", "hook"]):
                return True
    except (ImportError, Exception):
        pass

    # Check if we're being called from a hook script (common pattern) - but not VS Code
    return bool(any("hook" in str(arg).lower() for arg in sys.argv if "vscode" not in str(arg).lower()))


def should_use_concise_mode() -> bool:
    """Determine if we should use concise output mode (for git hooks)."""
    return is_git_hook_environment() or os.environ.get("TEST_CONCISE_MODE") == "1"


def supports_color() -> bool:  # noqa: PLR0911
    """Check if the current terminal supports ANSI colors."""
    # Force color support if explicitly requested
    if os.environ.get("FORCE_COLOR", "").lower() in ("1", "true", "yes"):
        return True

    # Force no color if explicitly requested
    if os.environ.get("NO_COLOR", "").lower() in ("1", "true", "yes"):
        return False

    # Check for Git Bash/MINGW environments which support colors
    if any(os.environ.get(var) for var in ["MSYSTEM", "MINGW_PREFIX", "TERM"]):
        return True

    # Check for common CI environments that support color
    ci_environments = ("GITHUB_ACTIONS", "GITLAB_CI", "TRAVIS", "CIRCLECI")
    if any(os.environ.get(env) for env in ci_environments):
        return True

    # Git hooks often run in terminals that support color
    if is_git_hook_environment():
        return True

    # PowerShell and Windows Terminal support colors
    if os.name == "nt" and hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        # Try to enable VT processing on Windows
        try:
            import ctypes
            from ctypes import wintypes

            # Type ignore for MyPy since windll only exists on Windows
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = wintypes.DWORD()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            # Enable ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004)
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True  # noqa: TRY300
        except Exception:
            pass

    # Check if we're in a TTY and return result directly
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"  # Dark gray for muted text
    LIGHT_GRAY = "\033[37m"  # Light gray alternative

    # Styles
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    DIM = "\033[2m"  # Dim/faint text

    # Reset
    RESET = "\033[0m"

    @classmethod
    def disable_on_windows_if_needed(cls) -> None:
        """Disable colors if the terminal doesn't support them."""
        if not supports_color():
            # Disable all colors
            for attr in dir(cls):
                if not attr.startswith("_") and attr != "disable_on_windows_if_needed":
                    setattr(cls, attr, "")


def colored_text(text: str, color: str, bold: bool = False) -> str:
    """Create colored text with optional bold styling."""
    # Respect color support detection, but allow override
    if not supports_color() and not os.environ.get("FORCE_COLOR"):
        return text

    style = Colors.BOLD if bold else ""
    return f"{style}{color}{text}{Colors.RESET}"


def muted_text(text: str) -> str:
    """Create muted (gray/dim) text for less important information."""
    if not supports_color() and not os.environ.get("FORCE_COLOR"):
        return text

    # Use dim gray for muted text
    return f"{Colors.DIM}{Colors.GRAY}{text}{Colors.RESET}"


def safe_emoji_text(emoji_text: str, plain_text: str) -> str:  # noqa: PLR0911
    """Return emoji text if supported by terminal, otherwise plain text."""
    try:
        # Test if emoji can be encoded to the default encoding
        emoji_text.encode(sys.stdout.encoding or "utf-8")
        # Use colored emoji text if colors are supported
        if supports_color():
            if "✅" in emoji_text:
                return colored_text(emoji_text, Colors.GREEN, bold=True)
            if "❌" in emoji_text:
                return colored_text(emoji_text, Colors.RED, bold=True)
            if "🎉" in emoji_text:
                return colored_text(emoji_text, Colors.CYAN, bold=True)
            return colored_text(emoji_text, Colors.YELLOW, bold=True)
        return emoji_text  # noqa: TRY300
    except (UnicodeEncodeError, AttributeError, LookupError):
        # Fall back to colored plain text
        if supports_color():
            if "PASSED" in plain_text:
                return colored_text(plain_text, Colors.GREEN, bold=True)
            if "FAILED" in plain_text:
                return colored_text(plain_text, Colors.RED, bold=True)
            return colored_text(plain_text, Colors.YELLOW, bold=True)
        return plain_text


def detailed_failure_message(test_name: str, view_name: str, function_name: str, error_details: str) -> str:
    """Create a detailed failure message with colors and formatting."""
    header = colored_text(safe_emoji_text("🔥 VIEW TEST FAILURE! 🔥", "VIEW TEST FAILURE!"), Colors.RED, bold=True)
    test_info = colored_text(f"Test: {test_name}", Colors.CYAN)
    view_info = colored_text(f"View: {view_name}", Colors.YELLOW)
    func_info = colored_text(f"Function: {function_name}", Colors.MAGENTA)
    error_header = colored_text(safe_emoji_text("💥 Error Details:", "Error Details:"), Colors.RED, bold=True)

    return f"""
{header}
{test_info}
{view_info}
{func_info}

{error_header}
{colored_text(error_details, Colors.WHITE)}
{"=" * 60}
"""


def view_test_wrapper(view_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for view tests that provides detailed failure messages."""

    def decorator(test_func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(test_func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            try:
                return test_func(self, *args, **kwargs)
            except Exception as e:
                # Extract function name from traceback
                tb = traceback.extract_tb(e.__traceback__)
                function_name = "unknown"
                for frame in reversed(tb):
                    if "controller" in frame.filename.lower():
                        function_name = frame.name
                        break

                # Create detailed failure message
                detailed_failure_message(
                    test_name=test_func.__name__, view_name=view_name, function_name=function_name, error_details=f"{type(e).__name__}: {e!s}"
                )

                # Print the detailed message

                # Re-raise the original exception
                raise

        return wrapper

    return decorator


def controller_test_wrapper(controller_name: str, method_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for controller method tests that provides detailed failure messages."""

    def decorator(test_func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(test_func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            try:
                return test_func(self, *args, **kwargs)
            except Exception as e:
                # Create detailed failure message
                header = colored_text(safe_emoji_text("🚨 CONTROLLER TEST FAILURE! 🚨", "CONTROLLER TEST FAILURE!"), Colors.RED, bold=True)
                test_info = colored_text(f"Test: {test_func.__name__}", Colors.CYAN)
                controller_info = colored_text(f"Controller: {controller_name}", Colors.YELLOW)
                method_info = colored_text(f"Method: {method_name}", Colors.MAGENTA)
                error_header = colored_text(safe_emoji_text("💀 Error Details:", "Error Details:"), Colors.RED, bold=True)

                f"""
{header}
{test_info}
{controller_info}
{method_info}

{error_header}
{colored_text(f"{type(e).__name__}: {e!s}", Colors.WHITE)}
{"=" * 60}
"""

                # Print the detailed message

                # Re-raise the original exception
                raise

        return wrapper

    return decorator


class EnhancedTestResult(unittest.TestResult):
    """Custom TestResult class with enhanced failure reporting and colors."""

    def __init__(self, stream: TextIO | None = None, descriptions: bool | None = None, verbosity: int | None = None) -> None:
        """Initialize the enhanced test result with color support and verbosity control."""
        super().__init__(stream, descriptions, verbosity)
        Colors.disable_on_windows_if_needed()
        self.stream = stream
        self.show_all = verbosity is not None and verbosity > 1
        self.dots = verbosity == 1

    def addError(self, test: unittest.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:  # type: ignore[override]  # noqa: N802
        """Add an error result and print detailed error information."""
        super().addError(test, err)
        self._print_detailed_error(test, err, "ERROR")

    def addFailure(self, test: unittest.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:  # type: ignore[override]  # noqa: N802
        """Add a failure result and print detailed failure information."""
        super().addFailure(test, err)
        self._print_detailed_error(test, err, "FAILURE")

    def addSuccess(self, test: unittest.TestCase) -> None:  # noqa: N802
        """Add a success result."""
        super().addSuccess(test)
        # In concise mode (git hooks), don't print individual test results
        if not should_use_concise_mode():
            pass

    def _print_detailed_error(self, test: unittest.TestCase, err: tuple[type[BaseException], BaseException, Any], error_type: str) -> None:
        """Print a detailed error message with colors."""
        exc_type, exc_value, exc_traceback = err

        # Extract relevant information
        test_name = test._testMethodName  # noqa: SLF001
        test_class = test.__class__.__name__
        error_msg = str(exc_value)

        # In concise mode, just store the failure for later summary
        if should_use_concise_mode():
            # Store failure info for summary (we'll add this to the class)
            if not hasattr(self, "_concise_failures"):
                self._concise_failures = []
            self._concise_failures.append(
                {
                    "test_class": test_class,
                    "test_name": test_name,
                    "error_type": exc_type.__name__,
                    "error_msg": error_msg,
                    "is_error": error_type == "ERROR",
                }
            )
            return

        # Create detailed header
        if error_type == "ERROR":
            header = colored_text(safe_emoji_text("💥 TEST ERROR! 💥", "TEST ERROR!"), Colors.RED, bold=True)
            emoji = safe_emoji_text("🔥", "ERROR:")
        else:
            header = colored_text(safe_emoji_text("❌ TEST FAILURE! ❌", "TEST FAILURE!"), Colors.YELLOW, bold=True)
            emoji = safe_emoji_text("💔", "FAILED:")

        # Format the message
        f"""
{header}
{colored_text(f"Test Class: {test_class}", Colors.CYAN)}
{colored_text(f"Test Method: {test_name}", Colors.MAGENTA)}
{colored_text(f"Error Type: {exc_type.__name__}", Colors.YELLOW)}

{colored_text(f"{emoji} What went wrong:", Colors.RED, bold=True)}
{colored_text(error_msg, Colors.WHITE)}

{colored_text(safe_emoji_text("📍 Stack trace:", "Stack trace:"), Colors.BLUE, bold=True)}
"""

        # Print a simplified stack trace with colors
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in tb_lines[-5:]:  # Show last 5 lines of traceback
            if 'File "' in line or line.strip().startswith(("assert", "self.assert")):
                pass
            else:
                pass


class EnhancedTestRunner(unittest.TextTestRunner):
    """Custom test runner that uses EnhancedTestResult."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the enhanced test runner with custom result class."""
        kwargs["resultclass"] = EnhancedTestResult
        kwargs["verbosity"] = 0  # We handle our own output
        super().__init__(*args, **kwargs)


def run_enhanced_tests(test_suite: unittest.TestSuite) -> unittest.TestResult:
    """Run tests with enhanced failure reporting."""
    runner = EnhancedTestRunner()
    result = runner.run(test_suite)

    # Final summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    total_tests - failures - errors

    if failures == 0 and errors == 0:
        pass
    else:
        pass

    return result


def safe_symbol(unicode_symbol: str, ascii_fallback: str) -> str:
    """Return Unicode symbol if supported, otherwise ASCII fallback."""
    try:
        # Test if the symbol can be encoded to the console encoding
        unicode_symbol.encode(sys.stdout.encoding or "utf-8")
        return unicode_symbol  # noqa: TRY300
    except (UnicodeEncodeError, AttributeError, LookupError):
        return ascii_fallback


def safe_arrow() -> str:
    """Return Unicode arrow if supported, otherwise ASCII fallback."""
    return safe_symbol("→ ", "-> ")


def colorized_status_message(message: str, is_success: bool, is_warning: bool = False) -> str:
    """Create a colorized status message based on the status type."""
    # Add visual symbols for better distinction with safe encoding
    if is_success:
        prefix = safe_symbol("✓ ", "[OK] ")
        if supports_color():
            return colored_text(f"{prefix}{message}", Colors.GREEN, bold=True)
        return f"{prefix}{message}"
    if is_warning:
        prefix = safe_symbol("⚠ ", "[INFO] ")
        if supports_color():
            return colored_text(f"{prefix}{message}", Colors.YELLOW, bold=True)
        return f"{prefix}{message}"
    prefix = safe_symbol("✗ ", "[ERROR] ")
    if supports_color():
        return colored_text(f"{prefix}{message}", Colors.RED, bold=True)
    return f"{prefix}{message}"
