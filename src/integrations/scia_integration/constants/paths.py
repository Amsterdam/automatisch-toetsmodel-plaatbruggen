"""
Path constants for SCIA integration.

These constants define file system paths specific to SCIA integration,
including template files and resource locations.
"""

from pathlib import Path

# Base paths for SCIA integration
SCIA_PROJECT_PATH = Path(__file__).parent.parent.parent.parent.parent
SCIA_RESOURCES_PATH = SCIA_PROJECT_PATH / "resources"

# SCIA templates for integration strips analysis
SCIA_TEMPLATE_PATH = SCIA_RESOURCES_PATH / "templates" / "model_governing_integrationstrips.esa"
SCIA_TEMPLATE_FULL_PATH = SCIA_RESOURCES_PATH / "templates" / "model_full_integrationstrips.esa"

# SCIA templates for sections-on-plane analysis
SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH = SCIA_RESOURCES_PATH / "templates" / "model_governing_sectionsonplane.esa"
SCIA_TEMPLATE_SECTIONS_ON_PLANE_FULL_PATH = SCIA_RESOURCES_PATH / "templates" / "model_full_sectionsonplane.esa"
