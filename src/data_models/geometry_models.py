"""
Pydantic models for geometric data structures.

This module contains models for geometric calculations, coordinates, and spatial data.
"""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


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
