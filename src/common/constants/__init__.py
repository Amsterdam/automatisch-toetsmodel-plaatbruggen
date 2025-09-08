"""
Constants package for the src layer.

This package contains specialized constants files organized by purpose:
- parametrization: UI field options and validation constants
- technical: Technical limits, factors, and calculation constants
"""

# Import all constants for backward compatibility
from .parametrization import (
    CC_CLASS_OPTIONS,
    DESIGN_CODE_OPTIONS,
    LOAD_ZONE_TYPES,
    PAVEMENT_MATERIAL_OPTIONS,
)
from .technical import (
    MAX_LOAD_ZONE_SEGMENT_FIELDS,
    SIGNAGE_LOAD_FACTORS,
)

__all__ = [
    "CC_CLASS_OPTIONS",
    "DESIGN_CODE_OPTIONS",
    "LOAD_ZONE_TYPES",
    "MAX_LOAD_ZONE_SEGMENT_FIELDS",
    "PAVEMENT_MATERIAL_OPTIONS",
    "SIGNAGE_LOAD_FACTORS",
]
