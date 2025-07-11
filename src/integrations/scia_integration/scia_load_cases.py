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


def create_self_weight_load_case() -> LoadCaseDefinition:
    """
    Create definition for self-weight load case BG1001.

    :returns: Definition for the self-weight load case.
    :rtype: LoadCaseDefinition
    """
    return create_load_case(
        group_name="LG1000",
        case_name="BG1001",
        description="Eigen gewicht",
        case_type="PERMANENT",
        permanent_type="SELF_WEIGHT",
    )


def create_resting_load_cases() -> list[LoadCaseDefinition]:
    """
    Create definitions for resting permanent load cases BG2001 to BG2005.

    :returns: List of resting load case definitions.
    :rtype: list[LoadCaseDefinition]
    """
    data = [
        ("BG2001", "Rustende belasting - Asfalt"),
        ("BG2002", "Rustende belasting - Uitvulling"),
        ("BG2003", "Rustende belasting - Ophogingen, schampkanten, trottoir"),
        ("BG2004", "Rustende belasting - Leuning"),
        ("BG2005", "Rustende belasting - Lichtmast"),
    ]
    return [
        create_load_case(
            group_name="LG2000",
            case_name=name,
            description=desc,
            case_type="PERMANENT",
            permanent_type="STANDARD",
        )
        for name, desc in data
    ]


def create_temperature_load_cases() -> list[LoadCaseDefinition]:
    """
    Create definitions for temperature load cases BG3001 to BG3004.

    :returns: List of temperature load case definitions.
    :rtype: list[LoadCaseDefinition]
    """
    data = [
        ("BG3001", "Temperatuur, dek - Temp combi 1"),
        ("BG3002", "Temperatuur, dek - Temp combi 2"),
        ("BG3003", "Temperatuur, dek - Temp combi 3"),
        ("BG3004", "Temperatuur, dek - Temp combi 4"),
    ]
    return [
        create_load_case(
            group_name="LG3000",
            case_name=name,
            description=desc,
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="TEMPERATURE",
            duration="LONG",
        )
        for name, desc in data
    ]


def create_udl_traffic_load_cases() -> list[LoadCaseDefinition]:
    """
    Create definitions for UDL traffic load cases BG4001 to BG4004.

    :returns: List of UDL traffic load case definitions.
    :rtype: list[LoadCaseDefinition]
    """
    data = [
        ("BG4001", "Verkeer, dek - LM1 UDL RS 1"),
        ("BG4002", "Verkeer, dek - LM1 UDL RS 2"),
        ("BG4003", "Verkeer, dek - LM1 UDL RS 3"),
        ("BG4004", "Verkeer, dek - LM1 UDL rest"),
    ]
    return [
        create_load_case(
            group_name="LG4000",
            case_name=name,
            description=desc,
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        for name, desc in data
    ]


def create_pedestrian_load_case() -> LoadCaseDefinition:
    """
    Create definition for pedestrian load case BG5001.

    :returns: Pedestrian load case definition.
    :rtype: LoadCaseDefinition
    """
    return create_load_case(
        group_name="LG5000",
        case_name="BG5001",
        description="Verkeer, mensenmenigte - LM4",
        case_type="VARIABLE",
        variable_type="STATIC",
        specification="STANDARD",
        duration="SHORT",
    )


def create_service_vehicle_load_cases() -> list[LoadCaseDefinition]:
    """
    Create definitions for service vehicle load cases BG6001 to BG6003.

    :returns: List of service vehicle load case definitions.
    :rtype: list[LoadCaseDefinition]
    """
    data = [
        ("BG6001", "Verkeer, dienstvoertuig - RS 1"),
        ("BG6002", "Verkeer, dienstvoertuig - RS 2"),
        ("BG6003", "Verkeer, dienstvoertuig - RS 3"),
    ]
    return [
        create_load_case(
            group_name="LG6000",
            case_name=name,
            description=desc,
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        for name, desc in data
    ]


def create_unintended_vehicle_load_cases() -> list[LoadCaseDefinition]:
    """
    Create definitions for unintended vehicle load cases BG7001 to BG7003.

    :returns: List of unintended vehicle load case definitions.
    :rtype: list[LoadCaseDefinition]
    """
    data = [
        ("BG7001", "Verkeer, onbedoeld voertuig - RS 1"),
        ("BG7002", "Verkeer, onbedoeld voertuig - RS 2"),
        ("BG7003", "Verkeer, onbedoeld voertuig - RS 3"),
    ]
    return [
        create_load_case(
            group_name="LG7000",
            case_name=name,
            description=desc,
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        for name, desc in data
    ]


def create_tandem_rs_load_cases(rs: int) -> list[LoadCaseDefinition]:
    """
    Create definitions for tandem system load cases for a given RS (1,2,3).

    :param rs: Road system number (1, 2, or 3).
    :type rs: int
    :returns: List of tandem load case definitions for the specified RS.
    :rtype: list[LoadCaseDefinition]
    :raises ValueError: If rs is not 1, 2, or 3.
    """
    if rs == 1:
        group_name = "LG8000"
        prefix = "BG80"
    elif rs == 2:
        group_name = "LG9000"
        prefix = "BG90"
    elif rs == 3:
        group_name = "LG10000"
        prefix = "BG100"
    else:
        raise ValueError("RS must be 1, 2, or 3")

    positions = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6]
    cases = []
    for i, pos in enumerate(positions, 1):
        case_name = f"{prefix}{i:02d}"
        description = f"Verkeer, dek - LM1 TS RS {rs} - x = {pos} m"
        cases.append(
            create_load_case(
                group_name=group_name,
                case_name=case_name,
                description=description,
                case_type="VARIABLE",
                variable_type="STATIC",
                specification="STANDARD",
                duration="SHORT",
            )
        )
    return cases
