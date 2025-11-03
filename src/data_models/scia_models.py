"""
Pydantic models for SCIA integration data structures.

This module contains models for SCIA load configurations, bridge dimensions,
and other SCIA-related data validation.
"""

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
    first_segment_thickness: float = Field(gt=0.1, le=5.0, description="First segment thickness in meters")
    first_segment_thickness_2: float = Field(ge=0, le=5.0, description="Second segment thickness in meters")

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
        # Validate second thickness is not greater than first thickness
        if self.first_segment_thickness_2 > self.first_segment_thickness:
            raise ValueError(
                f"Second segment thickness {self.first_segment_thickness_2}m cannot be greater than "
                f"first segment thickness {self.first_segment_thickness}m"
            )

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


class SectionOnPlaneDefinition(BaseModel):
    """
    Definition for a section on plane object in SCIA analysis.

    Represents a cross-section cutting plane defined by two 3D points.
    Validates coordinate ranges and ensures geometric consistency.

    :param name: Name identifier for the section
    :param point_1: Start coordinates (x, y, z) in meters
    :param point_2: End coordinates (x, y, z) in meters
    :param draw: Optional plane direction (default: None, uses Z_DIRECTION)
    :param direction_of_cut: Optional in-plane vector defining cut direction (default: None, uses (0, 0, 1))
    """

    name: str = Field(min_length=1, description="Section name identifier")
    point_1: tuple[float, float, float] = Field(description="Start coordinates (x, y, z) in meters")
    point_2: tuple[float, float, float] = Field(description="End coordinates (x, y, z) in meters")
    draw: str | None = Field(default=None, description="Optional plane direction")
    direction_of_cut: tuple[float, float, float] | None = Field(default=None, description="Optional cut direction vector")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate section name is not empty."""
        if not v.strip():
            raise ValueError("Section name cannot be empty or whitespace only")
        return v.strip()

    @field_validator("point_1", "point_2")
    @classmethod
    def validate_point_tuple(cls, v: tuple[float, float, float]) -> tuple[float, float, float]:
        """Validate coordinate tuple has exactly 3 elements and reasonable ranges."""
        if len(v) != 3:
            raise ValueError(f"Coordinate tuple must have exactly 3 values (x, y, z), got {len(v)}")

        x, y, z = v

        # Validate coordinate ranges (reasonable bridge dimensions)
        if not (-1000 <= x <= 1000):
            raise ValueError(f"X-coordinate {x}m is unrealistic (must be between -1000 and 1000m)")
        if not (-1000 <= y <= 1000):
            raise ValueError(f"Y-coordinate {y}m is unrealistic (must be between -1000 and 1000m)")
        if not (-100 <= z <= 100):
            raise ValueError(f"Z-coordinate {z}m is unrealistic (must be between -100 and 100m)")

        return v

    @field_validator("direction_of_cut")
    @classmethod
    def validate_direction_of_cut(cls, v: tuple[float, float, float] | None) -> tuple[float, float, float] | None:
        """Validate direction of cut vector if provided."""
        if v is None:
            return None

        if len(v) != 3:
            raise ValueError(f"Direction of cut vector must have exactly 3 values, got {len(v)}")

        # Normalize check - vector should not be zero
        x, y, z = v
        magnitude = (x**2 + y**2 + z**2) ** 0.5
        if magnitude < 1e-10:
            raise ValueError("Direction of cut vector cannot be zero (all components cannot be zero)")

        return v

    @model_validator(mode="after")
    def validate_points_different(self) -> "SectionOnPlaneDefinition":
        """Validate that point_1 and point_2 are different points."""
        if self.point_1 == self.point_2:
            raise ValueError("point_1 and point_2 must be different coordinates")
        return self

    model_config = ConfigDict(validate_assignment=True)
