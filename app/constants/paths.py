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
CHANGELOG_PATH = PROJECT_PATH / "CHANGELOG.md"

# Resource paths
CSS_PATH = PROJECT_PATH / "resources" / "styles" / "style.css"
OUTPUT_REPORT_PATH = PROJECT_PATH / "resources" / "templates" / "template_eindrapport.docx"
SCIA_TEMPLATE_PATH = PROJECT_PATH / "resources" / "templates" / "model.esa"

# Data file paths
BRIDGE_DATA_PATH = PROJECT_PATH / "resources" / "data" / "bridges" / "filtered_bridges.json"
REINFORCEMENT_PATH = PROJECT_PATH / "resources" / "data" / "materials" / "betonstaalkwaliteit.csv"
CONCRETEQUALITY_CSV_PATH = PROJECT_PATH / "resources" / "data" / "materials" / "betonkwaliteit.csv"

# Note: Additional material paths are managed by src.common.materials module
