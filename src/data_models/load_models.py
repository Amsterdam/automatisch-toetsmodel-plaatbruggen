"""
Pydantic models for load zone and loading data structures.

This module contains models for load zones, traffic loads, and related validation.
"""

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# Import constants from src layer for single source of truth
from src.common.constants.parametrization import LOAD_ZONE_TYPES, PAVEMENT_MATERIAL_OPTIONS

# True single source of truth: Use Pydantic's field validation with constants
# This approach eliminates the need for manual Literal type updates


class LoadZoneData(BaseModel):
    """
    Represents a single load zone with pavement and width data.

    Validates zone types, materials, and geometric constraints.
    """

    zone_type: str = Field(description=f"Type of load zone ({', '.join(LOAD_ZONE_TYPES)})")
    pavement_thickness: float = Field(gt=0, le=0.5, description="Pavement thickness in meters (0-0.5m)")
    pavement_material: str = Field(description=f"Pavement material type ({', '.join(PAVEMENT_MATERIAL_OPTIONS)})")

    # Width fields for D-points 1-15 (all optional)
    d1_width: float | None = Field(default=None, ge=0, le=50, description="Width at D1 point in meters")
    d2_width: float | None = Field(default=None, ge=0, le=50, description="Width at D2 point in meters")
    d3_width: float | None = Field(default=None, ge=0, le=50, description="Width at D3 point in meters")
    d4_width: float | None = Field(default=None, ge=0, le=50, description="Width at D4 point in meters")
    d5_width: float | None = Field(default=None, ge=0, le=50, description="Width at D5 point in meters")
    d6_width: float | None = Field(default=None, ge=0, le=50, description="Width at D6 point in meters")
    d7_width: float | None = Field(default=None, ge=0, le=50, description="Width at D7 point in meters")
    d8_width: float | None = Field(default=None, ge=0, le=50, description="Width at D8 point in meters")
    d9_width: float | None = Field(default=None, ge=0, le=50, description="Width at D9 point in meters")
    d10_width: float | None = Field(default=None, ge=0, le=50, description="Width at D10 point in meters")
    d11_width: float | None = Field(default=None, ge=0, le=50, description="Width at D11 point in meters")
    d12_width: float | None = Field(default=None, ge=0, le=50, description="Width at D12 point in meters")
    d13_width: float | None = Field(default=None, ge=0, le=50, description="Width at D13 point in meters")
    d14_width: float | None = Field(default=None, ge=0, le=50, description="Width at D14 point in meters")
    d15_width: float | None = Field(default=None, ge=0, le=50, description="Width at D15 point in meters")

    # Calculated fields (populated by system)
    zone_widths_per_d: list[float] = Field(default_factory=list, description="Calculated widths for each D-point")
    y_coords_top_current_zone: list[float] = Field(default_factory=list, description="Y-coordinates for zone top boundary")

    @field_validator("zone_type")
    @classmethod
    def validate_zone_type_against_constants(cls, v: str) -> str:
        """Validate zone type against constants - true single source of truth."""
        if v not in LOAD_ZONE_TYPES:
            valid_options = ", ".join(LOAD_ZONE_TYPES)
            raise ValueError(f"Invalid zone_type '{v}'. Must be one of: {valid_options}")
        return v

    @field_validator("pavement_material")
    @classmethod
    def validate_pavement_material_against_constants(cls, v: str) -> str:
        """Validate pavement material against constants - true single source of truth."""
        if v not in PAVEMENT_MATERIAL_OPTIONS:
            valid_options = ", ".join(PAVEMENT_MATERIAL_OPTIONS)
            raise ValueError(f"Invalid pavement_material '{v}'. Must be one of: {valid_options}")
        return v

    @field_validator("pavement_thickness")
    @classmethod
    def validate_pavement_thickness_by_type(cls, v: float, info: ValidationInfo) -> float:
        """Validate pavement thickness based on zone type."""
        if info.data and "zone_type" in info.data:
            zone_type = info.data["zone_type"]
            if zone_type == "Auto" and v < 0.05:
                raise ValueError(f"Auto zones require minimum 5cm pavement thickness, got {v * 100:.1f}cm")
            if zone_type in ["Voetgangers", "Fietsers"] and v < 0.02:
                raise ValueError(f"{zone_type} zones require minimum 2cm pavement thickness, got {v * 100:.1f}cm")
        return v

    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True)
