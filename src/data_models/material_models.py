"""
Pydantic models for material configuration and validation.

This module contains models for concrete, reinforcement, and material compatibility.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.common.materials import get_concrete_qualities, get_prestress_qualities, get_reinforcement_qualities


class MaterialConfig(BaseModel):
    """
    Configuration for structural materials.

    Validates material types exist in project database and are compatible.
    """

    concrete_type: str = Field(description="Concrete quality designation (e.g., C30/37)")
    reinforcement_type: str = Field(description="Reinforcement steel quality (e.g., B500B)")
    prestress_type: str | None = Field(None, description="Prestressing steel quality (optional)")

    @field_validator("concrete_type")
    @classmethod
    def validate_concrete_exists(cls, v: str) -> str:
        """Validate concrete type exists in project database."""
        valid_concretes = get_concrete_qualities()
        if v not in valid_concretes:
            available = ", ".join(valid_concretes[:5])
            raise ValueError(f"Concrete type '{v}' not found in database. Available: {available}...")
        return v

    @field_validator("reinforcement_type")
    @classmethod
    def validate_reinforcement_exists(cls, v: str) -> str:
        """Validate reinforcement type exists in project database."""
        valid_reinforcement = get_reinforcement_qualities()
        if v not in valid_reinforcement:
            available = ", ".join(valid_reinforcement[:5])
            raise ValueError(f"Reinforcement type '{v}' not found in database. Available: {available}...")
        return v

    @field_validator("prestress_type")
    @classmethod
    def validate_prestress_exists(cls, v: str | None) -> str | None:
        """Validate prestressing steel type exists in project database if provided."""
        if v is None:
            return v

        valid_prestress = get_prestress_qualities()
        if v not in valid_prestress:
            available = ", ".join(valid_prestress[:3])
            raise ValueError(f"Prestressing steel type '{v}' not found in database. Available: {available}...")
        return v

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    @classmethod
    def from_params_dict(cls, params: dict) -> "MaterialConfig":
        """
        Create MaterialConfig from VIKTOR params dictionary.

        Handles the nested structure and optional prestress material.
        """
        return cls(
            concrete_type=params["concrete_type"], reinforcement_type=params["reinforcement_type"], prestress_type=params.get("prestress_type")
        )
