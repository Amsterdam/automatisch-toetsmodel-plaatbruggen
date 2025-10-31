"""
Geometry constants for calculations, offsets, and rendering.

These constants define default values for geometric calculations, offsets,
spacing, and 3D model rendering parameters used throughout the geometry module.
"""

# Default offsets and spacing
DEFAULT_LABEL_Y_OFFSET = 1.5  # m - Vertical offset for D-point labels
TOP_VIEW_LABEL_Y_OFFSET = 0.5  # m - Reduced offset for D labels in top view
DIMENSION_TEXT_Y_OFFSET = 1.0  # m - Offset for dimension text below bridge
SUPPORT_ANNOTATION_OFFSET = 0.5  # m - Offset below bridge for support symbols

# Default lane and zone properties
DEFAULT_LANE_WIDTH = 3.0  # m - Standard traffic lane width
DEFAULT_AUTO_ZONE_PAVEMENT_THICKNESS = 0.1  # m - 10cm asphalt for traffic lanes
DEFAULT_BERM_ZONE_PAVEMENT_THICKNESS = 0.05  # m - 5cm gravel for rest area

# Geometry calculation factors
MIDPOINT_DIVISOR = 2.0  # Divisor for calculating midpoints (e.g., (pos1 + pos2) / 2.0)
REBAR_POSITION_HALF_OFFSET = 0.5  # Offset for rebar position calculation (e.g., (i + 0.5) * hoh)

# 3D model rendering
AXES_LENGTH_DEFAULT = 5.0  # m - Default axes length
AXES_RADIUS_DEFAULT = 0.05  # m - Default axes radius
AXES_CYLINDER_SECTIONS = 20  # Number of sections for axes cylinders
CYLINDER_SECTIONS_DEFAULT = 16  # Number of sections for general cylinder creation
PLANE_THICKNESS = 0.01  # m - Thickness of section planes
MODEL_PADDING = 5  # m - Padding added to model bounds
BLACK_DOT_RADIUS = 0.1  # m - Radius of origin marker dot

# Annotation positioning
TEXT_X_OFFSET_CROSS_SECTION = 0.75  # m - Offset for text in cross-section view
ZONE_LABEL_X_OFFSET = 2.0  # m - X offset for zone labels in load zone plot
ANNOTATION_Y_OFFSET_CROSS_SECTION = 1.0  # m - Y offset below bridge for annotations
ANNOTATION_Y_OFFSET_HORIZONTAL = 0.5  # m - Y offset above bridge for horizontal section
DIMENSION_TEXT_X_OFFSET = 0.5  # m - X offset for dimension text in longitudinal section
MIN_DISPLAY_WIDTH = 0.01  # m - Minimum width for displaying dimension annotations
