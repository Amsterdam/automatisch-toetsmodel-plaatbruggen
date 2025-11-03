"""
Technical constants for calculations, limits, and factors.

These constants define technical limits, calculation factors, and other
engineering parameters used throughout the application.
"""

from enum import Enum

# Maximum number of D-fields (D1 to D15) supported for load zones
MAX_LOAD_ZONE_SEGMENT_FIELDS = 15

# Unit conversion factors
MM_TO_M = 1000.0  # Conversion factor from millimeters to meters

# Signage load factors for "Werkelijke wegindeling met bebording"
# Maps to signage options: ["50 ton", "45 ton", "40 ton", "35 ton", "30 ton", "25 ton", "20 ton"]
SIGNAGE_LOAD_FACTORS = [0.83, 0.75, 0.67, 0.58, 0.5, 0.42, 0.33]

INTEGRATION_STRIP_WIDTH = 1.0  # Width of integration strips in meters
EDGE_OFFSET = 0.5  # Offset from the edge of the road for strip placement in meters

# Standard reinforcement bar diameters in millimeters
STANDARD_REBAR_DIAMETERS = {6, 8, 10, 12, 14, 16, 20, 25, 32, 40}


# Enumeration of supported analysis types
class AnalysisType(Enum):
    """Enumeration of supported analysis types."""

    SCIA = "scia"
    IDEA = "idea"
