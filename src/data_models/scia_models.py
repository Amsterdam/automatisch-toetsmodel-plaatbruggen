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
