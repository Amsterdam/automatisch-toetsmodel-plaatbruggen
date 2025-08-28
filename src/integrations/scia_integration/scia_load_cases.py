"""
SCIA load cases utility module.

This module provides functions for creating standard SCIA load cases by calling
the SciaModelBuilder interface.
"""

from typing import Any, Literal

from .scia_load_generators import extract_bridge_dimensions
from .scia_loads_helper import (
    generate_theoretical_lane_positions_bg8000,
    tandem_system_sequencer,
)
from .scia_model_interface import SciaLoadCase, SciaModelBuilder


def create_load_case(  # noqa: PLR0913
    builder: SciaModelBuilder,
    group_name: str,
    case_name: str,
    description: str,
    case_type: Literal["PERMANENT", "VARIABLE"],
    permanent_type: Literal["SELF_WEIGHT", "STANDARD", "PRIMARY_EFFECT"] | None = None,
    variable_type: Literal["STATIC", "PRIMARY_EFFECT"] | None = None,
    specification: Literal["STANDARD", "STATIC_WIND", "SNOW", "TEMPERATURE", "EARTHQUAKE"] | None = None,
    duration: Literal["INSTANTANEOUS", "SHORT", "MEDIUM", "LONG"] | None = None,
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
        group_name="LG1000 - Permanent",
        case_name="BG1001",
        description="Eigen gewicht",
        case_type="PERMANENT",
        permanent_type="SELF_WEIGHT",
    )


def create_dead_load_cases(builder: SciaModelBuilder) -> dict[str, SciaLoadCase]:
    """
    Create dead load cases BG2001 to BG2005.

    :param builder: The SCIA model builder instance.
    :returns: Dictionary of created dead load cases.
    :rtype: dict[str, SciaLoadCase]
    """
    data = [
        ("asfalt", "BG2001", "Permanente belasting - Asfalt"),
        ("uitvulling", "BG2002", "Permanente belasting - Uitvulling"),
        ("ophogingen", "BG2003", "Permanente belasting - Ophogingen, schampkanten, trottoir"),
        ("leuning", "BG2004", "Permanente belasting - Leuning"),
        ("lichtmast", "BG2005", "Permanente belasting - Lichtmast"),
    ]
    cases = {}
    for key, name, desc in data:
        cases[key] = create_load_case(
            builder,
            group_name="LG2000 - Rustende belasting",
            case_name=name,
            description=desc,
            case_type="PERMANENT",
            permanent_type="STANDARD",
        )
    return cases


def create_temperature_load_cases(builder: SciaModelBuilder) -> dict[str, SciaLoadCase]:
    """
    Create temperature load cases BG3001 to BG3004.

    :param builder: The SCIA model builder instance.
    :returns: Dictionary of created temperature load cases.
    :rtype: dict[str, SciaLoadCase]
    """
    data = [
        ("combi_1", "BG3001", "Temperatuur, dek - Temp combi 1"),
        ("combi_2", "BG3002", "Temperatuur, dek - Temp combi 2"),
        ("combi_3", "BG3003", "Temperatuur, dek - Temp combi 3"),
        ("combi_4", "BG3004", "Temperatuur, dek - Temp combi 4"),
    ]
    cases = {}
    for key, name, desc in data:
        cases[key] = create_load_case(
            builder,
            group_name="LG3000 - Temperatuur",
            case_name=name,
            description=desc,
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="TEMPERATURE",
            duration="LONG",
        )
    return cases


def create_udl_traffic_load_cases(builder: SciaModelBuilder) -> dict[str, SciaLoadCase]:
    """
    Create UDL traffic load cases BG4001 to BG4004.

    :param builder: The SCIA model builder instance.
    :returns: Dictionary of created UDL traffic load cases.
    :rtype: dict[str, SciaLoadCase]
    """
    data = [
        ("rs_1", "BG4001", "Verkeer, dek - LM1 UDL RS 1"),
        ("rs_2", "BG4002", "Verkeer, dek - LM1 UDL RS 2"),
        ("rs_3", "BG4003", "Verkeer, dek - LM1 UDL RS 3"),
    ]
    cases = {}
    for key, name, desc in data:
        cases[key] = create_load_case(
            builder,
            group_name="LG4000 - UDL",
            case_name=name,
            description=desc,
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
    return cases


def create_pedestrian_load_case(builder: SciaModelBuilder) -> SciaLoadCase:
    """
    Create pedestrian load case BG5001.

    :param builder: The SCIA model builder instance.
    :returns: The created pedestrian load case.
    :rtype: SciaLoadCase
    """
    return create_load_case(
        builder,
        group_name="LG5000 - Mensenmenigte",
        case_name="BG5001",
        description="Verkeer, mensenmenigte - LM4",
        case_type="VARIABLE",
        variable_type="STATIC",
        specification="STANDARD",
        duration="SHORT",
    )


def create_service_vehicle_load_cases(builder: SciaModelBuilder, params: Any) -> dict[str, SciaLoadCase]:  # noqa: ANN401
    """
    Create service vehicle load cases with dynamic positioning based on bridge geometry.

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters for calculating positions.
    :returns: Dictionary of created service vehicle load cases.
    :rtype: dict[str, SciaLoadCase]
    """
    # Extract bridge dimensions needed for position calculation
    dims = extract_bridge_dimensions(params)
    length = dims.total_length
    thickness = dims.thickness

    # Get X positions using the same sequencer as tandem loads

    positions = tandem_system_sequencer(length, thickness)

    cases = {}

    # Create load cases for y_plus (top edge)
    for i, pos in enumerate(positions, 1):
        case_name = f"BG6{i:03d}"
        key = f"y_plus_x{pos}"
        # Call builder directly to avoid passing permanent_type=None (tests expect it omitted)
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, dienstvoertuig - y+ - x = {pos:g} m",
            group_name="LG6000 - Dienstvoertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )

    # Create load cases for y_minus (bottom edge), continuing numbering
    for i, pos in enumerate(positions, len(positions) + 1):
        case_name = f"BG6{i:03d}"
        key = f"y_minus_x{pos}"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, dienstvoertuig - y- - x = {pos:g} m",
            group_name="LG6000 - Dienstvoertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )

    return cases


def create_unintended_vehicle_load_cases(builder: SciaModelBuilder, params: Any) -> dict[str, SciaLoadCase]:  # noqa: ANN401
    """
    Create unintended vehicle load cases with dynamic positioning based on bridge geometry.
    Creates loads for both forward and reverse directions on edges (RS 1 and RS 3).

    Forward: 80 kN front axle leads, 40 kN rear axle follows
    Reverse: 80 kN front axle leads in opposite direction

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters for calculating positions.
    :returns: Dictionary of created unintended vehicle load cases.
    :rtype: dict[str, SciaLoadCase]
    """
    # Extract bridge dimensions needed for position calculation
    dims = extract_bridge_dimensions(params)
    length = dims.total_length
    thickness = dims.thickness

    # Get X positions using the same sequencer as tandem loads

    positions = tandem_system_sequencer(length, thickness)

    cases = {}
    case_counter = 1

    # Create load cases for RS 1 (top edge) - Forward direction
    for pos in positions:
        case_name = f"BG7{case_counter:03d}"
        key = f"rs_1_x{pos}_forward"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - RS 1 forward - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        case_counter += 1

    # Create load cases for RS 1 (top edge) - Reverse direction
    for pos in positions:
        case_name = f"BG7{case_counter:03d}"
        key = f"rs_1_x{pos}_reverse"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - RS 1 reverse - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        case_counter += 1

    # Create load cases for RS 3 (bottom edge) - Forward direction
    for pos in positions:
        case_name = f"BG7{case_counter:03d}"
        key = f"rs_3_x{pos}_forward"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - RS 3 forward - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        case_counter += 1

    # Create load cases for RS 3 (bottom edge) - Reverse direction
    for pos in positions:
        case_name = f"BG7{case_counter:03d}"
        key = f"rs_3_x{pos}_reverse"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - RS 3 reverse - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type="VARIABLE",
            variable_type="STATIC",
            specification="STANDARD",
            duration="SHORT",
        )
        case_counter += 1

    return cases


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

    # Extract bridge dimensions needed for tandem load case generation
    dims = extract_bridge_dimensions(params)
    length = dims.total_length
    thickness = dims.thickness
    width = dims.total_width

    # Determine the number of theoretical lanes, with a maximum of 3
    # Use alias to allow tests to patch 'generate_theoretical_lane_positions'
    num_lanes = len(generate_theoretical_lane_positions_bg8000(width))
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
        group_name = "LG8000 - TS rijstrook 1"
        prefix = "BG8"
    elif rs == 2:
        group_name = "LG9000 - TS rijstrook 2"
        prefix = "BG9"
    elif rs == 3:
        group_name = "LG10000 - TS rijstrook 3"
        prefix = "BG10"
    else:
        raise ValueError("RS must be 1, 2, or 3")

    positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
    cases = {}
    if rs == 3:
        # BG10000 series: double amount for both configurations
        idx = 1
        # First configuration (A): 200 kN left, 100 kN right
        for pos in positions:
            case_name = f"{prefix}{idx:03d}"
            description = f"Verkeer, dek - LM1 TS RS 3 (configuratie 1) - x = {pos:g} m"
            cases[f"tandem_rs3_x{pos}_A"] = create_load_case(
                builder,
                group_name=group_name,
                case_name=case_name,
                description=description,
                case_type="VARIABLE",
                variable_type="STATIC",
                specification="STANDARD",
                duration="SHORT",
            )
            idx += 1
        # Second configuration (B): 100 kN left, 200 kN right
        for pos in positions:
            case_name = f"{prefix}{idx:03d}"
            description = f"Verkeer, dek - LM1 TS RS 3 (configuratie 2) - x = {pos:g} m"
            cases[f"tandem_rs3_x{pos}_B"] = create_load_case(
                builder,
                group_name=group_name,
                case_name=case_name,
                description=description,
                case_type="VARIABLE",
                variable_type="STATIC",
                specification="STANDARD",
                duration="SHORT",
            )
            idx += 1
    else:
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
    :rtype: dict[str, dict]
    """
    # Create a structured dictionary of all load cases
    return {
        "self_weight": create_self_weight_load_case(builder),
        "dead_load_cases": create_dead_load_cases(builder),
        "temperature_cases": create_temperature_load_cases(builder),
        "udl_traffic_cases": create_udl_traffic_load_cases(builder),
        "pedestrian": create_pedestrian_load_case(builder),
        "service_vehicle_cases": create_service_vehicle_load_cases(builder, params),
        "unintended_vehicle_cases": create_unintended_vehicle_load_cases(builder, params),
        "tandem_cases": create_dynamic_tandem_load_cases(builder, params),
    }
