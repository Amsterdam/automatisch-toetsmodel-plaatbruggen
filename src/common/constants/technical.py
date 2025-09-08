"""
Technical constants for calculations, limits, and factors.

These constants define technical limits, calculation factors, and other
engineering parameters used throughout the application.
"""

from enum import Enum

# Maximum number of D-fields (D1 to D15) supported for load zones
MAX_LOAD_ZONE_SEGMENT_FIELDS = 15

# Signage load factors for "Werkelijke wegindeling onderliggend wegennet met bebording"
# Maps to signage options: ["50 ton", "45 ton", "40 ton", "35 ton", "30 ton", "25 ton", "20 ton"]
SIGNAGE_LOAD_FACTORS = [0.83, 0.75, 0.67, 0.58, 0.5, 0.42, 0.33]


# Enumeration of supported analysis types
class AnalysisType(Enum):
    """Enumeration of supported analysis types."""

    SCIA = "scia"
    IDEA = "idea"
