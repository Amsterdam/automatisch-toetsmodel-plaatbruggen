"""
IDEA Integration Data Models.

This module provides Pydantic models for passing data to IDEA integration functions,
replacing direct dependency on BridgeParametrization from the app layer.

This enables:
- Clear separation between app and src layers
- Type-safe data passing
- Easier testing without VIKTOR SDK
- Clear documentation of required data
- Runtime validation with clear error messages
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from src.common.materials import get_concrete_qualities, get_reinforcement_qualities
from src.integrations.idea_integration.constants.materials import (
    DEFAULT_BRIDGE_NAME,
    DEFAULT_CONCRETE_STRENGTH_CLASS,
    DEFAULT_STEEL_QUALITY,
)

# ReinforcementConfig has been replaced with ReinforcementConfigData from src.data_models.idea_models
# This allows using the existing Pydantic model with validation instead of maintaining a separate dataclass


class ReinforcementZoneConfig(BaseModel):
    """
    Configuration for a single reinforcement zone.

    Contains all reinforcement parameters for one zone configuration that can be applied
    to multiple bridge zones.

    Validates diameters, spacing, and zone numbers according to concrete engineering standards.
    """

    zone_number: list[str] = Field(min_length=1, description="List of zone numbers this configuration applies to")
    hoofdwapening_langs_boven_diameter: float = Field(ge=0, le=40, description="Main reinforcement longitudinal top diameter in mm")
    hoofdwapening_dwars_boven_diameter: float = Field(ge=0, le=40, description="Main reinforcement transverse top diameter in mm")
    hoofdwapening_langs_onder_diameter: float = Field(ge=0, le=40, description="Main reinforcement longitudinal bottom diameter in mm")
    hoofdwapening_dwars_onder_diameter: float = Field(ge=0, le=40, description="Main reinforcement transverse bottom diameter in mm")
    hoofdwapening_langs_boven_hart_op_hart: float = Field(
        ge=0, le=500, description="Main reinforcement longitudinal top center-to-center spacing in mm"
    )
    hoofdwapening_dwars_boven_hart_op_hart: float = Field(
        ge=0, le=500, description="Main reinforcement transverse top center-to-center spacing in mm"
    )
    hoofdwapening_langs_onder_hart_op_hart: float = Field(
        ge=0, le=500, description="Main reinforcement longitudinal bottom center-to-center spacing in mm"
    )
    hoofdwapening_dwars_onder_hart_op_hart: float = Field(
        ge=0, le=500, description="Main reinforcement transverse bottom center-to-center spacing in mm"
    )
    heeft_bijlegwapening: bool = Field(description="Whether additional reinforcement is present")
    bijlegwapening_langs_boven_diameter: float = Field(
        default=0.0, ge=0, le=40, description="Additional reinforcement longitudinal top diameter in mm"
    )
    bijlegwapening_dwars_boven_diameter: float = Field(default=0.0, ge=0, le=40, description="Additional reinforcement transverse top diameter in mm")
    bijlegwapening_langs_onder_diameter: float = Field(
        default=0.0, ge=0, le=40, description="Additional reinforcement longitudinal bottom diameter in mm"
    )
    bijlegwapening_dwars_onder_diameter: float = Field(
        default=0.0, ge=0, le=40, description="Additional reinforcement transverse bottom diameter in mm"
    )
    bijlegwapening_boven_hart_op_hart: float = Field(
        default=0.0, ge=0, le=500, description="Additional reinforcement top center-to-center spacing in mm"
    )

    model_config = ConfigDict(validate_assignment=True)


class BridgeGeometryConfig(BaseModel):
    """
    Configuration for bridge geometry and covers.

    Validates reinforcement cover values and placement configuration.
    """

    dekking_boven: float = Field(ge=0, le=300, description="Top reinforcement cover in mm")
    dekking_onder: float = Field(ge=0, le=300, description="Bottom reinforcement cover in mm")
    langswapening_buiten: bool = Field(description="Whether longitudinal reinforcement is placed as first layer")

    model_config = ConfigDict(validate_assignment=True)


class BridgeIdeaInputData(BaseModel):
    """
    Complete input data for IDEA model creation.

    This Pydantic model contains all necessary data extracted from BridgeParametrization
    needed to create an IDEA RCS model, removing the direct dependency on VIKTOR SDK.

    Validates materials against project database and ensures all required fields are present.

    :param entity_id: VIKTOR entity ID for caching
    :type entity_id: int
    :param bridge_name: Bridge name or object number for project identification
    :type bridge_name: str
    :param concrete_strength_class: Concrete strength class (e.g., "C30/37")
    :type concrete_strength_class: str
    :param steel_quality: Reinforcement steel quality (e.g., "B500B")
    :type steel_quality: str
    :param reinforcement_zones: List of reinforcement zone configurations
    :type reinforcement_zones: list[ReinforcementZoneConfig]
    :param bridge_segments: List of bridge segment dictionaries from parametrization
    :type bridge_segments: list[dict[str, Any]]
    :param geometry_config: Bridge geometry configuration (covers)
    :type geometry_config: BridgeGeometryConfig
    """

    entity_id: int = Field(ge=0, description="VIKTOR entity ID for caching")
    bridge_name: str = Field(min_length=1, default=DEFAULT_BRIDGE_NAME, description="Bridge name or object number for project identification")
    concrete_strength_class: str = Field(default=DEFAULT_CONCRETE_STRENGTH_CLASS, description="Concrete strength class (e.g., 'C30/37')")
    steel_quality: str = Field(default=DEFAULT_STEEL_QUALITY, description="Reinforcement steel quality (e.g., 'B500B')")
    reinforcement_zones: list[ReinforcementZoneConfig] = Field(
        description="List of reinforcement zone configurations (may be empty for initialization)"
    )
    bridge_segments: list[dict[str, Any]] = Field(
        description="List of bridge segment dictionaries from parametrization (may be empty for initialization)"
    )
    geometry_config: BridgeGeometryConfig = Field(description="Bridge geometry configuration (covers)")

    @field_validator("concrete_strength_class")
    @classmethod
    def validate_concrete_strength_class(cls, v: str, _info: ValidationInfo) -> str:
        """Validate concrete strength class against material database."""
        if isinstance(v, str):
            v = v.strip()
        valid_concretes = get_concrete_qualities()
        if v not in valid_concretes:
            available = ", ".join(valid_concretes[:5])
            raise ValueError(f"Concrete strength class '{v}' not found in database. Available: {available}...")
        return v

    @field_validator("steel_quality")
    @classmethod
    def validate_steel_quality(cls, v: str, _info: ValidationInfo) -> str:
        """Validate steel quality against material database."""
        if isinstance(v, str):
            v = v.strip()
        valid_reinforcement = get_reinforcement_qualities()
        if v not in valid_reinforcement:
            available = ", ".join(valid_reinforcement[:5])
            raise ValueError(f"Steel quality '{v}' not found in database. Available: {available}...")
        return v

    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True)


def extract_bridge_idea_input_data(params: Any) -> BridgeIdeaInputData:  # noqa: ANN401
    """
    Extract IDEA input data from BridgeParametrization.

    This function serves as the boundary between app and src layers,
    extracting all necessary data from the VIKTOR parametrization object.

    :param params: BridgeParametrization object from VIKTOR
    :type params: BridgeParametrization
    :returns: Extracted input data for IDEA integration
    :rtype: BridgeIdeaInputData
    :raises AttributeError: If required parameters are missing
    """
    # Extract bridge identification
    bridge_name = getattr(params.info, "bridge_objectnumm", None) or DEFAULT_BRIDGE_NAME

    # Extract material properties
    concrete_strength_value = getattr(params, "concrete_strength_class", "")
    concrete_strength_class = concrete_strength_value.strip() if concrete_strength_value else DEFAULT_CONCRETE_STRENGTH_CLASS
    if not concrete_strength_class:
        concrete_strength_class = DEFAULT_CONCRETE_STRENGTH_CLASS

    steel_quality = getattr(params.input.geometrie_wapening, "staalsoort", None) or DEFAULT_STEEL_QUALITY

    # Extract geometry configuration
    geometry_config = BridgeGeometryConfig(
        dekking_boven=params.input.geometrie_wapening.dekking_boven,
        dekking_onder=params.input.geometrie_wapening.dekking_onder,
        langswapening_buiten=params.input.geometrie_wapening.langswapening_buiten,
    )

    # Extract reinforcement zones
    reinforcement_zones = []
    for rebar_config in params.reinforcement_zones_array:
        zone_config = ReinforcementZoneConfig(
            zone_number=getattr(rebar_config, "zone_number", []),
            hoofdwapening_langs_boven_diameter=getattr(rebar_config, "hoofdwapening_langs_boven_diameter", 0.0),
            hoofdwapening_dwars_boven_diameter=getattr(rebar_config, "hoofdwapening_dwars_boven_diameter", 0.0),
            hoofdwapening_langs_onder_diameter=getattr(rebar_config, "hoofdwapening_langs_onder_diameter", 0.0),
            hoofdwapening_dwars_onder_diameter=getattr(rebar_config, "hoofdwapening_dwars_onder_diameter", 0.0),
            hoofdwapening_langs_boven_hart_op_hart=getattr(rebar_config, "hoofdwapening_langs_boven_hart_op_hart", 0.0),
            hoofdwapening_dwars_boven_hart_op_hart=getattr(rebar_config, "hoofdwapening_dwars_boven_hart_op_hart", 0.0),
            hoofdwapening_langs_onder_hart_op_hart=getattr(rebar_config, "hoofdwapening_langs_onder_hart_op_hart", 0.0),
            hoofdwapening_dwars_onder_hart_op_hart=getattr(rebar_config, "hoofdwapening_dwars_onder_hart_op_hart", 0.0),
            heeft_bijlegwapening=getattr(rebar_config, "heeft_bijlegwapening", False),
            bijlegwapening_langs_boven_diameter=getattr(rebar_config, "bijlegwapening_langs_boven_diameter", 0.0),
            bijlegwapening_dwars_boven_diameter=getattr(rebar_config, "bijlegwapening_dwars_boven_diameter", 0.0),
            bijlegwapening_langs_onder_diameter=getattr(rebar_config, "bijlegwapening_langs_onder_diameter", 0.0),
            bijlegwapening_dwars_onder_diameter=getattr(rebar_config, "bijlegwapening_dwars_onder_diameter", 0.0),
            bijlegwapening_boven_hart_op_hart=getattr(rebar_config, "bijlegwapening_boven_hart_op_hart", 0.0),
        )
        reinforcement_zones.append(zone_config)

    # Extract bridge segments
    bridge_segments = list(params.bridge_segments_array)

    return BridgeIdeaInputData(
        entity_id=0,  # Will be set by caller
        bridge_name=bridge_name,
        concrete_strength_class=concrete_strength_class,
        steel_quality=steel_quality,
        reinforcement_zones=reinforcement_zones,
        bridge_segments=bridge_segments,
        geometry_config=geometry_config,
    )
