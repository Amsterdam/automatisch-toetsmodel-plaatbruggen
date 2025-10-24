"""
Geometry and lane constants for SCIA integration.

These constants define lane dimensions, bridge geometry thresholds,
and spatial relationships used in load positioning calculations.
"""

# Lane dimensions
DEFAULT_LANE_WIDTH = 3.0  # Standard lane width in meters

# Tandem system wheel offsets and spacing
TANDEM_WHEEL_SPACING_LONGITUDINAL = 1.2  # Distance between wheels in longitudinal direction (meters)
TANDEM_WHEEL_SPACING_TRANSVERSE = 2.0  # Distance between wheels in transverse direction (meters)

# Bridge geometry thresholds
MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES = 9.0  # Minimum bridge width for certain lane configurations (meters)

# Load positioning offsets
TANDEM_START_Y_OFFSET = 1.2  # Y-offset for tandem positioning calculations (meters)
LANE_CENTER_OFFSET_FACTOR = 0.5  # Factor for lane center calculations (0.5 = half lane width)

# Vehicle positioning
VEHICLE_INSET_FROM_BRIDGE_EDGE = 0.5  # Standard inset distance from bridge edge (meters)

# Vehicle dimensions
TANDEM_VEHICLE_LENGTH = 1.6  # Length of tandem vehicle for sequencing (meters)

# Tandem system spacing and positioning
TANDEM_SPACING_LONGITUDINAL = 0.5  # Default spacing between tandem systems (meters)
TANDEM_START_Y_OFFSET_FACTOR = 0.9  # Factor for tandem start Y calculation (0.9 * thickness)
