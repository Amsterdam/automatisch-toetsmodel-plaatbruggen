"""
Path constants for SCIA integration.

These constants define file system paths specific to SCIA integration,
including template files and resource locations.
"""

from pathlib import Path

# Base paths for SCIA integration
SCIA_PROJECT_PATH = Path(__file__).parent.parent.parent.parent.parent
SCIA_RESOURCES_PATH = SCIA_PROJECT_PATH / "resources"
SCIA_TEMPLATE_PATH = SCIA_RESOURCES_PATH / "templates" / "model.esa"
