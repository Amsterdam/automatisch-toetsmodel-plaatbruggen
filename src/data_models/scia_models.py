"""
Pydantic models for SCIA integration data structures.

This module contains models for SCIA load configurations, bridge dimensions,
and other SCIA-related data validation.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WheelLoadConfig(BaseModel):
    """
    Configuration for standard vehicle wheel loads in SCIA analysis.

    Validates wheel position, side, load magnitude, and axle locations
    according to traffic engineering standards.
    """

    position: str = Field(min_length=1, description="Wheel position (front, rear, middle)")
    side: str = Field(min_length=1, description="Wheel side (left, right)")
    corners_key: str = Field(min_length=1, description="Key identifying corner geometry")
    load: float = Field(gt=0, le=200, description="Wheel load in kN (0-200kN range)")
    axle_locations: dict[str, list[tuple[float, float, float]]] = Field(description="Dictionary mapping axle names to 3D coordinate lists")

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: str) -> str:
        """Validate wheel position against allowed values."""
        allowed_positions = {"front", "rear", "middle", "front_left", "front_right", "rear_left", "rear_right"}
        if v.lower() not in allowed_positions:
            raise ValueError(f"Position '{v}' not allowed. Must be one of: {', '.join(allowed_positions)}")
        return v.lower()

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate wheel side against allowed values."""
        allowed_sides = {"left", "right"}
        if v.lower() not in allowed_sides:
            raise ValueError(f"Side '{v}' not allowed. Must be one of: {', '.join(allowed_sides)}")
        return v.lower()

    @field_validator("axle_locations")
    @classmethod
    def validate_axle_locations(cls, v: dict[str, list[tuple[float, float, float]]]) -> dict[str, list[tuple[float, float, float]]]:
        """Validate axle location coordinates."""
        for axle_name, coordinates in v.items():
            if not coordinates:
                raise ValueError(f"Axle '{axle_name}' must have at least one coordinate")

            for i, coord in enumerate(coordinates):
                if len(coord) != 3:
                    raise ValueError(f"Axle '{axle_name}' coordinate {i} must have exactly 3 values (x, y, z)")

                # Check for reasonable coordinate ranges (assuming meters)
                x, y, z = coord
                if not (-1000 <= x <= 1000):
                    raise ValueError(f"Axle '{axle_name}' x-coordinate {x} is unrealistic (must be -1000 to 1000m)")
                if not (-1000 <= y <= 1000):
                    raise ValueError(f"Axle '{axle_name}' y-coordinate {y} is unrealistic (must be -1000 to 1000m)")
                if not (-100 <= z <= 100):
                    raise ValueError(f"Axle '{axle_name}' z-coordinate {z} is unrealistic (must be -100 to 100m)")

        return v

    model_config = ConfigDict(validate_assignment=True)


class AmsterdamWheelLoadConfig(BaseModel):
    """
    Configuration for Amsterdam-specific vehicle wheel loads.

    Simplified version of WheelLoadConfig for Amsterdam traffic regulations.
    """

    position: str = Field(min_length=1, description="Wheel position (front, rear, middle)")
    corners_key: str = Field(min_length=1, description="Key identifying corner geometry")
    load: float = Field(gt=0, le=200, description="Wheel load in kN (0-200kN range)")

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: str) -> str:
        """Validate wheel position against allowed values."""
        allowed_positions = {"front", "rear", "middle"}
        if v.lower() not in allowed_positions:
            raise ValueError(f"Position '{v}' not allowed. Must be one of: {', '.join(allowed_positions)}")
        return v.lower()

    @field_validator("load")
    @classmethod
    def validate_load_realistic(cls, v: float) -> float:
        """Validate load is realistic for Amsterdam traffic."""
        if v < 10:
            raise ValueError(f"Load {v}kN is too light for Amsterdam traffic (minimum 10kN)")
        if v > 150:
            raise ValueError(f"Load {v}kN exceeds Amsterdam traffic limits (maximum 150kN)")
        return v

    model_config = ConfigDict(validate_assignment=True)


class BridgeDimensionsData(BaseModel):
    """
    Bridge dimensions extracted from parametrization for SCIA analysis.

    Validates geometric consistency and realistic dimension ranges.
    """

    total_length: float = Field(gt=0, le=1000, description="Total bridge length in meters")
    total_width: float = Field(gt=0, le=100, description="Total bridge width in meters")
    thickness: float = Field(gt=0.1, le=5.0, description="Bridge deck thickness in meters")
    zone1_width: float = Field(gt=0, le=50, description="Zone 1 width in meters")
    zone2_width: float = Field(gt=0, le=50, description="Zone 2 width in meters")
    zone3_width: float = Field(gt=0, le=50, description="Zone 3 width in meters")
    first_segment_thickness: float = Field(gt=0.1, le=5.0, description="Thickness of zones 1 and 3 (dz) in meters")
    first_segment_thickness_2: float = Field(ge=0, le=5.0, description="Thickness of zone 2 (dz_2) in meters")

    @field_validator("zone1_width", "zone2_width", "zone3_width")
    @classmethod
    def validate_zone_widths(cls, v: float) -> float:
        """Validate individual zone widths."""
        if v < 0.1:
            raise ValueError(f"Zone width {v}m is too narrow (minimum 0.1m)")
        return v

    @model_validator(mode="after")
    def validate_thickness_and_width_consistency(self) -> "BridgeDimensionsData":
        """Validate thickness and width consistency."""
        # Note: Zone thicknesses (dz and dz_2) can differ in the cross-section (transverse direction).
        # Zones 1 and 3 can have different thickness than zone 2.
        # Longitudinal consistency (same thickness along bridge length) is validated elsewhere.

        # Validate that zone widths don't exceed total width
        total_zone_width = self.zone1_width + self.zone2_width + self.zone3_width
        if total_zone_width > self.total_width:
            raise ValueError(f"Sum of zone widths {total_zone_width}m exceeds total bridge width {self.total_width}m")

        return self

    @property
    def zone_widths(self) -> dict[str, float]:
        """Get zone widths as a dictionary for backward compatibility."""
        return {
            "bz1": self.zone1_width,
            "bz2": self.zone2_width,
            "bz3": self.zone3_width,
        }

    model_config = ConfigDict(validate_assignment=True)


class Span(BaseModel):
    """
    Represents a span in the bridge structure for UDL generation.

    A span is defined by segments between two supports. Contains geometric properties
    and information about intermediate segment boundaries.

    Note: This model is used by UDL generators to identify bridge spans.

    :param start_x: X-coordinate where the span starts in [m]
    :param end_x: X-coordinate where the span ends in [m]
    :param length: Total length of the span in [m]
    :param width: Total width of the span (bz1 + bz2 + bz3) in [m]
    :param bz1: Width of zone 1 in [m]
    :param bz2: Width of zone 2 in [m]
    :param bz3: Width of zone 3 in [m]
    :param min_thickness: Minimum thickness (min of dz and dz_2) in [m]
    :param span_index: Index of the span (1-based)
    :param num_segment_definitions: Number of segment definition points within the span
    :param intermediate_segment_x_positions: X-coordinates of intermediate segment boundaries in [m]
    """

    start_x: float = Field(ge=0, le=1000, description="X-coordinate where the span starts in [m]")
    end_x: float = Field(ge=0, le=1000, description="X-coordinate where the span ends in [m]")
    length: float = Field(gt=0, le=1000, description="Total length of the span in [m]")
    width: float = Field(gt=0, le=100, description="Total width of the span in [m]")
    bz1: float = Field(ge=0, le=50, description="Width of zone 1 in [m]")
    bz2: float = Field(ge=0, le=50, description="Width of zone 2 in [m]")
    bz3: float = Field(ge=0, le=50, description="Width of zone 3 in [m]")
    min_thickness: float = Field(gt=0.05, le=5.0, description="Minimum thickness in [m]")
    span_index: int = Field(gt=0, description="Index of the span (1-based)")
    num_segment_definitions: int = Field(ge=2, description="Number of segment definition points")
    intermediate_segment_x_positions: list[float] = Field(default_factory=list, description="X-coordinates of intermediate segment boundaries in [m]")

    @field_validator("end_x")
    @classmethod
    def validate_end_after_start(cls, v: float, info: Any) -> float:  # noqa: ANN401
        """Validate end_x is after start_x."""
        start_x = info.data.get("start_x")
        if start_x is not None and v <= start_x:
            raise ValueError("end_x must be greater than start_x")
        return v

    model_config = ConfigDict(validate_assignment=True)


class LoadConfiguration(str):
    """
    Load configuration types for UDL generation.

    Represents the three different UDL load configurations:
    - Conf. A: Leftmost lanes configuration
    - Conf. B: Rightmost lanes configuration
    - Conf. C: Center lanes configuration
    """

    __slots__ = ()

    CONF_A = "Conf. A"
    CONF_B = "Conf. B"
    CONF_C = "Conf. C"


class UdlLoadCaseData(BaseModel):
    """
    Data for a single UDL load case.

    Represents a uniformly distributed load case with its associated polygon,
    load value, and descriptive title for SCIA analysis.
    """

    polygon: list[tuple[float, float, float]] = Field(min_length=4, max_length=4, description="4-point rectangular polygon (counter-clockwise)")
    load: float = Field(gt=0, description="Load value in N/m² (must be positive)")
    title: str = Field(min_length=1, description="Descriptive title for load case")

    @field_validator("load")
    @classmethod
    def validate_positive_load(cls, v: float) -> float:
        """
        Validate that load value is positive.

        :param v: Load value in N/m²
        :type v: float
        :returns: Validated load value
        :rtype: float
        :raises ValueError: If load is not positive
        """
        if v <= 0:
            raise ValueError(f"Load must be positive, got {v}")
        return v

    @field_validator("polygon")
    @classmethod
    def validate_polygon_points(cls, v: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
        """
        Validate polygon points structure.

        :param v: List of polygon corner points
        :type v: list[tuple[float, float, float]]
        :returns: Validated polygon points
        :rtype: list[tuple[float, float, float]]
        :raises ValueError: If polygon doesn't have exactly 4 points or invalid coordinate structure
        """
        if len(v) != 4:
            raise ValueError(f"Polygon must have exactly 4 corners, got {len(v)}")

        for i, point in enumerate(v):
            if not isinstance(point, tuple) or len(point) != 3:
                raise ValueError(f"Point {i} must be a 3-element tuple (x, y, z), got {point}")

        return v

    model_config = ConfigDict(validate_assignment=True)
