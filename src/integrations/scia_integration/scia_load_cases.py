"""
SCIA load cases utility module.

This module provides functions for creating definitions of standard SCIA load cases.
These definitions are pure Python objects that can be used by the app layer to
construct the actual SCIA model.
"""

from typing import Any, Literal, TypeAlias

from .scia_definitions import LoadCaseDefinition

# Type alias for SCIA model object (kept for type hinting consistency in higher-level functions)
SciaModel: TypeAlias = Any
SciaLoadGroup: TypeAlias = Any
SciaLoadCase: TypeAlias = Any


def create_load_case(
    group_name: str,
    case_name: str,
    description: str,
    case_type: Literal["PERMANENT", "VARIABLE"],
    **kwargs: str,
) -> LoadCaseDefinition:
    """
    Create a definition for a SCIA load case.

    :param group_name: Name of the load group this case belongs to.
    :param case_name: Name for the load case.
    :param description: Description of the load case.
    :param case_type: "PERMANENT" or "VARIABLE".
    :param kwargs: Optional parameters:
        - permanent_type: "SELF_WEIGHT", "STANDARD", "PRIMARY_EFFECT"
        - variable_type: "STATIC", "PRIMARY_EFFECT"
        - specification: "STANDARD", "STATIC_WIND", "SNOW", "TEMPERATURE", "EARTHQUAKE"
        - duration: "INSTANTANEOUS", "SHORT", "MEDIUM", "LONG"
    :returns: A LoadCaseDefinition object.
    :rtype: LoadCaseDefinition
    """
    return LoadCaseDefinition(
        name=case_name,
        description=description,
        group_name=group_name,
        case_type=case_type,
        permanent_type=kwargs.get("permanent_type"),  # type: ignore[arg-type]
        variable_type=kwargs.get("variable_type"),  # type: ignore[arg-type]
        specification=kwargs.get("specification"),  # type: ignore[arg-type]
        duration=kwargs.get("duration"),  # type: ignore[arg-type]
    )


def create_self_weight_load_case(
    permanent_group_name: str,
) -> LoadCaseDefinition:
    """
    Create definition for self-weight load case BG01.

    :param permanent_group_name: Name of the permanent load group (e.g., "LG1").
    :returns: Definition for the self-weight load case.
    :rtype: LoadCaseDefinition
    """
    return create_load_case(
        group_name=permanent_group_name,
        case_name="BG01",
        description="Eigen gewicht",
        case_type="PERMANENT",
        permanent_type="SELF_WEIGHT",
    )


def create_wind_load_case(
    wind_group_name: str,
) -> LoadCaseDefinition:
    """
    Create definition for wind load case.

    :param wind_group_name: Name of the wind load group (e.g., "LG3").
    :returns: Definition for the wind load case.
    :rtype: LoadCaseDefinition
    """
    return create_load_case(
        group_name=wind_group_name,
        case_name="Q2_Wind",
        description="Wind Load",
        case_type="VARIABLE",
        variable_type="STATIC",
        specification="STATIC_WIND",
        duration="SHORT",
    )


def create_tandem_load_case(
    traffic_group_name: str,
    case_name: str,
    mode: str = "theoretical",
) -> LoadCaseDefinition:
    """
    Create definition for a tandem load case.

    :param traffic_group_name: Name of the traffic load group (e.g., "LG2").
    :param case_name: Name for the tandem load case (e.g., "TH6001").
    :param mode: Load case mode ("theoretical", "actual", "shiftable").
    :returns: Definition for the tandem load case.
    :rtype: LoadCaseDefinition
    """
    mode_descriptions = {
        "theoretical": "Tandem System - Theoretical Lane",
        "eurocode": "Load Model 1 - Tandem System",
        "shiftable": "Tandem System - Shiftable Position",
        "actual": "Tandem System - Actual Lane",
    }
    description = f"{mode_descriptions.get(mode, 'Tandem System')} {case_name}"

    return create_load_case(
        group_name=traffic_group_name,
        case_name=case_name,
        description=description,
        case_type="VARIABLE",
        variable_type="STATIC",
        specification="STANDARD",
        duration="SHORT",
    )


def create_basic_permanent_load_cases(
    permanent_group_name: str,
) -> dict[str, LoadCaseDefinition]:
    """
    Create definitions for basic permanent load cases.

    :param permanent_group_name: Name of the permanent load group.
    :returns: Dictionary with created permanent load case definitions.
    :rtype: dict[str, LoadCaseDefinition]
    """
    self_weight_case_def = create_self_weight_load_case(permanent_group_name)

    return {
        "self_weight": self_weight_case_def,
    }


# TODO: Additional load case creation functions to be added for complete bridge analysis
# - create_udl_load_case() - for uniformly distributed loads
# - create_pedestrian_load_case() - for pedestrian loads
# - create_temperature_load_case() - for temperature effects
# - create_multiple_tandem_load_cases() - for multiple tandem positions
# - create_special_vehicle_load_case() - for special vehicle loads
# - create_settlement_load_case() - for settlement effects
# - create_seismic_load_case() - for seismic loads
# - create_construction_stage_load_case() - for construction stages
