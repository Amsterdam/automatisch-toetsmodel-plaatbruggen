"""
Pydantic models for geometry data structures.

This module contains models for geometric calculations, coordinate data,
and spatial validation used in bridge analysis.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DPointLabelData(BaseModel):
    """
    Data for D-point labels in bridge geometry visualization.

    Validates label text and coordinate positions.
    """

    text: str = Field(min_length=1, max_length=10, description="Label text (max 10 characters)")
    x: float = Field(description="X coordinate of label position")
    y: float = Field(description="Y coordinate of label position")

    @field_validator("text")
    @classmethod
    def validate_label_text(cls, v: str) -> str:
        """Validate label text format."""
        # Remove whitespace and check for valid characters
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Label text cannot be empty or whitespace only")

        # Check for reasonable label format (letters, numbers, basic punctuation)
        if not all(c.isalnum() or c in ".-_" for c in cleaned):
            raise ValueError("Label text can only contain letters, numbers, dots, hyphens, and underscores")

        return cleaned

    @field_validator("x", "y")
    @classmethod
    def validate_coordinates(cls, v: float) -> float:
        """Validate coordinate values."""
        if not (-10000 <= v <= 10000):
            raise ValueError(f"Coordinate {v} is unrealistic (must be between -10000 and 10000)")
        return v

    model_config = ConfigDict(validate_assignment=True)


class LoadZoneGeometryData(BaseModel):
    """
    Geometric data for load zone visualization and analysis.

    Validates coordinate consistency and geometric constraints for
    bridge cross-section visualization.
    """

    x_coords_d_points: list[float] = Field(min_length=0, max_length=15, description="X coordinates of D-points in meters")
    y_top_structural_edge_at_d_points: list[float] = Field(
        min_length=0, max_length=15, description="Y coordinates of top structural edge at D-points"
    )
    total_widths_at_d_points: list[float] = Field(min_length=0, max_length=15, description="Total widths at each D-point")
    y_bridge_bottom_at_d_points: list[float] = Field(min_length=0, max_length=15, description="Y coordinates of bridge bottom at D-points")
    num_defined_d_points: int = Field(ge=0, le=15, description="Number of defined D-points")
    d_point_label_data: list[DPointLabelData] = Field(description="Label data for each D-point")

    @field_validator("x_coords_d_points")
    @classmethod
    def validate_x_coords_ascending(cls, v: list[float]) -> list[float]:
        """Validate X coordinates are unique and in ascending order."""
        if len(v) != len(set(v)):
            raise ValueError("X coordinates must be unique (no duplicate D-points)")
        if v != sorted(v):
            raise ValueError("X coordinates must be in ascending order along bridge length")
        return v

    @model_validator(mode="after")
    def validate_coordinate_consistency(self) -> "LoadZoneGeometryData":
        """Validate coordinate consistency and relationships."""
        # Validate coordinate arrays have matching lengths
        expected_length = len(self.x_coords_d_points)

        if len(self.y_top_structural_edge_at_d_points) != expected_length:
            raise ValueError(
                f"y_top_structural_edge_at_d_points length {len(self.y_top_structural_edge_at_d_points)} doesn't match x_coords_d_points length {expected_length}"
            )

        if len(self.total_widths_at_d_points) != expected_length:
            raise ValueError(
                f"total_widths_at_d_points length {len(self.total_widths_at_d_points)} doesn't match x_coords_d_points length {expected_length}"
            )

        if len(self.y_bridge_bottom_at_d_points) != expected_length:
            raise ValueError(
                f"y_bridge_bottom_at_d_points length {len(self.y_bridge_bottom_at_d_points)} doesn't match x_coords_d_points length {expected_length}"
            )

        # Validate that top edge coordinates are above bottom edge coordinates
        for i, (top, bottom) in enumerate(zip(self.y_top_structural_edge_at_d_points, self.y_bridge_bottom_at_d_points)):
            if top < bottom:
                raise ValueError(f"Top edge coordinate {top} at D-point {i + 1} is below bottom edge coordinate {bottom}")

        # Validate that num_defined_d_points matches actual data length
        if self.num_defined_d_points != expected_length:
            raise ValueError(f"num_defined_d_points {self.num_defined_d_points} doesn't match actual data length {expected_length}")

        # Validate that label data count matches D-points count
        if len(self.d_point_label_data) != self.num_defined_d_points:
            raise ValueError(f"Label data count {len(self.d_point_label_data)} doesn't match num_defined_d_points {self.num_defined_d_points}")

        return self

    @field_validator("total_widths_at_d_points")
    @classmethod
    def validate_widths_positive(cls, v: list[float]) -> list[float]:
        """Validate that all widths are positive."""
        for i, width in enumerate(v):
            if width <= 0:
                raise ValueError(f"Total width {width} at D-point {i + 1} must be positive")
        return v

    @field_validator("x_coords_d_points", "y_top_structural_edge_at_d_points", "y_bridge_bottom_at_d_points")
    @classmethod
    def validate_coordinate_ranges(cls, v: list[float]) -> list[float]:
        """Validate coordinate values are within reasonable ranges."""
        for i, coord in enumerate(v):
            if not (-1000 <= coord <= 1000):
                field_name = "coordinate"
                if hasattr(cls, "__annotations__"):
                    # Try to get field name from context
                    pass
                raise ValueError(f"Coordinate {coord} at index {i} is unrealistic (must be between -1000 and 1000)")
        return v

    model_config = ConfigDict(validate_assignment=True)
