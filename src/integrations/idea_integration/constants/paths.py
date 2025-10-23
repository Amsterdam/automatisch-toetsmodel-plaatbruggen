"""
Path constants for IDEA StatiCa integration.

These constants define file system paths specific to IDEA integration,
including material data files and resource locations.
"""

from pathlib import Path

# Base paths for IDEA integration
IDEA_PROJECT_PATH = Path(__file__).parent.parent.parent.parent.parent
IDEA_RESOURCES_PATH = IDEA_PROJECT_PATH / "resources"
IDEA_MATERIALS_PATH = IDEA_RESOURCES_PATH / "data" / "idea_materials"
