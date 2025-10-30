"""
Constants package for the src layer.

This package contains specialized constants files organized by purpose:
- parametrization: UI field options and validation constants
- technical: Technical limits, factors, and calculation constants
- plotting: Visualization styling and appearance constants
"""

# Import all constants for backward compatibility
from .parametrization import (
    CC_CLASS_OPTIONS,
    DESIGN_CODE_OPTIONS,
    LOAD_ZONE_TYPES,
    PAVEMENT_MATERIAL_OPTIONS,
    SUPPORT_TYPE_FIXED,
    SUPPORT_TYPE_FLEXIBLE,
    SUPPORT_TYPE_NONE,
    SUPPORT_TYPE_OPTIONS,
)
from .plotting import (
    DEFAULT_PLOTLY_COLORS,
    DEFAULT_ZONE_APPEARANCE_MAP,
    ZONE_BOUNDARY_ABSOLUTE_EDGE_THICKNESS,
    ZONE_BOUNDARY_SBS_LINE_THICKNESS,
    ZONE_BOUNDARY_SBS_OFFSET,
)
from .technical import (
    MAX_LOAD_ZONE_SEGMENT_FIELDS,
    SIGNAGE_LOAD_FACTORS,
)

__all__ = [
    "CC_CLASS_OPTIONS",
    "DEFAULT_PLOTLY_COLORS",
    "DEFAULT_ZONE_APPEARANCE_MAP",
    "DESIGN_CODE_OPTIONS",
    "LOAD_ZONE_TYPES",
    "MAX_LOAD_ZONE_SEGMENT_FIELDS",
    "PAVEMENT_MATERIAL_OPTIONS",
    "SIGNAGE_LOAD_FACTORS",
    "SUPPORT_TYPE_FIXED",
    "SUPPORT_TYPE_FLEXIBLE",
    "SUPPORT_TYPE_NONE",
    "SUPPORT_TYPE_OPTIONS",
    "ZONE_BOUNDARY_ABSOLUTE_EDGE_THICKNESS",
    "ZONE_BOUNDARY_SBS_LINE_THICKNESS",
    "ZONE_BOUNDARY_SBS_OFFSET",
]
