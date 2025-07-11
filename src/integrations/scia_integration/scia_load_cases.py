"""
SCIA load cases utility module.

This module provides functions for creating standard SCIA load cases by calling
the SciaModelBuilder interface.
"""

from typing import Any, Literal

from .scia_bridge_geometry import extract_tandem_parameters_from_bridge
from .scia_loads_helper import generate_theoretical_lane_positions, tandem_system_sequencer
from .scia_model_interface import SciaLoadCase, SciaModelBuilder


def create_load_case(  # noqa: PLR0913
    builder: SciaModelBuilder,
    group_name: str,
    case_name: str,
    description: str,
    case_type: Literal["PERMANENT", "VARIABLE"],
    permanent_type: str | None = None,
    variable_type: str | None = None,
    specification: str | None = None,
    duration: str | None = None,
) -> SciaLoadCase:
    """
    Create a SCIA load case using the provided builder.

    :param builder: The SCIA model builder instance.
    :param group_name: Name of the load group this case belongs to.
    :param case_name: Name for the load case.
    :param description: Description of the load case.
    :param case_type: "PERMANENT" or "VARIABLE".
    :param permanent_type: "SELF_WEIGHT", "STANDARD", "PRIMARY_EFFECT"
    :param variable_type: "STATIC", "PRIMARY_EFFECT"
    :param specification: "STANDARD", "STATIC_WIND", "SNOW", "TEMPERATURE", "EARTHQUAKE"
    :param duration: "INSTANTANEOUS", "SHORT", "MEDIUM", "LONG"
    :returns: The created SCIA Load Case object.
    :rtype: SciaLoadCase
    """
    return builder.create_load_case(
        name=case_name,
        description=description,
        group_name=group_name,
        case_type=case_type,
        permanent_type=permanent_type,
        variable_type=variable_type,
        specification=specification,
        duration=duration,
    )


def create_self_weight_load_case(builder: SciaModelBuilder) -> SciaLoadCase:
    """
    Create the self-weight load case BG1001.

    :param builder: The SCIA model builder instance.
    :returns: The created self-weight load case.
    :rtype: SciaLoadCase
    """
    return create_load_case(
        builder,
        group_name="LG1000",
        case_name="BG1001",
        description="Eigen gewicht",
        case_type="PERMANENT",
        permanent_type="SELF_WEIGHT",
    )


def create_dead_load_cases(builder: SciaModelBuilder) -> list[SciaLoadCase]:
    """
    Create dead load cases BG2001 to BG2005.

    :param builder: The SCIA model builder instance.
    :returns: List of created dead load cases.
    :rtype: list[SciaLoadCase]
    """
    data = [
        ("BG2001", "Permanente belasting - Asfalt"),
        ("BG2002", "Permanente belasting - Uitvulling"),
        ("BG2003", "Permanente belasting - Ophogingen, schampkanten, trottoir"),
        ("BG2004", "Permanente belasting - Leuning"),
        ("BG2005", "Permanente belasting - Lichtmast"),
    ]
    return [
        create_load_case(
            builder,
            group_name="LG2000",
            case_name=name,
            description=desc,
            case_type="PERMANENT",
            permanent_type="STANDARD",
        )
        for name, desc in data
    ]


def create_temperature_load_cases(builder: SciaModelBuilder) -> list[SciaLoadCase]:
    """
    Create temperature load cases BG3001 to BG3004.

    :param builder: The SCIA model builder instance.
    :returns: List of created temperature load cases.
    :rtype: list[SciaLoadCase]
    """
    data = [
        ("BG3001", "Temperatuur, dek - Temp combi 1"),
        ("BG3002", "Temperatuur, dek - Temp combi 2"),
        ("BG3003", "Temperatuur, dek - Temp combi 3"),
        ("BG3004", "Temperatuur, dek - Temp combi 4"),
    ]
    return [
        create_load_case(
            builder,
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


def create_udl_traffic_load_cases(builder: SciaModelBuilder) -> list[SciaLoadCase]:
    """
    Create UDL traffic load cases BG4001 to BG4004.

    :param builder: The SCIA model builder instance.
    :returns: List of created UDL traffic load cases.
    :rtype: list[SciaLoadCase]
    """
    data = [
        ("BG4001", "Verkeer, dek - LM1 UDL RS 1"),
        ("BG4002", "Verkeer, dek - LM1 UDL RS 2"),
        ("BG4003", "Verkeer, dek - LM1 UDL RS 3"),
        ("BG4004", "Verkeer, dek - LM1 UDL rest"),
    ]
    return [
        create_load_case(
            builder,
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


def create_pedestrian_load_case(builder: SciaModelBuilder) -> SciaLoadCase:
    """
    Create pedestrian load case BG5001.

    :param builder: The SCIA model builder instance.
    :returns: The created pedestrian load case.
    :rtype: SciaLoadCase
    """
    return create_load_case(
        builder,
        group_name="LG5000",
        case_name="BG5001",
        description="Verkeer, mensenmenigte - LM4",
        case_type="VARIABLE",
        variable_type="STATIC",
        specification="STANDARD",
        duration="SHORT",
    )


def create_service_vehicle_load_cases(builder: SciaModelBuilder) -> list[SciaLoadCase]:
    """
    Create service vehicle load cases BG6001 to BG6003.

    :param builder: The SCIA model builder instance.
    :returns: List of created service vehicle load cases.
    :rtype: list[SciaLoadCase]
    """
    data = [
        ("BG6001", "Verkeer, dienstvoertuig - RS 1"),
        ("BG6002", "Verkeer, dienstvoertuig - RS 2"),
        ("BG6003", "Verkeer, dienstvoertuig - RS 3"),
    ]
    return [
        create_load_case(
            builder,
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


def create_unintended_vehicle_load_cases(builder: SciaModelBuilder) -> list[SciaLoadCase]:
    """
    Create unintended vehicle load cases BG7001 to BG7003.

    :param builder: The SCIA model builder instance.
    :returns: List of created unintended vehicle load cases.
    :rtype: list[SciaLoadCase]
    """
    data = [
        ("BG7001", "Verkeer, onbedoeld voertuig - RS 1"),
        ("BG7002", "Verkeer, onbedoeld voertuig - RS 2"),
        ("BG7003", "Verkeer, onbedoeld voertuig - RS 3"),
    ]
    return [
        create_load_case(
            builder,
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


def create_dynamic_tandem_load_cases(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> dict[str, SciaLoadCase]:
    """
    Create dynamic tandem load cases based on bridge geometry.

    This function determines the number of theoretical lanes and creates
    the corresponding tandem system (TS) load cases for each lane (RS).

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    :return: A dictionary of all created tandem system load cases.
    :rtype: dict[str, SciaLoadCase]
    """
    load_cases = {}

    # Extract bridge parameters needed for tandem load case generation
    bridge_params = extract_tandem_parameters_from_bridge(params)
    length = bridge_params["length_bridgedeck"]
    thickness = bridge_params["thickness_bridgedeck"]
    width = bridge_params["width_bridgedeck"]

    # Determine the number of theoretical lanes, with a maximum of 3
    num_lanes = len(generate_theoretical_lane_positions(width))
    num_lanes = min(num_lanes, 3)

    # Create tandem load cases for each road system (RS)
    for rs in range(1, num_lanes + 1):
        tandem_cases_dict = create_tandem_rs_load_cases(builder, rs, length, thickness)
        load_cases.update(tandem_cases_dict)

    return load_cases


def create_tandem_rs_load_cases(builder: SciaModelBuilder, rs: int, length_bridgedeck: float, thickness_bridgedeck: float) -> dict[str, SciaLoadCase]:
    """
    Create tandem system load cases for a given RS (1,2,3).

    Positions are determined dynamically based on the bridge geometry.

    :param builder: The SCIA model builder instance.
    :param rs: Road system number (1, 2, or 3).
    :type rs: int
    :param length_bridgedeck: The length of the bridge deck in meters.
    :type length_bridgedeck: float
    :param thickness_bridgedeck: The thickness of the bridge deck in meters.
    :type thickness_bridgedeck: float
    :returns: Dictionary of tandem load cases for the specified RS.
    :rtype: dict[str, SciaLoadCase]
    :raises ValueError: If rs is not 1, 2, or 3.
    """
    if rs == 1:
        group_name = "LG8000"
        prefix = "BG8000"
    elif rs == 2:
        group_name = "LG9000"
        prefix = "BG9000"
    elif rs == 3:
        group_name = "LG10000"
        prefix = "BG10000"
    else:
        raise ValueError("RS must be 1, 2, or 3")

    positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
    cases = {}
    for i, pos in enumerate(positions, 1):
        case_name = f"{prefix}{i:03d}"
        description = f"Verkeer, dek - LM1 TS RS {rs} - x = {pos:g} m"
        cases[f"tandem_rs{rs}_x{pos}"] = create_load_case(
            builder,
            group_name=group_name,
            case_name=case_name,
            description=description,
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
    return cases


def create_all_load_cases(builder: SciaModelBuilder, params: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    Create a nested dictionary of all standard and dynamic load cases for the bridge model.

    This function aggregates all individual load case creation helpers into a single,
    structured dictionary where top-level keys represent load case categories.

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters, used for dynamic load case generation.
    :return: A nested dictionary containing all created SciaLoadCase objects.
    :rtype: dict[str, dict[str, SciaLoadCase]]
    """
    # Create a structured dictionary of all load cases
    return {
        "standard_cases": {
            "self_weight": create_self_weight_load_case(builder),
            "pedestrian": create_pedestrian_load_case(builder),
        },
        "dead_load_cases": create_dead_load_cases(builder),
        "temperature_cases": create_temperature_load_cases(builder),
        "udl_traffic_cases": create_udl_traffic_load_cases(builder),
        "service_vehicle_cases": create_service_vehicle_load_cases(builder),
        "unintended_vehicle_cases": create_unintended_vehicle_load_cases(builder),
        "tandem_cases": create_dynamic_tandem_load_cases(builder, params),
    }
