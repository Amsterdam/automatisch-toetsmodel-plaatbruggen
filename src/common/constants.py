"""
Common constants used across the src layer.

These constants are shared between different modules in the src layer
and should not depend on the app layer (VIKTOR SDK).
"""

from enum import Enum

# Maximum number of D-fields (D1 to D15) supported for load zones
MAX_LOAD_ZONE_SEGMENT_FIELDS = 15


class AnalysisType(Enum):
    """Enumeration of supported analysis types."""

    SCIA = "scia"
    IDEA = "idea"
