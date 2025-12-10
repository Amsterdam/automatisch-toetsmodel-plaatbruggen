"""
Pydantic models for load combination configuration and validation.

This module contains models for load combination parameters, design codes,
and consequence classes used in structural analysis.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# Import constants from src layer for single source of truth
from src.common.constants.parametrization import CC_CLASS_OPTIONS, DESIGN_CODE_OPTIONS

# True single source of truth: Use Pydantic's field validation with constants
# This approach eliminates the need for manual Literal type updates
# Pydantic will validate against the actual constants at runtime


class LoadCombinationConfig(BaseModel):
    """
    Configuration for load combination generation.

    Validates consequence class, design code, and construction year parameters
    according to NEN 8700 standards.
    """

    cc_class: str = Field(description=f"Consequence class according to NEN 8700 ({', '.join(CC_CLASS_OPTIONS)})")
    design_code: str = Field(description=f"Design code and safety level for load factor selection ({', '.join(DESIGN_CODE_OPTIONS)})")
    construction_year: int = Field(ge=1850, le=2100, description="Year of construction for load factor selection")

    @field_validator("construction_year")
    @classmethod
    def validate_construction_year_realistic(cls, v: int, _info: ValidationInfo) -> int:
        """Validate that construction year is realistic for bridge structures."""
        current_year = datetime.now(UTC).year

        if v > current_year + 10:
            raise ValueError(f"Construction year {v} is too far in the future (max: {current_year + 10})")
        if v < 1850:
            raise ValueError(f"Construction year {v} is too old for modern standards (min: 1850)")

        # Warn about very old bridges that may need special consideration
        if v < 1950:
            # Note: This is just validation, not a warning system
            # In a real application, you might log a warning here
            pass

        return v

    @field_validator("cc_class", mode="before")
    @classmethod
    def validate_cc_class_format(cls, v: str) -> str:
        """Validate CC class against constants - true single source of truth."""
        # Strip whitespace first
        if isinstance(v, str):
            v = v.strip()

        # Validate against the actual constants
        if v not in CC_CLASS_OPTIONS:
            valid_options = ", ".join(CC_CLASS_OPTIONS)
            raise ValueError(f"Invalid cc_class '{v}'. Must be one of: {valid_options}")

        return v

    @field_validator("design_code", mode="before")
    @classmethod
    def validate_design_code_format(cls, v: str) -> str:
        """Validate design code against constants - true single source of truth."""
        # Strip whitespace first
        if isinstance(v, str):
            v = v.strip()

        # Validate against the actual constants
        if v not in DESIGN_CODE_OPTIONS:
            valid_options = ", ".join(DESIGN_CODE_OPTIONS)
            raise ValueError(f"Invalid design_code '{v}'. Must be one of: {valid_options}")

        return v

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,  # Automatically strip whitespace from string inputs
    )

    @classmethod
    def from_params_dict(cls, params: dict) -> "LoadCombinationConfig":
        """
        Create LoadCombinationConfig from VIKTOR params dictionary.

        Handles the nested structure: params["info"]["construction_year"]

        Args:
            params: Dictionary containing cc_class, design_code, and info.construction_year

        Returns:
            LoadCombinationConfig instance with validated parameters

        Raises:
            KeyError: If required parameters are missing
            ValidationError: If parameter values are invalid

        """
        # Check for required top-level parameters
        if "cc_class" not in params:
            raise KeyError("Missing required parameter: cc_class")
        if "design_code" not in params:
            raise KeyError("Missing required parameter: design_code")

        # Check for nested construction_year parameter
        if "info" not in params:
            raise KeyError("Missing required parameter: info")
        if "construction_year" not in params["info"]:
            raise KeyError("Missing required parameter: info.construction_year")

        return cls(cc_class=params["cc_class"], design_code=params["design_code"], construction_year=int(params["info"]["construction_year"]))

    def to_tuple(self) -> tuple[str, str, str]:
        """
        Convert to tuple format for backward compatibility.

        Returns:
            Tuple of (cc_class, design_code, construction_year_str)

        """
        return self.cc_class, self.design_code, str(self.construction_year)
