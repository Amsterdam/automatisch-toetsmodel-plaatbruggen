"""
Constants package for IDEA StatiCa integration.

This package contains constants specific to IDEA RCS integration,
including material properties, unit conversions, and file paths.
"""

from .materials import (
    DEFAULT_REBAR_POSITION_BASE,
    DEFAULT_STONE_DIAMETER,
    DEFAULT_YOUNGS_MODULUS,
)
from .paths import IDEA_MATERIALS_PATH
from .units import M_TO_MM_IDEA, MM_TO_M_IDEA

__all__ = [
    "DEFAULT_REBAR_POSITION_BASE",
    "DEFAULT_STONE_DIAMETER",
    "DEFAULT_YOUNGS_MODULUS",
    "IDEA_MATERIALS_PATH",
    "MM_TO_M_IDEA",
    "M_TO_MM_IDEA",
]
