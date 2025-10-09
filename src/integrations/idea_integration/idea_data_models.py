"""
IDEA Integration Data Models.

This module provides dataclasses for passing data to IDEA integration functions,
replacing direct dependency on BridgeParametrization from the app layer.

This enables:
- Clear separation between app and src layers
- Type-safe data passing
- Easier testing without VIKTOR SDK
- Clear documentation of required data
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ReinforcementConfig:
    """
    Configuration for reinforcement parameters (processed from ReinforcementZoneConfig).

    This dataclass holds processed reinforcement parameters including distances,
    diameters, heights, and extra reinforcement configuration.
    """

    main_reinf_ctc_distances: dict[str, float]
    main_reinf_diameters: dict[str, float]
    reinf_heights: dict[str, float]
    extra_reinf_diameter: dict[str, float]
    extra_reinf_ctc_distances: dict[str, float]
    has_extra_reinforcement: bool
    rebar_config: dict[str, Any]


@dataclass
class ReinforcementZoneConfig:
    """
    Configuration for a single reinforcement zone.

    Contains all reinforcement parameters for one zone configuration that can be applied
    to multiple bridge zones.
    """

    zone_number: list[str]
    hoofdwapening_langs_boven_diameter: float  # mm
    hoofdwapening_dwars_boven_diameter: float  # mm
    hoofdwapening_langs_onder_diameter: float  # mm
    hoofdwapening_dwars_onder_diameter: float  # mm
    hoofdwapening_langs_boven_hart_op_hart: float  # mm
    hoofdwapening_dwars_boven_hart_op_hart: float  # mm
    hoofdwapening_langs_onder_hart_op_hart: float  # mm
    hoofdwapening_dwars_onder_hart_op_hart: float  # mm
    heeft_bijlegwapening: bool
    bijlegwapening_langs_boven_diameter: float = 0.0  # mm
    bijlegwapening_dwars_boven_diameter: float = 0.0  # mm
    bijlegwapening_langs_onder_diameter: float = 0.0  # mm
    bijlegwapening_dwars_onder_diameter: float = 0.0  # mm
    bijlegwapening_boven_hart_op_hart: float = 0.0  # mm


@dataclass
class BridgeGeometryConfig:
    """Configuration for bridge geometry and covers."""

    dekking_boven: float  # Top reinforcement cover in mm
    dekking_onder: float  # Bottom reinforcement cover in mm
    langswapening_buiten: bool  # Whether longitudinal reinforcement is placed as first layer


@dataclass
class BridgeIdeaInputData:
    """
    Complete input data for IDEA model creation.

    This dataclass contains all necessary data extracted from BridgeParametrization
    needed to create an IDEA RCS model, removing the direct dependency on VIKTOR SDK.

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

    entity_id: int
    bridge_name: str
    concrete_strength_class: str
    steel_quality: str
    reinforcement_zones: list[ReinforcementZoneConfig]
    bridge_segments: list[dict[str, Any]]
    geometry_config: BridgeGeometryConfig


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
    bridge_name = getattr(params.info, "bridge_objectnumm", None) or "Unnamed Bridge"

    # Extract material properties
    concrete_strength_value = getattr(params, "concrete_strength_class", "")
    concrete_strength_class = concrete_strength_value.strip() if concrete_strength_value else "C30/37"
    if not concrete_strength_class:
        concrete_strength_class = "C30/37"

    steel_quality = getattr(params.input.geometrie_wapening, "staalsoort", None) or "B500B"

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
