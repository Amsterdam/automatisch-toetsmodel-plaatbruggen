"""
Pydantic models for bridge-related data structures.

This module contains models for bridge geometry, segments, and structural elements.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BridgeSegmentDimensions(BaseModel):
    """
    Represents the dimensions of a single bridge segment cross-section.

    Uses Pydantic for automatic validation and clear error messages.
    All dimensions must be positive values representing physical measurements in meters.
    """

    bz1: float = Field(gt=0, description="Bridge zone 1 width in meters")
    bz2: float = Field(gt=0, description="Bridge zone 2 width in meters")
    bz3: float = Field(gt=0, description="Bridge zone 3 width in meters")
    segment_length: float = Field(ge=0, description="Length to previous segment in meters (0 for first segment)")

    @field_validator("bz1", "bz2", "bz3")
    @classmethod
    def validate_zone_widths(cls, v: float) -> float:
        """Validate that bridge zone widths are reasonable (between 0.1m and 50m)."""
        if not 0.1 <= v <= 50.0:
            raise ValueError(f"Bridge zone width {v}m is unrealistic. Must be between 0.1m and 50m.")
        return v

    @field_validator("segment_length")
    @classmethod
    def validate_segment_length(cls, v: float) -> float:
        """Validate that segment length is reasonable (max 200m for typical bridges)."""
        if v > 200.0:
            raise ValueError(f"Segment length {v}m is unrealistic. Must be ≤ 200m.")
        return v

    model_config = ConfigDict(
        # Allow validation on assignment (validates when fields are changed)
        validate_assignment=True,
        # Use enum values instead of enum objects in serialization
        use_enum_values=True,
    )
