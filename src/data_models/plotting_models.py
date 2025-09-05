"""
Pydantic models for plotting and visualization data structures.

This module contains models for bridge geometry plotting, zone styling, and visualization data.
"""

from typing import Any

import plotly.graph_objects as go
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class BridgeBaseGeometry(BaseModel):
    """
    Base geometry data for bridge plotting.

    Validates coordinate consistency and geometric constraints.
    """

    x_coords_d_points: list[float] = Field(min_length=1, max_length=15, description="X coordinates of D-points in meters")
    y_coords_bridge_top_edge: list[float] = Field(min_length=1, max_length=15, description="Y coordinates of bridge top edge in meters")
    y_coords_bridge_bottom_edge: list[list[float]] = Field(min_length=1, max_length=15, description="Y coordinates of bridge bottom edge boundaries")
    num_defined_d_points: int = Field(ge=1, le=15, description="Number of defined D-points")

    @field_validator("x_coords_d_points")
    @classmethod
    def validate_x_coords_ascending(cls, v: list[float]) -> list[float]:
        """Validate X coordinates are unique and in ascending order."""
        if len(v) != len(set(v)):
            raise ValueError("X coordinates must be unique (no duplicate D-points)")
        if v != sorted(v):
            raise ValueError("X coordinates must be in ascending order along bridge length")
        return v

    @field_validator("y_coords_bridge_top_edge")
    @classmethod
    def validate_top_edge_length(cls, v: list[float], info: ValidationInfo) -> list[float]:
        """Validate top edge coordinates match number of D-points."""
        if info.data and "num_defined_d_points" in info.data:
            expected_length = info.data["num_defined_d_points"]
            if len(v) != expected_length:
                raise ValueError(f"Top edge coordinates length {len(v)} doesn't match num_defined_d_points {expected_length}")
        return v

    @field_validator("y_coords_bridge_bottom_edge")
    @classmethod
    def validate_bottom_edge_structure(cls, v: list[list[float]], info: ValidationInfo) -> list[list[float]]:
        """Validate bottom edge coordinate structure."""
        if info.data and "num_defined_d_points" in info.data:
            expected_length = info.data["num_defined_d_points"]
            if len(v) != expected_length:
                raise ValueError(f"Bottom edge coordinates length {len(v)} doesn't match num_defined_d_points {expected_length}")

        # Each bottom edge should have exactly 2 coordinates [min, max]
        for i, coords in enumerate(v):
            if len(coords) != 2:
                raise ValueError(f"Bottom edge at D-point {i + 1} must have exactly 2 coordinates, got {len(coords)}")
            if coords[0] > coords[1]:
                raise ValueError(f"Bottom edge at D-point {i + 1}: min ({coords[0]}) must be ≤ max ({coords[1]})")

        return v

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)


class ZoneStylingDefaults(BaseModel):
    """Zone styling defaults for appearance mapping and colors."""

    zone_appearance_map: dict[str, dict[str, Any]] = Field(description="Mapping of zone types to their visual appearance properties")
    default_plotly_colors: list[str] = Field(min_length=1, description="List of default Plotly colors for zones")

    @field_validator("zone_appearance_map")
    @classmethod
    def validate_appearance_map_structure(cls, v: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Validate that appearance map has required styling properties."""
        required_properties = {"line_color", "fill_color"}

        for zone_type, properties in v.items():
            missing_props = required_properties - set(properties.keys())
            if missing_props:
                raise ValueError(f"Zone type '{zone_type}' missing required properties: {missing_props}")

        return v

    model_config = ConfigDict(validate_assignment=True)


class ZoneBoundaryLineStyle(BaseModel):
    """Styling parameters for zone boundary lines."""

    line_color: str = Field(min_length=1, description="Color of the boundary line")
    sbs_line_thickness: float = Field(ge=0, le=10, description="Side-by-side line thickness")
    sbs_offset: float = Field(ge=0, le=5, description="Side-by-side offset distance")
    absolute_edge_thickness: float = Field(ge=0, le=10, description="Absolute edge line thickness")

    @field_validator("line_color")
    @classmethod
    def validate_color_format(cls, v: str) -> str:
        """Validate color is a valid format (basic check)."""
        # Basic validation - could be enhanced with more sophisticated color validation
        if not v.strip():
            raise ValueError("Line color cannot be empty")
        return v.strip()

    model_config = ConfigDict(validate_assignment=True)


class ZonePlottingGeometry(BaseModel):
    """Geometry data for plotting individual load zones."""

    x_coords: list[float] = Field(min_length=1, description="X coordinates along zone")
    y_coords_top: list[float] = Field(min_length=1, description="Y coordinates of zone top boundary")
    y_coords_bottom: list[float] = Field(min_length=1, description="Y coordinates of zone bottom boundary")

    @field_validator("y_coords_top", "y_coords_bottom")
    @classmethod
    def validate_coordinate_lengths_match(cls, v: list[float], info: ValidationInfo) -> list[float]:
        """Validate all coordinate arrays have same length."""
        if info.data and "x_coords" in info.data:
            expected_length = len(info.data["x_coords"])
            if len(v) != expected_length:
                raise ValueError(f"Coordinate array length {len(v)} doesn't match x_coords length {expected_length}")
        return v

    @field_validator("y_coords_top")
    @classmethod
    def validate_top_above_bottom(cls, v: list[float], info: ValidationInfo) -> list[float]:
        """Validate that top coordinates are above bottom coordinates."""
        if info.data and "y_coords_bottom" in info.data:
            bottom_coords = info.data["y_coords_bottom"]
            if len(v) == len(bottom_coords):
                for i, (top, bottom) in enumerate(zip(v, bottom_coords)):
                    if top < bottom:
                        raise ValueError(f"Top coordinate {top} at index {i} is below bottom coordinate {bottom}")
        return v

    model_config = ConfigDict(validate_assignment=True)


class PlotPresentationDetails(BaseModel):
    """Ancillary details related to plot presentation."""

    base_traces: list[go.Scatter] | None = Field(default=None, description="Base Plotly traces for the plot")
    validation_messages: list[str] | None = Field(default=None, description="Validation messages to display")
    figure_title: str = Field(min_length=1, description="Title for the plot figure")

    @field_validator("validation_messages")
    @classmethod
    def validate_messages_not_empty(cls, v: list[str] | None) -> list[str] | None:
        """Ensure validation messages are not empty strings if provided."""
        if v is not None:
            non_empty_messages = [msg.strip() for msg in v if msg.strip()]
            return non_empty_messages if non_empty_messages else None
        return v

    model_config = ConfigDict(
        validate_assignment=True,
        # Allow arbitrary types for Plotly objects
        arbitrary_types_allowed=True,
    )
