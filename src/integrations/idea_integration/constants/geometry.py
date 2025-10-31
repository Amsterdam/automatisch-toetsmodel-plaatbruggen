"""
Geometry constants for IDEA StatiCa integration.

These constants define geometry-related values used in IDEA RCS model creation,
including slab dimensions, rebar positioning, and direction vectors.
"""

# Slab geometry constants
SLAB_WIDTH = 1.0  # meters - IDEA slab cross-section width

# Rebar positioning constants
MIDPOINT_DIVISOR = 2.0  # For calculating midpoints between rebars
REBAR_POSITION_HALF_OFFSET = 0.5  # Half offset for even rebar spacing calculations
SLAB_EDGE_SPACE_BOUNDARY = 0.5  # meters - Remaining space boundary at slab end for additional reinforcement

# Direction vector constants
DIRECTION_VECTOR_THRESHOLD = 0.7  # Threshold for strip orientation detection (absolute value)
DEFAULT_DIRECTION_VECTOR_X = (1.0, 0.0, 0.0)  # Default x-direction vector
