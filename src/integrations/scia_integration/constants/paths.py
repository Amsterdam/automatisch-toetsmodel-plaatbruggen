"""
Path constants for SCIA integration.

These constants define file system paths specific to SCIA integration,
including template files and resource locations.
"""

from pathlib import Path

# Base paths for SCIA integration
SCIA_PROJECT_PATH = Path(__file__).parent.parent.parent.parent.parent
SCIA_RESOURCES_PATH = SCIA_PROJECT_PATH / "resources"

# SCIA templates - currently testing with governing template
SCIA_TEMPLATE_PATH = SCIA_RESOURCES_PATH / "templates" / "model_governing.esa"
SCIA_TEMPLATE_FULL_PATH = SCIA_RESOURCES_PATH / "templates" / "model_full.esa"
