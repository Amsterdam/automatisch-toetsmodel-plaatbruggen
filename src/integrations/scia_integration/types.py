"""
Centralized type definitions for SCIA integration.

This module contains all enums, TypedDicts, and dataclasses used throughout
the SCIA integration modules to ensure consistency and avoid circular imports.
"""

from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import Any, TypedDict

# ===================================================================================================================
# Enums
# ===================================================================================================================


class SciaCombinationType(Enum):
    """
    Enumeration for SCIA Load Combination types, aligned with the VIKTOR SDK.

    These values correspond to the combination types available in SCIA Engineer
    for different analysis purposes (ultimate limit state, serviceability, etc.).
    """

    ENVELOPE_ULTIMATE = "ENVELOPE_ULTIMATE"
    ENVELOPE_SERVICEABILITY = "ENVELOPE_SERVICEABILITY"
    LINEAR_ULTIMATE = "LINEAR_ULTIMATE"
    LINEAR_SERVICEABILITY = "LINEAR_SERVICEABILITY"
    EN_ULS_SET_B = "EN_ULS_SET_B"
    EN_ULS_SET_C = "EN_ULS_SET_C"
    EN_SLS_CHAR = "EN_SLS_CHAR"
    EN_SLS_FREQ = "EN_SLS_FREQ"
    EN_SLS_QUASI = "EN_SLS_QUASI"
    EN_ACC_ONE = "EN_ACC_ONE"
    EN_ACC_TWO = "EN_ACC_TWO"
    EN_SEISMIC = "EN_SEISMIC"


class LoadType(Enum):
    """
    Enumeration of available load types for bridge analysis.

    :param TANDEM: Tandem axle loads (concentrated vehicle loads)
    :param UDL: Uniformly distributed loads (traffic loads)
    """

    TANDEM = "tandem"
    UDL = "udl"


class LoadGroup(Enum):
    """
    Enumeration of available load groups for tandem loads.

    These correspond to different vehicle weight categories:

    :param BG8000: 8000 kg vehicle category
    :param BG9000: 9000 kg vehicle category
    :param BG10000: 10000 kg vehicle category
    """

    BG8000 = "bg8000"
    BG9000 = "bg9000"
    BG10000 = "bg10000"


class UDLGroup(Enum):
    """
    Enumeration of available UDL load groups.

    These represent different lane configurations for uniformly distributed loads:

    :param BG4001: Leftmost lanes loading
    :param BG4002: Rightmost lanes loading
    :param BG4003: Center lanes loading
    """

    BG4001 = "bg4001"  # Leftmost lanes
    BG4002 = "bg4002"  # Rightmost lanes
    BG4003 = "bg4003"  # Center lanes


class LoadMode(Enum):
    """
    Enumeration of load generation modes.

    :param THEORETICAL: Theoretical lane layout based on standard assumptions
    :param ACTUAL: Actual lane layout based on real road geometry
    """

    THEORETICAL = "theoretical"
    ACTUAL = "actual"


# ===================================================================================================================
# TypedDicts
# ===================================================================================================================


class WheelConfig(TypedDict):
    """
    Type definition for standard vehicle wheel configuration.

    :param position: Position identifier for the wheel (e.g., "front", "rear")
    :param side: Side of the vehicle ("left" or "right")
    :param corners_key: Key identifying the corner points for load application
    :param load: Load value in Newtons
    :param axle_locations: Dictionary mapping axle names to coordinate lists
    """

    position: str
    side: str
    corners_key: str
    load: float
    axle_locations: dict[str, list[tuple[float, float, float]]]


class AmsterdamWheelConfig(TypedDict):
    """
    Type definition for Amsterdam vehicle wheel configuration.

    Simplified wheel configuration used for Amsterdam-specific vehicle types.

    :param position: Position identifier for the wheel
    :param corners_key: Key identifying the corner points for load application
    :param load: Load value in Newtons
    """

    position: str
    corners_key: str
    load: float


# ===================================================================================================================
# Dataclasses
# ===================================================================================================================


@dataclass(frozen=True)
class BridgeDimensions:
    """
    Bridge dimensions extracted from parametrization.

    This dataclass provides a structured way to access key bridge dimensions
    that are frequently used throughout the SCIA integration process.

    :param total_length: Total length of the bridge in meters
    :param total_width: Total width of the bridge in meters
    :param thickness: Bridge deck thickness in meters
    :param zone1_width: Width of zone 1 (bz1) in meters
    :param zone2_width: Width of zone 2 (bz2) in meters
    :param zone3_width: Width of zone 3 (bz3) in meters
    :param first_segment_thickness: Thickness of the first segment in meters
    :param first_segment_thickness_2: Secondary thickness parameter (optional)
    """

    total_length: float
    total_width: float
    thickness: float
    zone1_width: float
    zone2_width: float
    zone3_width: float
    first_segment_thickness: float
    first_segment_thickness_2: float = 0.0

    @property
    def zone_widths(self) -> dict[str, float]:
        """
        Get zone widths as a dictionary for backward compatibility.

        :returns: Dictionary mapping zone names to widths
        :rtype: dict[str, float]
        """
        return {
            "bz1": self.zone1_width,
            "bz2": self.zone2_width,
            "bz3": self.zone3_width,
        }


@dataclass
class SegmentGeometry:
    """
    Class to hold segment geometry data for easier access.

    This dataclass encapsulates the geometric properties of a bridge segment,
    including its position and zone boundaries.

    :param index: 1-based index of the segment
    :param x_start: Start x-coordinate in meters
    :param x_end: End x-coordinate in meters
    :param top_y: Top y-coordinate (z1_left) in meters
    :param mid_upper_y: Middle upper y-coordinate (z1_right/z2_left) in meters
    :param mid_lower_y: Middle lower y-coordinate (z2_right/z3_left) in meters
    :param bottom_y: Bottom y-coordinate (z3_right) in meters
    """

    index: int  # 1-based index of the segment
    x_start: float  # Start x-coordinate
    x_end: float  # End x-coordinate
    top_y: float  # Top y-coordinate (z1_left)
    mid_upper_y: float  # Middle upper y-coordinate (z1_right/z2_left)
    mid_lower_y: float  # Middle lower y-coordinate (z2_right/z3_left)
    bottom_y: float  # Bottom y-coordinate (z3_right)


@dataclass
class UnitConversion:
    """
    Represents a unit conversion with both the display unit and conversion factor.

    This dataclass is used to maintain consistency between unit display and
    value conversion throughout the SCIA results processing pipeline.

    :param display_unit: The unit string to display (e.g., "kN", "kNm")
    :param conversion_factor: Factor to convert from raw SCIA units (N->kN = 1/1000)
    :param raw_unit: The original unit from SCIA (for documentation)
    """

    display_unit: str
    conversion_factor: float
    raw_unit: str = ""


# ===================================================================================================================
# Type Aliases
# ===================================================================================================================

# Type aliases for opaque SCIA objects that the builder implementation will handle.
# The src layer treats these as abstract types.
SciaObject = Any
SciaModel = Any
SciaNode = Any
SciaMaterial = Any
SciaPlate = Any
SciaLoadGroup = Any
SciaLoadCase = Any
SciaLoadCombination = Any
SciaLineSupport = Any
SciaFreeSurfaceLoad = Any
SciaLineForceSurface = Any
SciaFreeLineLoad = Any
SciaAnalysis = Any
SciaResults = Any
SciaResultClass = Any
SciaIntegrationStrip = Any
SciaSectionOnPlane = Any

# Type aliases for file objects
SciaFile = BytesIO | bytes

# Type alias to avoid importing from app layer
BridgeParams = Any
BridgeParametrization = Any
