"""
Material property constants for IDEA StatiCa integration.

These constants define default material properties and values
used in IDEA RCS material creation and processing.
"""

# Default material properties
DEFAULT_YOUNGS_MODULUS = 200000.0  # MPa - Default Young's modulus for concrete
DEFAULT_STONE_DIAMETER = 16.0  # mm - Default stone diameter for concrete

# Rebar positioning constants
DEFAULT_REBAR_POSITION_BASE = 1000  # Base value for rebar position calculations

# Default material values
DEFAULT_CONCRETE_STRENGTH_CLASS = "C30/37"  # Default concrete strength class
DEFAULT_STEEL_QUALITY = "B500B"  # Default reinforcement steel quality
DEFAULT_BRIDGE_NAME = "Unnamed Bridge"  # Default bridge name when not provided

# Material property defaults
DEFAULT_STEEL_UNIT_MASS = 7850.0  # kg/m³ - Standard steel unit mass
DEFAULT_CONCRETE_UNIT_MASS = 2450.0  # kg/m³ - Standard concrete unit mass
DEFAULT_FTK_TO_FYK_RATIO = 1.08  # Default ratio of tensile strength to yield strength for reinforcement
DEFAULT_EPSUK = 50.0  # Default ultimate strain (in 1e-4 units for API)
DEFAULT_REINFORCEMENT_CLASS = "B"  # Default reinforcement class
