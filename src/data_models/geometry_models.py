"""
Pydantic models for geometric data structures.

This module contains models for geometric calculations, coordinates, and spatial data.
"""

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class TheoreticalLaneResult(BaseModel):
    """
    Result structure for theoretical traffic lane calculations.

    Validates that lane calculations are consistent and within realistic ranges.
    """

    num_lanes: int = Field(ge=0, le=10, description="Number of traffic lanes (0 for very narrow bridges)")
    lane_width: float = Field(ge=2.5, le=4.0, description="Standard lane width in meters")
    rest_width: float = Field(ge=0, description="Remaining width after lanes in meters")
    total_lanes_width: float = Field(ge=0, description="Total width of all lanes in meters (0 if no lanes fit)")

    @field_validator("total_lanes_width")
    @classmethod
    def validate_total_width_consistency(cls, v: float, info: ValidationInfo) -> float:
        """Validate that total lanes width matches num_lanes x lane_width."""
        if info.data and "num_lanes" in info.data and "lane_width" in info.data:
            expected = info.data["num_lanes"] * info.data["lane_width"]
            if abs(v - expected) > 0.01:  # Allow small floating point differences
                raise ValueError(
                    f"Total lanes width {v}m doesn't match "
                    f"num_lanes x lane_width = {info.data['num_lanes']} x {info.data['lane_width']} = {expected}m"
                )
        return v

    model_config = ConfigDict(validate_assignment=True)


class Point3D(BaseModel):
    """
    3D point with validation.

    Represents a point in 3D space, typically used for load positioning
    and geometric calculations in SCIA models.
    """

    x: float = Field(description="X-coordinate in meters")
    y: float = Field(description="Y-coordinate in meters")
    z: float = Field(default=0.0, description="Z-coordinate in meters (typically 0.0 for 2D sections)")

    def to_tuple(self) -> tuple[float, float, float]:
        """
        Convert point to tuple format.

        :returns: (x, y, z) tuple
        :rtype: tuple[float, float, float]
        """
        return (self.x, self.y, self.z)

    model_config = ConfigDict(validate_assignment=True)


class RectangularPolygon(BaseModel):
    """
    Rectangular polygon defined by 4 corner points.

    Used for defining load areas in SCIA models. Points should be ordered
    counter-clockwise starting from bottom-left.
    """

    corners: list[Point3D] = Field(min_length=4, max_length=4, description="4 corner points (counter-clockwise)")

    @field_validator("corners")
    @classmethod
    def validate_rectangle(cls, v: list[Point3D]) -> list[Point3D]:
        """
        Validate that polygon has exactly 4 corners.

        :param v: List of corner points
        :type v: list[Point3D]
        :returns: Validated list of corners
        :rtype: list[Point3D]
        :raises ValueError: If polygon doesn't have exactly 4 corners
        """
        if len(v) != 4:
            raise ValueError("Polygon must have exactly 4 corners")
        return v

    def to_tuple_list(self) -> list[tuple[float, float, float]]:
        """
        Convert all corner points to tuple format.

        :returns: List of (x, y, z) tuples for each corner
        :rtype: list[tuple[float, float, float]]
        """
        return [p.to_tuple() for p in self.corners]

    model_config = ConfigDict(validate_assignment=True)
