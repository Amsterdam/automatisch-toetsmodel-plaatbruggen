"""
Development Environment Setup Script.

This script automates the setup process for new developers on the project.
It installs dependencies and verifies the installation.

Usage:
    python setup_dev.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"[*] {description}...")
    try:
        subprocess.run(command.split(), check=True, capture_output=True, text=True, cwd=Path.cwd())
        print(f"[+] {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[X] {description} - FAILED")
        print(f"   Error: {e.stderr.strip()}")
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


def main() -> int:
    """Main setup function."""
    print(">> Setting up development environment...")
    print("=" * 50)

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

    # Install dependencies
    steps = [
        ("viktor-cli install", "Installing VIKTOR dependencies"),
        ("pip install -r requirements_dev.txt", "Installing development tools"),
    ]

    for command, description in steps:
        if not run_command(command, description):
            print(f"\n[X] Setup failed at: {description}")
            return 1

    print("\n" + "=" * 50)
    print("[+] Development environment setup complete!")
    print("\nNext steps:")
    print("1. Test the setup:")
    print("   python ruft.py --dry-run")
    print("\n2. Start developing:")
    print("   git checkout -b feature/my-new-feature")
    print("   # ... make changes ...")
    print("   git add .")
    print("   git commit -m 'feat: add new feature'")
    print("   git push origin feature/my-new-feature")
    print("\nFull documentation: docs/testing_uitleg.md")
    print("\nNote: This works with any Python environment setup")
    print("   (system-wide, virtual env, conda, poetry, etc.)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
