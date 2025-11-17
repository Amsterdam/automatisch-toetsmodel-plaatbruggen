"""
SCIA load cases utility module.

This module provides functions for creating standard SCIA load cases by calling
the SciaModelBuilder interface.
"""

from typing import Any

from src.integrations.scia_integration.constants import SERVICE_VEHICLE_LENGTH_FOR_SEQUENCING
from src.integrations.scia_integration.load_system.tandem_sequencer import (
    tandem_system_sequencer,
)
from src.integrations.scia_integration.model.scia_model_interface import SciaLoadCase, SciaModelBuilder
from src.integrations.scia_integration.scia_enums import (
    LoadCaseActionType,
    LoadCaseDuration,
    LoadCaseSpecification,
    PermanentLoadType,
    VariableLoadType,
)

from .scia_load_generators import extract_bridge_dimensions


def create_load_case(  # noqa: PLR0913
    builder: SciaModelBuilder,
    group_name: str,
    case_name: str,
    description: str,
    case_type: LoadCaseActionType,
    permanent_type: PermanentLoadType | None = None,
    variable_type: VariableLoadType | None = None,
    specification: LoadCaseSpecification | None = None,
    duration: LoadCaseDuration | None = None,
) -> SciaLoadCase:
    """
    Create a SCIA load case using the provided builder.

    :param builder: The SCIA model builder instance.
    :param group_name: Name of the load group this case belongs to.
    :param case_name: Name for the load case.
    :param description: Description of the load case.
    :param case_type: SDK enum for action type (PERMANENT or VARIABLE).
    :param permanent_type: SDK enum for permanent load type.
    :param variable_type: SDK enum for variable load type.
    :param specification: SDK enum for load specification.
    :param duration: SDK enum for load duration.
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
        case_type=LoadCaseActionType.PERMANENT,
        permanent_type=PermanentLoadType.SELF_WEIGHT,
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
            case_type=LoadCaseActionType.PERMANENT,
            permanent_type=PermanentLoadType.STANDARD,
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
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.TEMPERATURE,
            duration=LoadCaseDuration.LONG,
        )
    return cases


def create_udl_traffic_load_cases(builder: SciaModelBuilder, params: Any) -> dict[str, dict[str, SciaLoadCase]]:  # noqa: ANN401
    """
    Create UDL traffic load cases dynamically, categorized by lane type.

    NEW SYSTEM: Creates three separate dictionaries for main lane, other lanes, and rest areas.
    This allows different load combination factors to be applied to each category.

    Creates individual load cases for each polygon generated by the UDL generators,
    with titles matching the format defined in udl_generators.py.
    Titles include lane/rest designation, configuration (A, B, or C), and span index
    (e.g., "RS 1 - Conf. A - Span 1", "rest 1 - Conf. B - Span 2").

    Load polygons are generated per span, so each span will have its own set of load cases
    for each lane and rest area. Load cases are numbered sequentially (BG4001, BG4002, etc.)
    across all spans.

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters for generating UDL loads.
    :returns: Dictionary with three keys: "udl_main_cases", "udl_other_cases", "udl_rest_cases", 
              each containing a dict of load cases keyed by BG4xxx names.
    :rtype: dict[str, dict[str, SciaLoadCase]]
    """
    from src.integrations.scia_integration.constants import UDL_BASE_VALUE
    from src.integrations.scia_integration.load_system.scia_load_generators import extract_bridge_dimensions, get_load_mode_from_params
    from src.integrations.scia_integration.load_system.udl_generators import (
        create_real_udl_traffic_loads,
        create_theoretical_udl_traffic_loads,
    )
    from src.integrations.scia_integration.types import LoadMode

    # Get load mode from params
    mode = get_load_mode_from_params(params)
    dims = extract_bridge_dimensions(params)

    # Generate UDL loads to determine which load cases we need
    if mode == LoadMode.THEORETICAL:
        udl_results = create_theoretical_udl_traffic_loads(
            params, dims.total_length, dims.total_width, dims.zone3_width, dims.zone2_width, UDL_BASE_VALUE
        )
    else:
        udl_results = create_real_udl_traffic_loads(params, dims.total_length, UDL_BASE_VALUE)

    # Create three separate dictionaries for different lane types
    main_cases = {}
    other_cases = {}
    rest_cases = {}

    # Create a load case for each generated UDL load
    for load_case_name, load_data in sorted(udl_results.items()):  # Sort to ensure consistent ordering
        title = load_data.get("title", "")

        # Extract configuration from title to determine group name
        group_name = "LG4000 - UDL - conf. A"  # Default to conf. A
        if "Conf. A" in title:
            group_name = "LG4000 - UDL - conf. A"
        elif "Conf. B" in title:
            group_name = "LG4001 - UDL - conf. B"
        elif "Conf. C" in title:
            group_name = "LG4002 - UDL - conf. C"

        # Create the load case with the title as description
        description = f"Verkeer, dek - LM1 UDL {title}" if title else f"Verkeer, dek - LM1 UDL {load_case_name}"

        load_case = create_load_case(
            builder,
            group_name=group_name,
            case_name=load_case_name,
            description=description,
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )

        # Categorize by lane type based on title
        if title.startswith("RS 1 "):
            # Main lane (RS 1)
            main_cases[load_case_name] = load_case
        elif title.startswith("RS "):
            # Other lanes (RS 2, RS 3, etc.)
            other_cases[load_case_name] = load_case
        elif title.startswith("rest "):
            # Rest areas
            rest_cases[load_case_name] = load_case
        else:
            # Fallback: categorize as other
            other_cases[load_case_name] = load_case

    return {
        "udl_main_cases": main_cases,
        "udl_other_cases": other_cases,
        "udl_rest_cases": rest_cases,
    }


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
        case_type=LoadCaseActionType.VARIABLE,
        variable_type=VariableLoadType.STATIC,
        specification=LoadCaseSpecification.STANDARD,
        duration=LoadCaseDuration.SHORT,
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

    positions = tandem_system_sequencer(length, thickness, length_vehicle=SERVICE_VEHICLE_LENGTH_FOR_SEQUENCING)

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
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )

    # Create load cases for y_minus (bottom edge), continuing numbering
    for i, pos in enumerate(positions, len(positions) + 1):
        case_name = f"BG6{i:03d}"
        key = f"y_minus_x{pos}"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, dienstvoertuig - y- - x = {pos:g} m",
            group_name="LG6000 - Dienstvoertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
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

    positions = tandem_system_sequencer(length, thickness, length_vehicle=1.2)
    positions_amsterdam = tandem_system_sequencer(length, thickness)
    positions_amsterdam_rotated = tandem_system_sequencer(length, thickness, length_vehicle=2.0)

    cases = {}
    case_counter = 1

    # Create load cases for y_plus (top edge) - Forward direction
    for pos in positions:
        case_name = f"BG7{case_counter:03d}"
        key = f"y_plus_x{pos}_forward"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - y+ forward - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
        case_counter += 1

    # Create load cases for y_plus (top edge) - Reverse direction
    for pos in positions:
        case_name = f"BG7{case_counter:03d}"
        key = f"y_plus_x{pos}_reverse"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - y+ reverse - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
        case_counter += 1

    # Create load cases for y_minus (bottom edge) - Forward direction
    for pos in positions:
        case_name = f"BG7{case_counter:03d}"
        key = f"y_minus_x{pos}_forward"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - y- forward - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
        case_counter += 1

    # Create load cases for y_minus (bottom edge) - Reverse direction
    for pos in positions:
        case_name = f"BG7{case_counter:03d}"
        key = f"y_minus_x{pos}_reverse"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - y- reverse - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
        case_counter += 1

    # Create load cases for Amsterdam vehicle on y_plus and y_minus
    for pos in positions_amsterdam:
        case_name = f"BG7{case_counter:03d}"
        key = f"y_plus_x{pos}_amsterdam"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - y+ Amsterdam - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
        case_counter += 1
    for pos in positions_amsterdam:
        case_name = f"BG7{case_counter:03d}"
        key = f"y_minus_x{pos}_amsterdam"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - y- Amsterdam - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
        case_counter += 1

    # Create load cases for Amsterdam vehicle on y_plus and y_minus - Rotated
    for pos in positions_amsterdam_rotated:
        case_name = f"BG7{case_counter:03d}"
        key = f"y_plus_x{pos}_amsterdam_rotated"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - y+ Amsterdam rotated - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
        case_counter += 1

    for pos in positions_amsterdam_rotated:
        case_name = f"BG7{case_counter:03d}"
        key = f"y_minus_x{pos}_amsterdam_rotated"
        cases[key] = builder.create_load_case(
            name=case_name,
            description=f"Verkeer, onbedoeld voertuig - y- Amsterdam rotated - x = {pos:g} m",
            group_name="LG7000 - Onbedoeld voertuig",
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
        case_counter += 1

    return cases


def count_tram_tracks_from_params(params: Any) -> int:  # noqa: ANN401
    """
    Count the number of tram tracks from the load zones data.

    Tram tracks are identified by zone_type == "Tram" in the load_zones_data_array.

    :param params: Bridge parameters containing load_zones_data_array.
    :type params: Any
    :returns: Number of tram tracks (zones with zone_type "Tram").
    :rtype: int
    """
    try:
        load_zones = params.load_zones_data_array
        if load_zones is None or not isinstance(load_zones, list):
            return 0

        # Count zones where zone_type is "Tram"
        return sum(1 for zone in load_zones if zone.get("zone_type") == "Tram")
    except (AttributeError, TypeError):
        return 0


def create_dynamic_tandem_load_cases(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> dict[str, SciaLoadCase]:
    """
    Create dynamic tandem load cases based on bridge geometry.

    This function generates tandem loads first to determine what load cases are needed,
    then creates the corresponding tandem system (TS) load cases dynamically.
    Load cases are assigned to load groups based on the notional lane (RS) mentioned
    in their title: "rs 1" → LG8000, "rs 2" → LG9000, "rs 3" → LG10000.

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    :return: A dictionary of all created tandem system load cases.
    :rtype: dict[str, SciaLoadCase]
    """
    from src.integrations.scia_integration.load_system.scia_load_generators import generate_tandem_loads

    load_cases = {}

    # Generate tandem loads to determine what load cases we need
    tandem_loads = generate_tandem_loads(params)

    # Create load cases based on the generated loads
    for tandem_load in tandem_loads:
        load_case_name = tandem_load["load_case"]

        # Skip if already created
        if load_case_name in load_cases:
            continue

        # Get title from tandem_load
        title = tandem_load.get("title", "")

        # Determine group name based on which notional lane (RS) is in the title
        # This allows all tandem loads for a specific lane to be grouped together
        # regardless of their load case series number
        title_lower = title.lower()
        if "rs 1" in title_lower:
            group_name = "LG8000 - TS rijstrook 1"
        elif "rs 2" in title_lower:
            group_name = "LG9000 - TS rijstrook 2"
        elif "rs 3" in title_lower:
            group_name = "LG10000 - TS rijstrook 3"
        else:
            # Skip load cases without recognizable lane designation
            continue

        # Create description with title
        description = f"Verkeer, dek - LM1 TS - {title}" if title else f"Verkeer, dek - LM1 TS - {load_case_name}"

        load_cases[load_case_name] = create_load_case(
            builder,
            group_name=group_name,
            case_name=load_case_name,
            description=description,
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )

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

    positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=1.6)
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
                case_type=LoadCaseActionType.VARIABLE,
                variable_type=VariableLoadType.STATIC,
                specification=LoadCaseSpecification.STANDARD,
                duration=LoadCaseDuration.SHORT,
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
                case_type=LoadCaseActionType.VARIABLE,
                variable_type=VariableLoadType.STATIC,
                specification=LoadCaseSpecification.STANDARD,
                duration=LoadCaseDuration.SHORT,
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
                case_type=LoadCaseActionType.VARIABLE,
                variable_type=VariableLoadType.STATIC,
                specification=LoadCaseSpecification.STANDARD,
                duration=LoadCaseDuration.SHORT,
            )
    return cases


def create_dynamic_tram_track_tandem_load_cases(
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

    # Determine the number of tracks based on bridge parameters
    num_tracks = count_tram_tracks_from_params(params)

    # Create tandem load cases for each road system (RS)
    for track in range(1, num_tracks + 1):
        tram_tandem_cases_dict = create_tram_track_tandem_load_cases(builder, track, length, thickness)
        load_cases.update(tram_tandem_cases_dict)

    return load_cases


def create_tram_track_tandem_load_cases(
    builder: SciaModelBuilder, track: int, length_bridgedeck: float, thickness_bridgedeck: float
) -> dict[str, SciaLoadCase]:
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
    if track == 1:
        group_name = "LG11000 - TS tramspoor 1"
        prefix = "BG11"
    elif track == 2:
        group_name = "LG12000 - TS tramspoor 2"
        prefix = "BG12"
    else:
        raise ValueError("Track must be 1 or 2")

    positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=21.824)  # Tram length 15G (CAF Urbos 100)
    cases = {}
    for i, pos in enumerate(positions, 1):
        case_name = f"{prefix}{i:03d}"
        description = f"Tram, dek - Tramspoor {track} - x = {pos:g} m"
        cases[f"tandem_tram_track{track}_x{pos}"] = create_load_case(
            builder,
            group_name=group_name,
            case_name=case_name,
            description=description,
            case_type=LoadCaseActionType.VARIABLE,
            variable_type=VariableLoadType.STATIC,
            specification=LoadCaseSpecification.STANDARD,
            duration=LoadCaseDuration.SHORT,
        )
    return cases


def _get_load_case_selection_from_table(params: Any) -> dict[str, bool]:  # noqa: ANN401
    """
    Extract load case selection from the parametrization table.

    :param params: Bridge parameters containing load_case_selection_table.
    :return: Dictionary mapping load type names to boolean inclusion status.
    :rtype: dict[str, bool]
    """
    # Default selection (all enabled except Tram) for backward compatibility
    # Note: Tram is disabled by default to match UI default (unchecked).
    # User must explicitly enable tram loads via the checkbox.
    default_selection = {
        "Eigen gewicht": True,
        "Permanent": True,
        "Temperatuur": True,
        "UDL": True,
        "Voetgangers": True,
        "Dienstvoertuig": True,
        "Onbedoeld voertuig": True,
        "TS": True,
        "Tram": False,  # Default False - requires explicit user enablement
    }

    try:
        # Try to get the table from params
        table = getattr(params, "load_case_selection_table", None)
        if table is None:
            return default_selection

        # Extract selection from table rows and merge with defaults
        # Start with defaults, then override with table values
        selection = default_selection.copy()
        for row in table:
            load_type = row.get("load_type", "")
            include = row.get("include", True)
            if load_type:  # Only add non-empty load types
                selection[load_type] = include
    except (AttributeError, TypeError, KeyError):
        # Fallback to default if table is not available or malformed
        return default_selection
    else:
        return selection


def create_all_load_cases(builder: SciaModelBuilder, params: Any) -> dict[str, Any]:  # noqa: ANN401
    """
    Create a nested dictionary of all standard and dynamic load cases for the bridge model.

    This function aggregates all individual load case creation helpers into a single,
    structured dictionary where top-level keys represent load case categories.
    Load cases are created conditionally based on user selection in the parametrization table.

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters, used for dynamic load case generation and load case selection.
    :return: A nested dictionary containing all created SciaLoadCase objects.
    :rtype: dict[str, dict]
    """
    # Get load case selection from table
    load_selection = _get_load_case_selection_from_table(params)

    # Initialize the load cases dictionary
    load_cases = {}

    # Self-weight load case (BG1001)
    if load_selection.get("Eigen gewicht", True):
        load_cases["self_weight"] = create_self_weight_load_case(builder)

    # Dead load cases (BG2001-BG2005)
    if load_selection.get("Permanent", True):
        load_cases["dead_load_cases"] = create_dead_load_cases(builder)

    # Temperature load cases (BG3001-BG3004)
    if load_selection.get("Temperatuur", True):
        load_cases["temperature_cases"] = create_temperature_load_cases(builder)

    # UDL traffic load cases (BG4000 series) - now split into three categories
    if load_selection.get("UDL", True):
        udl_cases_dict = create_udl_traffic_load_cases(builder, params)
        load_cases["udl_main_cases"] = udl_cases_dict["udl_main_cases"]
        load_cases["udl_other_cases"] = udl_cases_dict["udl_other_cases"]
        load_cases["udl_rest_cases"] = udl_cases_dict["udl_rest_cases"]

    # Pedestrian load case (BG5001)
    if load_selection.get("Voetgangers", True):
        load_cases["pedestrian"] = create_pedestrian_load_case(builder)

    # Service vehicle load cases (BG6000 series)
    if load_selection.get("Dienstvoertuig", True):
        load_cases["service_vehicle_cases"] = create_service_vehicle_load_cases(builder, params)

    # Unintended vehicle load cases (BG7000 series)
    if load_selection.get("Onbedoeld voertuig", True):
        load_cases["unintended_vehicle_cases"] = create_unintended_vehicle_load_cases(builder, params)

    # Tandem system load cases (BG8000-BG10000 series)
    if load_selection.get("TS", True):
        load_cases["tandem_cases"] = create_dynamic_tandem_load_cases(builder, params)

    # Tram track tandem system load cases (BG11000-BG12000 series)
    if load_selection.get("Tram", False):
        load_cases["tram_track_tandem_cases"] = create_dynamic_tram_track_tandem_load_cases(builder, params)

    return load_cases
