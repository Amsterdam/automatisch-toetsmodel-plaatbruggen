"""
File and directory path constants for the app layer.

These constants define paths to resources, templates, data files,
and other file system locations used by the VIKTOR application.
"""

from pathlib import Path

# Base project path
PROJECT_PATH = Path(__file__).parent.parent.parent

# Documentation paths
README_PATH = PROJECT_PATH / "README.md"
VIKTOR_README_PATH = PROJECT_PATH / "VIKTOR_README.md"
CHANGELOG_PATH = PROJECT_PATH / "CHANGELOG.md"

# Resource paths
CSS_PATH = PROJECT_PATH / "resources" / "styles" / "style.css"
OUTPUT_REPORT_PATH = PROJECT_PATH / "resources" / "templates" / "template_management_summary.docx"

# SCIA templates — integration strips
SCIA_TEMPLATE_PATH = PROJECT_PATH / "resources" / "templates" / "model_governing_integrationstrips.esa"
SCIA_TEMPLATE_FULL_PATH = PROJECT_PATH / "resources" / "templates" / "model_full_integrationstrips.esa"

# SCIA templates — sections on plane
SCIA_TEMPLATE_SECTIONS_ON_PLANE_GOVERNING_PATH = PROJECT_PATH / "resources" / "templates" / "model_governing_sectionsonplane.esa"
SCIA_TEMPLATE_SECTIONS_ON_PLANE_FULL_PATH = PROJECT_PATH / "resources" / "templates" / "model_full_sectionsonplane.esa"

# Data file paths
BRIDGE_DATA_PATH = PROJECT_PATH / "resources" / "data" / "bridges" / "filtered_bridges.json"
REINFORCEMENT_PATH = PROJECT_PATH / "resources" / "data" / "materials" / "betonstaalkwaliteit.csv"
CONCRETEQUALITY_CSV_PATH = PROJECT_PATH / "resources" / "data" / "materials" / "betonkwaliteit.csv"

# Note: Additional material paths are managed by src.common.materials module
