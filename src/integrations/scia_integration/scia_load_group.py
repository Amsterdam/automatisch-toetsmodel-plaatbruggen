"""
SCIA load group utility module.

This module provides utilities for creating and managing load groups in SCIA Engineer.
Direct functions create specific load groups with predefined parameters.

Currently contains placeholder implementations for basic bridge analysis.
"""

from typing import Any

# Global VIKTOR imports with error handling for CI/testing environments
try:
    from viktor.external import scia

    VIKTOR_AVAILABLE = True
except ImportError:
    # Mock scia module for environments without VIKTOR SDK
    scia = None  # type: ignore[misc,assignment]
    VIKTOR_AVAILABLE = False

# Type aliases for SCIA objects
SciaModel = Any
SciaLoadGroup = Any


def create_permanent_load_group(model: SciaModel) -> SciaLoadGroup:
    """
    Create permanent load group LG1 matching SCIA interface.

    Creates load group "LG1" for permanent loads (self-weight, superimposed dead loads)
    using direct SCIA API to match SCIA Engineer interface exactly.

    :param model: SCIA model instance
    :returns: Created SCIA permanent load group LG1
    :rtype: SciaLoadGroup
    :raises ImportError: When VIKTOR SCIA module is not available
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    return model.create_load_group(
        "LG1",
        scia.LoadGroup.LoadOption.PERMANENT,
        scia.LoadGroup.RelationOption.STANDARD,
        scia.LoadGroup.LoadTypeOption.CONSTRUCTION_LOADS,
    )


def create_traffic_load_group(model: SciaModel) -> SciaLoadGroup:
    """
    Create traffic load group LG2 matching SCIA interface.

    Creates load group "LG2" for traffic loads (tandem, UDL, pedestrian)
    using direct SCIA API to match SCIA Engineer interface exactly.

    :param model: SCIA model instance
    :returns: Created SCIA traffic load group LG2
    :rtype: SciaLoadGroup
    :raises ImportError: When VIKTOR SCIA module is not available
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    return model.create_load_group(
        "LG2",
        scia.LoadGroup.LoadOption.VARIABLE,
        scia.LoadGroup.RelationOption.STANDARD,
        scia.LoadGroup.LoadTypeOption.CAT_A,
    )


def create_wind_load_group(model: SciaModel) -> SciaLoadGroup:
    """
    Create wind load group LG3 matching SCIA interface.

    Creates load group "LG3" for wind loads and other environmental loads
    using direct SCIA API to match SCIA Engineer interface exactly.

    :param model: SCIA model instance
    :returns: Created SCIA wind load group LG3
    :rtype: SciaLoadGroup
    :raises ImportError: When VIKTOR SCIA module is not available
    """
    if not VIKTOR_AVAILABLE or scia is None:
        raise ImportError("VIKTOR SCIA module not available. This function requires VIKTOR SDK.")

    return model.create_load_group(
        "LG3",
        scia.LoadGroup.LoadOption.VARIABLE,
        scia.LoadGroup.RelationOption.STANDARD,
        scia.LoadGroup.LoadTypeOption.CAT_A,
    )


def create_basic_load_groups(model: SciaModel) -> dict[str, SciaLoadGroup]:
    """
    Create all basic load groups for bridge analysis.

    Creates permanent, traffic, and wind load groups that are typically
    needed for bridge structural analysis.

    PLACEHOLDER: Currently creates basic groups. Will be expanded to include
    additional load groups for complete bridge analysis (seismic, construction, etc.).

    :param model: SCIA model instance
    :returns: Dictionary with created load groups
    :rtype: dict[str, SciaLoadGroup]
    """
    permanent_group = create_permanent_load_group(model)
    traffic_group = create_traffic_load_group(model)
    wind_group = create_wind_load_group(model)

    return {
        "permanent": permanent_group,
        "traffic": traffic_group,
        "wind": wind_group,
    }


# TODO: Additional load group creation functions to be added for complete bridge analysis
# - create_seismic_load_group() - for seismic loads
# - create_construction_load_group() - for construction stage loads
# - create_temperature_load_group() - for temperature effects
# - create_settlement_load_group() - for settlement effects
# - create_prestress_load_group() - for prestressing loads
# - create_special_vehicle_load_group() - for special vehicle loads
