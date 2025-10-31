"""
Pydantic models for IDEA StatiCa integration data structures.

This module contains models for reinforcement configuration and other
IDEA-related data validation.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.common.constants.technical import STANDARD_REBAR_DIAMETERS


class ReinforcementConfigData(BaseModel):
    """
    Configuration for reinforcement parameters in IDEA StatiCa analysis.

    Validates reinforcement diameters, distances, heights, and configuration
    according to concrete engineering standards.
    """

    main_reinf_ctc_distances: dict[str, float] = Field(description="Center-to-center distances for main reinforcement")
    main_reinf_diameters: dict[str, float] = Field(description="Diameters for main reinforcement bars")
    reinf_heights: dict[str, float] = Field(description="Heights/positions of reinforcement layers")
    extra_reinf_diameter: dict[str, float] = Field(description="Diameters for extra reinforcement bars")
    extra_reinf_ctc_distances: dict[str, float] = Field(description="Center-to-center distances for extra reinforcement")
    has_extra_reinforcement: bool = Field(description="Whether extra reinforcement is present")
    rebar_config: dict[str, Any] = Field(description="Additional rebar configuration parameters")

    @field_validator("main_reinf_diameters")
    @classmethod
    def validate_main_reinforcement_diameters(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate main reinforcement diameters against standard sizes."""
        for zone, diameter in v.items():
            if diameter not in STANDARD_REBAR_DIAMETERS:
                raise ValueError(
                    f"Reinforcement diameter {diameter}mm in zone '{zone}' is not standard. Standard sizes: {sorted(STANDARD_REBAR_DIAMETERS)}mm"
                )
            if diameter < 6:
                raise ValueError(f"Reinforcement diameter {diameter}mm in zone '{zone}' is too small (minimum 6mm)")
            if diameter > 40:
                raise ValueError(f"Reinforcement diameter {diameter}mm in zone '{zone}' is too large (maximum 40mm)")

        return v

    @field_validator("extra_reinf_diameter")
    @classmethod
    def validate_extra_reinforcement_diameters(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate extra reinforcement diameters - allows 0mm when extra reinforcement is not used."""
        for zone, diameter in v.items():
            # Allow 0mm diameter when has_extra_reinforcement=False
            if diameter == 0:
                continue

            if diameter not in STANDARD_REBAR_DIAMETERS:
                raise ValueError(
                    f"Reinforcement diameter {diameter}mm in zone '{zone}' is not standard. Standard sizes: {sorted(STANDARD_REBAR_DIAMETERS)}mm"
                )
            if diameter < 6:
                raise ValueError(f"Reinforcement diameter {diameter}mm in zone '{zone}' is too small (minimum 6mm)")
            if diameter > 40:
                raise ValueError(f"Reinforcement diameter {diameter}mm in zone '{zone}' is too large (maximum 40mm)")

        return v

    @field_validator("main_reinf_ctc_distances")
    @classmethod
    def validate_main_ctc_distances(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate main reinforcement center-to-center distances."""
        for zone, distance in v.items():
            if distance < 50:  # mm
                raise ValueError(f"Center-to-center distance {distance}mm in zone '{zone}' is too small (minimum 50mm)")
            if distance > 500:  # mm
                raise ValueError(f"Center-to-center distance {distance}mm in zone '{zone}' is too large (maximum 500mm)")

        return v

    @field_validator("extra_reinf_ctc_distances")
    @classmethod
    def validate_extra_ctc_distances(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate extra reinforcement center-to-center distances - allows 0mm when extra reinforcement is not used."""
        for zone, distance in v.items():
            # Allow 0mm distance when has_extra_reinforcement=False
            if distance == 0:
                continue

            if distance < 50:  # mm
                raise ValueError(f"Center-to-center distance {distance}mm in zone '{zone}' is too small (minimum 50mm)")
            if distance > 500:  # mm
                raise ValueError(f"Center-to-center distance {distance}mm in zone '{zone}' is too large (maximum 500mm)")

        return v

    @field_validator("reinf_heights")
    @classmethod
    def validate_reinforcement_heights(cls, v: dict[str, float]) -> dict[str, float]:
        """
        Validate reinforcement heights/positions.

        Allows negative values as they can represent positions below a reference point
        in certain coordinate systems.
        """
        for zone, height in v.items():
            # Allow negative heights (positions below reference point)
            if height < -2000:  # mm
                raise ValueError(f"Reinforcement height {height}mm in zone '{zone}' is unrealistically low (minimum -2000mm)")
            if height > 2000:  # mm
                raise ValueError(f"Reinforcement height {height}mm in zone '{zone}' is unrealistically high (maximum 2000mm)")

        return v

    @model_validator(mode="after")
    def validate_extra_reinforcement_consistency(self) -> "ReinforcementConfigData":
        """Validate extra reinforcement data consistency."""
        if self.has_extra_reinforcement:
            # If extra reinforcement is enabled, data should not be empty
            if not self.extra_reinf_diameter:
                raise ValueError("Extra reinforcement is enabled but extra_reinf_diameter is empty")
            if not self.extra_reinf_ctc_distances:
                raise ValueError("Extra reinforcement is enabled but extra_reinf_ctc_distances is empty")
        return self

    @field_validator("rebar_config")
    @classmethod
    def validate_rebar_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate rebar configuration parameters."""
        # For IDEA integration, rebar_config contains zone-specific data (e.g., heeft_bijlegwapening, zone_number)
        # This validator allows flexible dict structure for compatibility with different config sources
        # but validates specific fields when present for legacy test compatibility
        if not isinstance(v, dict):
            raise TypeError("rebar_config must be a dictionary")

        # Validate grade if present (optional validation for legacy test compatibility)
        if "grade" in v:
            grade = v["grade"]
            if isinstance(grade, str) and grade not in {"B500A", "B500B", "B500C"}:
                raise ValueError(f"Invalid reinforcement grade '{grade}'. Must be B500A, B500B, or B500C")

        # Note: We no longer enforce required keys (material, grade, cover) as the field is flexible
        # to support IDEA integration use cases where different keys may be present

        return v

    model_config = ConfigDict(validate_assignment=True)
