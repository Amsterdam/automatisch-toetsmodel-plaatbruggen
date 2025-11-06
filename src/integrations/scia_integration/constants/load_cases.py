"""
Load case naming and title constants for SCIA integration.

These constants define the standardized naming conventions and formatting
for load cases across different load types (UDL, tandem systems, service vehicles, etc.).
"""

# Load case naming prefixes
UDL_LOAD_CASE_PREFIX = "BG4"
TANDEM_RS1_PREFIX = "BG8"
TANDEM_RS2_PREFIX = "BG9"
TANDEM_RS3_PREFIX = "BG10"
TRAM_TRACK1_PREFIX = "BG11"
TRAM_TRACK2_PREFIX = "BG12"
SERVICE_VEHICLE_PREFIX = "BG6"
UNINTENDED_VEHICLE_PREFIX = "BG7"

# Load case number formatting
LOAD_CASE_NUMBER_WIDTH = 3  # For :03d formatting (BG4001, BG8001, etc.)

# Title components for UDL load cases
CONFIGURATION_A = "Conf. A"
CONFIGURATION_B = "Conf. B"
CONFIGURATION_C = "Conf. C"
LANE_TITLE_PREFIX = "RS"
REST_AREA_TITLE_PREFIX = "rest"
TITLE_SEPARATOR = " - "
SPAN_LABEL = "Span"

# Geometry constants for load positioning
DEFAULT_Z_COORDINATE = 0.0  # Z-coordinate for 2D load positioning (typically 0.0)
HALF_WIDTH_DIVISOR = 2.0  # Divisor for calculating half-width from full width
