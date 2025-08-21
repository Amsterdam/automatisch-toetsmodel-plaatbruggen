"""
Development Environment Setup Script.

This script automates the complete setup process for new developers on the project.
It creates the RUFT virtual environment, installs all dependencies, and verifies the setup.

Usage:
    python setup_dev.py
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command: str, description: str, show_output: bool = False) -> bool:
    """Run a command and return True if successful."""
    print(f"[*] {description}...")
    try:
        if show_output:
            # Show live output for longer operations
            subprocess.run(command, shell=True, check=True, cwd=Path.cwd())
        else:
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True, cwd=Path.cwd())
        print(f"[+] {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[X] {description} - FAILED")
        if hasattr(e, "stderr") and e.stderr:
            print(f"   Error: {e.stderr.strip()}")
        elif hasattr(e, "stdout") and e.stdout:
            print(f"   Output: {e.stdout.strip()}")
        return False
    except Exception as e:
        print(f"[X] {description} - FAILED")
        print(f"   Error: {e}")
        return False


def check_python_version() -> bool:
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        print(f"[+] Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    print(f"[X] Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.12+")
    return False


def setup_ruft_venv() -> tuple[bool, str]:
    """Set up the RUFT virtual environment and return success status and python path."""
    venv_dir = Path(".ruft_venv")
    py_path = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    # Create virtual environment if it doesn't exist
    if not py_path.exists() and not run_command(f"{sys.executable} -m venv {venv_dir}", "Creating RUFT virtual environment"):
        return False, ""

    # Install requirements in RUFT venv
    for req_file in ["requirements.txt", "requirements_dev.txt"]:
        if Path(req_file).exists() and not run_command(f"{py_path} -m pip install -r {req_file}", f"Installing {req_file} in RUFT venv", show_output=True):
            return False, ""

    # Verify the setup
    if not run_command(f"{py_path} --version", "Verifying RUFT Python installation"):
        return False, ""

    return True, str(py_path)


def main() -> int:
    """Main setup function."""
    print(">> Setting up development environment...")
    print("=" * 60)

    # Check Python version
    if not check_python_version():
        print("\n[X] Setup failed: Incompatible Python version")
        print("Please install Python 3.12 or higher and try again.")
        return 1

    # Check if we're in the right directory
    if not Path("requirements_dev.txt").exists():
        print("[X] Setup failed: requirements_dev.txt not found")
        print("Please run this script from the project root directory.")
        return 1

    # Step 1: Set up RUFT virtual environment (this is what ruft.py uses)
    print("\n>> Step 1: Setting up RUFT Virtual Environment")
    print("-" * 40)
    success, ruft_python = setup_ruft_venv()
    if not success:
        print("\n[X] Setup failed: Could not set up RUFT virtual environment")
        return 1

    # Step 2: Install VIKTOR dependencies (optional, for VIKTOR CLI)
    print("\n>> Step 2: Installing VIKTOR Dependencies (Optional)")
    print("-" * 40)
    viktor_success = run_command("viktor-cli install", "Installing VIKTOR dependencies")
    if not viktor_success:
        print("[!] VIKTOR CLI installation failed - this is optional for development")
        print("    You can still use the development tools without VIKTOR CLI")

    # Step 3: Basic verification
    print("\n>> Step 3: Basic Verification")
    print("-" * 40)
    print("[+] RUFT virtual environment created successfully")
    print("[+] All dependencies installed")
    print("[+] Setup complete!")

    # Success!
    print("\n" + "=" * 60)
    print("[+] Development environment setup complete!")
    print("\nEverything is ready for development!")

    print(f"\nRUFT Virtual Environment: {Path('.ruft_venv').absolute()}")
    print(f"Python Executable: {ruft_python}")

    print("\nIDE Setup (VS Code/Cursor):")
    print("   1. Open Command Palette (Ctrl+Shift+P)")
    print("   2. Select 'Python: Select Interpreter'")
    print(f"   3. Choose: {ruft_python}")
    print("   4. This enables proper test discovery and linting")

    print("\nQuick Start:")
    print("   python ruft.py --dry-run    # Test quality checks (takes 2-5 minutes first time)")
    print("   python ruft.py              # Run quality checks and push")

    print("\nDevelopment Workflow:")
    print("   git checkout -b feature/my-new-feature")
    print("   # ... make changes ...")
    print("   python ruft.py              # Quality checks + auto-commit + push")

    print("\nFirst Time Setup:")
    print("   - Run 'python ruft.py --dry-run' to verify everything works")
    print("   - This will take 2-5 minutes as it sets up and tests everything")
    print("   - Subsequent runs will be much faster")

    print("\nDocumentation:")
    print("   docs/testing_uitleg.md      # Testing guidelines")
    print("   docs/development_workflow.md # Development process")

    return 0


if __name__ == "__main__":
    sys.exit(main())
