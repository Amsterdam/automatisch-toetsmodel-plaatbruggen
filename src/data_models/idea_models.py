"""
Pydantic models for IDEA StatiCa integration data structures.

This module contains models for reinforcement configuration and other
IDEA-related data validation.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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

    @field_validator("main_reinf_diameters", "extra_reinf_diameter")
    @classmethod
    def validate_reinforcement_diameters(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate reinforcement diameters against standard sizes."""
        standard_diameters = {6, 8, 10, 12, 14, 16, 20, 25, 32, 40}  # mm

        for zone, diameter in v.items():
            if diameter not in standard_diameters:
                raise ValueError(
                    f"Reinforcement diameter {diameter}mm in zone '{zone}' is not standard. Standard sizes: {sorted(standard_diameters)}mm"
                )
            if diameter < 6:
                raise ValueError(f"Reinforcement diameter {diameter}mm in zone '{zone}' is too small (minimum 6mm)")
            if diameter > 40:
                raise ValueError(f"Reinforcement diameter {diameter}mm in zone '{zone}' is too large (maximum 40mm)")

        return v

    @field_validator("main_reinf_ctc_distances", "extra_reinf_ctc_distances")
    @classmethod
    def validate_ctc_distances(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate center-to-center distances."""
        for zone, distance in v.items():
            if distance < 50:  # mm
                raise ValueError(f"Center-to-center distance {distance}mm in zone '{zone}' is too small (minimum 50mm)")
            if distance > 500:  # mm
                raise ValueError(f"Center-to-center distance {distance}mm in zone '{zone}' is too large (maximum 500mm)")

        return v

    @field_validator("reinf_heights")
    @classmethod
    def validate_reinforcement_heights(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate reinforcement heights/positions."""
        for zone, height in v.items():
            if height < 0:
                raise ValueError(f"Reinforcement height {height}mm in zone '{zone}' cannot be negative")
            if height > 2000:  # mm
                raise ValueError(f"Reinforcement height {height}mm in zone '{zone}' is unrealistic (maximum 2000mm)")

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
        # Check for required keys if present
        if v:
            required_keys = {"material", "grade", "cover"}
            missing_keys = required_keys - set(v.keys())
            if missing_keys:
                raise ValueError(f"Rebar config missing required keys: {missing_keys}")

            # Validate material grade if present
            if "grade" in v:
                grade = v["grade"]
                if isinstance(grade, str) and grade not in {"B500A", "B500B", "B500C"}:
                    raise ValueError(f"Invalid reinforcement grade '{grade}'. Must be B500A, B500B, or B500C")

        return v

    model_config = ConfigDict(validate_assignment=True)
