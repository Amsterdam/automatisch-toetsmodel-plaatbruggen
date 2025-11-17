"""
UDL (Uniformly Distributed Load) traffic load generators.

This module provides functions for generating UDL traffic loads for both
theoretical and real lane distributions on bridge decks.

All functions are independent of the VIKTOR SDK and suitable for use in the core logic layer.
"""

from typing import TYPE_CHECKING, Any

from src.integrations.scia_integration.constants.geometry import (
    DEFAULT_LANE_WIDTH,
    LANE_CENTER_OFFSET_FACTOR,
)
from src.integrations.scia_integration.constants.load_cases import (
    CONFIGURATION_A,
    CONFIGURATION_B,
    CONFIGURATION_C,
    LANE_TITLE_PREFIX,
    REST_AREA_TITLE_PREFIX,
)
from src.integrations.scia_integration.constants.loads import (
    DEFAULT_UDL_VALUE,
)
from src.integrations.scia_integration.load_system.lane_calculations import (
    amount_of_notional_lanes,
    amount_of_notional_lanes_from_center,
)
from src.integrations.scia_integration.load_system.load_value_calculators import (
    calculate_real_udl_values,
    calculate_theoretical_udl_values,
)
from src.integrations.scia_integration.load_system.road_zone_utils import (
    get_number_of_road_zones,
    get_widths_of_two_road_zones,
    obtain_y_coordinates_road,
    obtain_y_coordinates_two_road_zones,
)
from src.integrations.scia_integration.load_system.theoretical_tandem_generators import (
    generate_theoretical_lane_positions_bg8000,
    generate_theoretical_lane_positions_bg9000,
)
from src.integrations.scia_integration.model.scia_section_on_plane import (
    Span,
    _identify_spans,
)

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


# Forward declarations - these will be imported from real_tandem_generators
def generate_real_lane_positions_bg8000(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[float]:
    """Forward declaration - implemented in real_tandem_generators."""
    from .real_tandem_generators import generate_real_lane_positions_bg8000 as _impl

    return _impl(params, lane_width)


def generate_real_lane_positions_two_road_zones(
    params: "BridgeParametrization",
    positioning_strategy: str,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[float]:
    """Forward declaration - implemented in real_tandem_generators."""
    from .real_tandem_generators import generate_real_lane_positions_two_road_zones as _impl

    return _impl(params, positioning_strategy, lane_width)


def generate_real_lane_positions_bg9000(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[float]:
    """Forward declaration - implemented in real_tandem_generators."""
    from .real_tandem_generators import generate_real_lane_positions_bg9000 as _impl

    return _impl(params, lane_width)


def generate_real_lane_positions_bg10000(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[float]:
    """Forward declaration - implemented in real_tandem_generators."""
    from .real_tandem_generators import generate_real_lane_positions_bg10000 as _impl

    return _impl(params, lane_width)


# ========================================================================
# HELPER FUNCTIONS FOR UDL LOAD CASE GENERATION
# ========================================================================


def _create_rectangular_polygon(
    span: "Span",  # type: ignore[name-defined]
    y_min: float,
    y_max: float,
    z: float = 0.0,
) -> list[tuple[float, float, float]]:
    """
    Create a rectangular polygon for a lane or rest area.

    :param span: Span object with start_x and end_x
    :type span: Span
    :param y_min: Minimum Y coordinate
    :type y_min: float
    :param y_max: Maximum Y coordinate
    :type y_max: float
    :param z: Z coordinate (default 0.0)
    :type z: float
    :returns: List of 4 corner points (counter-clockwise)
    :rtype: list[tuple[float, float, float]]
    """
    return [
        (span.start_x, y_min, z),
        (span.end_x, y_min, z),
        (span.end_x, y_max, z),
        (span.start_x, y_max, z),
    ]


def _calculate_lane_boundaries(
    y_center: float,
    lane_width: float,
) -> tuple[float, float]:
    """
    Calculate lane Y boundaries from center position.

    :param y_center: Center Y coordinate
    :type y_center: float
    :param lane_width: Width of the lane
    :type lane_width: float
    :returns: (y_min, y_max) tuple
    :rtype: tuple[float, float]
    """
    half_width = lane_width * LANE_CENTER_OFFSET_FACTOR
    return y_center - half_width, y_center + half_width


def _format_load_case_name(counter: int) -> str:
    """
    Format UDL load case name.

    :param counter: Load case counter
    :type counter: int
    :returns: Formatted name like "BG4001"
    :rtype: str
    """
    from src.integrations.scia_integration.constants.load_cases import LOAD_CASE_NUMBER_WIDTH, UDL_LOAD_CASE_PREFIX

    return f"{UDL_LOAD_CASE_PREFIX}{counter:0{LOAD_CASE_NUMBER_WIDTH}d}"


def _format_load_case_title(
    lane_type: str,
    lane_number: int,
    configuration: str,
    span_index: int,
) -> str:
    """
    Format load case title.

    :param lane_type: "RS" or "rest"
    :type lane_type: str
    :param lane_number: Lane/rest area number
    :type lane_number: int
    :param configuration: Configuration string (e.g., "Conf. A")
    :type configuration: str
    :param span_index: Span index (1-based)
    :type span_index: int
    :returns: Formatted title like "RS 1 - Conf. A - Span 1"
    :rtype: str
    """
    from src.integrations.scia_integration.constants.load_cases import SPAN_LABEL, TITLE_SEPARATOR

    return f"{lane_type} {lane_number}{TITLE_SEPARATOR}{configuration}{TITLE_SEPARATOR}{SPAN_LABEL} {span_index}"


def _create_load_case_entry(  # noqa: PLR0913
    counter: int,
    span: "Span",  # type: ignore[name-defined]
    y_min: float,
    y_max: float,
    load_value: float,
    lane_type: str,
    lane_number: int,
    configuration: str,
) -> tuple[str, dict[str, Any]]:
    """
    Create a complete load case entry.

    :param counter: Load case counter
    :type counter: int
    :param span: Span object
    :type span: Span
    :param y_min: Minimum Y coordinate
    :type y_min: float
    :param y_max: Maximum Y coordinate
    :type y_max: float
    :param load_value: Load value in N/m²
    :type load_value: float
    :param lane_type: Type of lane ("RS" or "rest")
    :type lane_type: str
    :param lane_number: Lane or rest area number
    :type lane_number: int
    :param configuration: Configuration string
    :type configuration: str
    :returns: (case_name, case_data) tuple
    :rtype: tuple[str, dict[str, Any]]
    """
    polygon = _create_rectangular_polygon(span, y_min, y_max)
    title = _format_load_case_title(lane_type, lane_number, configuration, span.span_index)

    case_name = _format_load_case_name(counter)
    case_data = {"polygon": polygon, "load": load_value, "title": title}

    return case_name, case_data


def _generate_lane_load_cases(  # noqa: PLR0913
    span: "Span",  # type: ignore[name-defined]
    y_positions: list[float],
    lane_width: float,
    max_lanes: int,
    main_value: float,
    other_value: float,
    configuration: str,
    load_case_counter: int,
) -> tuple[dict[str, dict[str, Any]], int]:
    """
    Generate lane load cases for a configuration.

    :param span: Span object
    :type span: Span
    :param y_positions: List of lane center Y positions
    :type y_positions: list[float]
    :param lane_width: Width of lanes
    :type lane_width: float
    :param max_lanes: Maximum number of lanes to generate
    :type max_lanes: int
    :param main_value: Load value for main lane in N/m²
    :type main_value: float
    :param other_value: Load value for other lanes in N/m²
    :type other_value: float
    :param configuration: Configuration string (e.g., "Conf. A")
    :type configuration: str
    :param load_case_counter: Current load case counter
    :type load_case_counter: int
    :returns: (results_dict, updated_counter) tuple
    :rtype: tuple[dict[str, dict[str, Any]], int]
    """
    from src.integrations.scia_integration.constants.load_cases import LANE_TITLE_PREFIX

    results = {}

    for lane_idx, y_center in enumerate(y_positions[:max_lanes]):
        y_min, y_max = _calculate_lane_boundaries(y_center, lane_width)
        rs_number = lane_idx + 1
        load_value = main_value if lane_idx == 0 else other_value

        case_name, case_data = _create_load_case_entry(load_case_counter, span, y_min, y_max, load_value, LANE_TITLE_PREFIX, rs_number, configuration)

        results[case_name] = case_data
        load_case_counter += 1

    return results, load_case_counter


# ========================================================================
# UNIFORMLY DISTRIBUTED TRAFFIC LOADS (UDL) FOR MAIN NOTIONAL LANES
# ========================================================================


def create_theoretical_udl_traffic_loads(  # noqa: PLR0913, C901
    params: "BridgeParametrization",
    length_bridgedeck: float,
    width_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    udl_value: float = DEFAULT_UDL_VALUE,
) -> dict[str, dict[str, Any]]:
    """
    Create UDLs for all notional lanes and remaining areas.

    Creates individual load cases for each polygon with naming:
    - "RS 1", "RS 2", etc. for notional lanes (main and other)
    - "rest 1", "rest 2", etc. for remaining areas
    - "Conf. A", "Conf. B", "Conf. C" for configurations
    - "Span 1", "Span 2", etc. for span indices

    :param length_bridgedeck: Bridge length in meters
    :param width_bridgedeck: Bridge width in meters
    :param width_firstsegment_zone3: Zone 3 width (for lane offset)
    :param width_firstsegment_zone2: Zone 2 width (for lane offset)
    :param udl_value: UDL value for main lane in N/m² (default DEFAULT_UDL_VALUE)
    :returns: Dict with keys BG4001, BG4002, etc., each containing a single polygon with load and title
    """
    # Create an empty results dictionary
    results: dict[str, dict[str, Any]] = {}
    load_case_counter = 1  # Start from BG4001

    # Identify spans from bridge segments
    spans = _identify_spans(params.bridge_segments_array)
    # If no spans identified, fall back to single span covering entire bridge
    if not spans:
        spans = [
            Span(
                start_x=0.0,
                end_x=length_bridgedeck,
                length=length_bridgedeck,
                width=width_bridgedeck,
                bz1=width_bridgedeck / 3,  # Distribute width evenly across zones
                bz2=width_bridgedeck / 3,
                bz3=width_bridgedeck / 3,
                min_thickness=0.5,  # Default fallback thickness in meters
                span_index=1,
                num_segment_definitions=2,
            )
        ]

    # Calculate UDL values using helper function
    main_value, other_value, rest_value = calculate_theoretical_udl_values(params, length_bridgedeck, udl_value)
    
    # Calculate amount of notional lanes and lane width when starting on one side of the bridge deck
    max_lanes, lane_width = amount_of_notional_lanes(width_bridgedeck)  # Maximum number of lanes to consider and lane width

    # Loop through each span to generate polygons
    for span in spans:
        # Configuration A: leftmost lanes (BG8000 logic)
        y_positions_left = generate_theoretical_lane_positions_bg8000(
            width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2
        )
        if y_positions_left:
            # Generate lane load cases using helper
            lane_results, load_case_counter = _generate_lane_load_cases(
                span, y_positions_left, lane_width, max_lanes, main_value, other_value, CONFIGURATION_A, load_case_counter
            )
            results.update(lane_results)

            # Create rest polygon for areas not covered by lanes
            max_lane_width = max_lanes * lane_width
            if max_lane_width < width_bridgedeck:
                y_rest_bottom = y_positions_left[0] + max_lane_width - LANE_CENTER_OFFSET_FACTOR * lane_width
                y_rest_top = width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3
                case_name, case_data = _create_load_case_entry(
                    load_case_counter, span, y_rest_bottom, y_rest_top, rest_value, REST_AREA_TITLE_PREFIX, 1, CONFIGURATION_A
                )
                results[case_name] = case_data
                load_case_counter += 1

        # Configuration B: Rightmost lanes (BG9000 logic)
        y_positions_right = generate_theoretical_lane_positions_bg9000(
            width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2
        )
        if y_positions_right:
            # Generate lane load cases using helper
            lane_results, load_case_counter = _generate_lane_load_cases(
                span, y_positions_right, lane_width, max_lanes, main_value, other_value, CONFIGURATION_B, load_case_counter
            )
            results.update(lane_results)

            # Rest polygon for area below lanes
            max_lane_width = max_lanes * lane_width
            if max_lane_width < width_bridgedeck:
                y_rest_bottom = -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3
                y_rest_top = y_positions_right[0] - max_lane_width + LANE_CENTER_OFFSET_FACTOR * lane_width
                case_name, case_data = _create_load_case_entry(
                    load_case_counter, span, y_rest_bottom, y_rest_top, rest_value, REST_AREA_TITLE_PREFIX, 1, CONFIGURATION_B
                )
                results[case_name] = case_data
                load_case_counter += 1

        # Configuration C: center lanes with dynamic number of lanes on each side
        # Calculate how many lanes can fit on each side of the center
        left_lanes, right_lanes, _ = amount_of_notional_lanes_from_center(width_bridgedeck)
        total_lanes = 1 + left_lanes + right_lanes  # Center lane + left lanes + right lanes

        # Get the center position and adjust for zone offsets
        center_y = width_bridgedeck / 2 - width_firstsegment_zone3 - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2

        # Create center (main) lane
        center_y_min = center_y - lane_width / 2
        center_y_max = center_y + lane_width / 2
        case_name, case_data = _create_load_case_entry(
            load_case_counter, span, center_y_min, center_y_max, main_value, LANE_TITLE_PREFIX, 1, CONFIGURATION_C
        )
        results[case_name] = case_data
        load_case_counter += 1

        # Track RS numbers for other lanes
        rs_counter = 2

        # Create left side lanes
        for i in range(left_lanes):
            y_center = center_y - (i + 1) * lane_width
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            case_name, case_data = _create_load_case_entry(
                load_case_counter, span, y_min, y_max, other_value, LANE_TITLE_PREFIX, rs_counter, CONFIGURATION_C
            )
            results[case_name] = case_data
            rs_counter += 1
            load_case_counter += 1

        # Create right side lanes
        for i in range(right_lanes):
            y_center = center_y + (i + 1) * lane_width
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            case_name, case_data = _create_load_case_entry(
                load_case_counter, span, y_min, y_max, other_value, LANE_TITLE_PREFIX, rs_counter, CONFIGURATION_C
            )
            results[case_name] = case_data
            rs_counter += 1
            load_case_counter += 1

        # Create rest polygons for any remaining areas
        total_lanes_width = total_lanes * lane_width
        rest_counter = 1

        # Upper rest area (if exists)
        y_upper_rest_bottom = center_y + total_lanes_width / 2
        y_upper_rest_top = width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3
        if y_upper_rest_bottom < y_upper_rest_top:
            case_name, case_data = _create_load_case_entry(
                load_case_counter, span, y_upper_rest_bottom, y_upper_rest_top, rest_value, REST_AREA_TITLE_PREFIX, rest_counter, CONFIGURATION_C
            )
            results[case_name] = case_data
            rest_counter += 1
            load_case_counter += 1

        # Lower rest area (if exists)
        y_lower_rest_bottom = -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3
        y_lower_rest_top = center_y - total_lanes_width / 2
        if y_lower_rest_top > y_lower_rest_bottom:
            case_name, case_data = _create_load_case_entry(
                load_case_counter, span, y_lower_rest_bottom, y_lower_rest_top, rest_value, REST_AREA_TITLE_PREFIX, rest_counter, CONFIGURATION_C
            )
            results[case_name] = case_data
            load_case_counter += 1

    return results


def create_real_udl_traffic_loads(  # noqa: PLR0912, C901, PLR0915
    params: "BridgeParametrization",
    length_bridgedeck: float,
    udl_value: float = DEFAULT_UDL_VALUE,
) -> dict[str, dict[str, Any]]:
    """
    Create real uniform distributed load (UDL) traffic loads for the bridge.

    Creates individual load cases for each polygon with naming:
    - "RS 1", "RS 2", etc. for notional lanes (main and other)
    - "rest 1", "rest 2", etc. for remaining areas
    - "Conf. A", "Conf. B", "Conf. C" for configurations
    - "Span 1", "Span 2", etc. for span indices

    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param length_bridgedeck: Length of the bridge deck
    :type length_bridgedeck: float
    :param udl_value: Uniform distributed load value (default: DEFAULT_UDL_VALUE)
    :type udl_value: float
    :returns: Dict with keys BG4001, BG4002, etc., each containing a single polygon with load and title
    :rtype: dict[str, dict[str, Any]]
    """
    # Create an empty results dictionary
    results: dict[str, dict[str, Any]] = {}
    load_case_counter = 1  # Start from BG4001

    # Identify spans from bridge segments
    spans = _identify_spans(params.bridge_segments_array)
    # If no spans identified, fall back to single span covering entire bridge
    if not spans:
        # Fallback span - use minimal valid values since actual geometry comes from params
        fallback_width = 1.0  # Minimal valid width
        spans = [
            Span(
                start_x=0.0,
                end_x=length_bridgedeck,
                length=length_bridgedeck,
                width=fallback_width,
                bz1=fallback_width / 3,  # Distribute width evenly
                bz2=fallback_width / 3,
                bz3=fallback_width / 3,
                min_thickness=0.5,  # Default fallback thickness in meters
                span_index=1,
                num_segment_definitions=2,
            )
        ]

    # Calculate UDL values based on berekeningsniveau
    main_value, other_value, rest_value = calculate_real_udl_values(params, length_bridgedeck, udl_value)

    # Check if we have two road zones
    num_road_zones = get_number_of_road_zones(params)

    # Loop through each span to generate polygons
    for span in spans:
        if num_road_zones == 2:
            # Get widths and coordinates for both zones
            width_zone_1, width_zone_2 = get_widths_of_two_road_zones(params)
            y_top_zone_1, y_top_zone_2 = obtain_y_coordinates_two_road_zones(params)

            y_bottom_zone_1 = y_top_zone_1 - width_zone_1
            y_bottom_zone_2 = y_top_zone_2 - width_zone_2

            # Calculate lane width based on combined width
            max_lanes, lane_width = amount_of_notional_lanes(width_zone_1 + width_zone_2)

            # Configuration A: leftmost lanes (BG8000 logic) - lanes from bottom upward
            y_positions_left = generate_real_lane_positions_two_road_zones(params, "bg8000", lane_width)

            if y_positions_left:
                # Generate lane load cases using helper
                lane_results, load_case_counter = _generate_lane_load_cases(
                    span, y_positions_left, lane_width, max_lanes, main_value, other_value, CONFIGURATION_A, load_case_counter
                )
                results.update(lane_results)

                # Create rest polygons for uncovered areas in each zone
                # Determine which lanes belong to which zone and calculate rest areas
                lanes_covered_zone_1 = sum(1 for y in y_positions_left[:max_lanes] if y_bottom_zone_1 <= y <= y_top_zone_1)
                lanes_covered_zone_2 = sum(1 for y in y_positions_left[:max_lanes] if y_bottom_zone_2 <= y <= y_top_zone_2)

                rest_counter = 1

                # Rest area for zone 1
                zone_1_lanes = [y for y in y_positions_left[:max_lanes] if y_bottom_zone_1 <= y <= y_top_zone_1]
                if zone_1_lanes:
                    # Zone has lanes - create rest polygon above the highest lane if there's remaining space
                    if lanes_covered_zone_1 * lane_width < width_zone_1:
                        highest_lane_top = max(zone_1_lanes) + lane_width / 2
                        if highest_lane_top < y_top_zone_1:
                            rest_polygon_1 = [
                                (span.start_x, highest_lane_top, 0.0),
                                (span.end_x, highest_lane_top, 0.0),
                                (span.end_x, y_top_zone_1, 0.0),
                                (span.start_x, y_top_zone_1, 0.0),
                            ]
                            results[f"BG4{load_case_counter:03d}"] = {
                                "polygon": rest_polygon_1,
                                "load": rest_value,
                                "title": f"rest {rest_counter} - Conf. A - Span {span.span_index}",
                            }
                            rest_counter += 1
                            load_case_counter += 1
                else:
                    # Zone has NO lanes - create rest polygon for entire zone
                    rest_polygon_1 = [
                        (span.start_x, y_bottom_zone_1, 0.0),
                        (span.end_x, y_bottom_zone_1, 0.0),
                        (span.end_x, y_top_zone_1, 0.0),
                        (span.start_x, y_top_zone_1, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_polygon_1,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. A - Span {span.span_index}",
                    }
                    rest_counter += 1
                    load_case_counter += 1

                # Rest area for zone 2
                zone_2_lanes = [y for y in y_positions_left[:max_lanes] if y_bottom_zone_2 <= y <= y_top_zone_2]
                if zone_2_lanes:
                    # Zone has lanes - create rest polygon above the highest lane if there's remaining space
                    if lanes_covered_zone_2 * lane_width < width_zone_2:
                        highest_lane_top = max(zone_2_lanes) + lane_width / 2
                        if highest_lane_top < y_top_zone_2:
                            rest_polygon_2 = [
                                (span.start_x, highest_lane_top, 0.0),
                                (span.end_x, highest_lane_top, 0.0),
                                (span.end_x, y_top_zone_2, 0.0),
                                (span.start_x, y_top_zone_2, 0.0),
                            ]
                            results[f"BG4{load_case_counter:03d}"] = {
                                "polygon": rest_polygon_2,
                                "load": rest_value,
                                "title": f"rest {rest_counter} - Conf. A - Span {span.span_index}",
                            }
                            rest_counter += 1
                            load_case_counter += 1
                else:
                    # Zone has NO lanes - create rest polygon for entire zone
                    rest_polygon_2 = [
                        (span.start_x, y_bottom_zone_2, 0.0),
                        (span.end_x, y_bottom_zone_2, 0.0),
                        (span.end_x, y_top_zone_2, 0.0),
                        (span.start_x, y_top_zone_2, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_polygon_2,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. A - Span {span.span_index}",
                    }
                    load_case_counter += 1

            # Configuration B: rightmost lanes (BG9000 logic) - lanes from top downward
            y_positions_right = generate_real_lane_positions_two_road_zones(params, "bg9000", lane_width)

            if y_positions_right:
                # Generate lane load cases using helper
                lane_results, load_case_counter = _generate_lane_load_cases(
                    span, y_positions_right, lane_width, max_lanes, main_value, other_value, CONFIGURATION_B, load_case_counter
                )
                results.update(lane_results)

                # Create rest polygons for uncovered areas in each zone
                lanes_covered_zone_1 = sum(1 for y in y_positions_right[:max_lanes] if y_bottom_zone_1 <= y <= y_top_zone_1)
                lanes_covered_zone_2 = sum(1 for y in y_positions_right[:max_lanes] if y_bottom_zone_2 <= y <= y_top_zone_2)

                rest_counter = 1

                # Rest area for zone 1
                zone_1_lanes = [y for y in y_positions_right[:max_lanes] if y_bottom_zone_1 <= y <= y_top_zone_1]
                if zone_1_lanes:
                    # Zone has lanes - create rest polygon below the lowest lane if there's remaining space
                    if lanes_covered_zone_1 * lane_width < width_zone_1:
                        lowest_lane_bottom = min(zone_1_lanes) - lane_width / 2
                        if lowest_lane_bottom > y_bottom_zone_1:
                            rest_polygon_1 = [
                                (span.start_x, y_bottom_zone_1, 0.0),
                                (span.end_x, y_bottom_zone_1, 0.0),
                                (span.end_x, lowest_lane_bottom, 0.0),
                                (span.start_x, lowest_lane_bottom, 0.0),
                            ]
                            results[f"BG4{load_case_counter:03d}"] = {
                                "polygon": rest_polygon_1,
                                "load": rest_value,
                                "title": f"rest {rest_counter} - Conf. B - Span {span.span_index}",
                            }
                            rest_counter += 1
                            load_case_counter += 1
                else:
                    # Zone has NO lanes - create rest polygon for entire zone
                    rest_polygon_1 = [
                        (span.start_x, y_bottom_zone_1, 0.0),
                        (span.end_x, y_bottom_zone_1, 0.0),
                        (span.end_x, y_top_zone_1, 0.0),
                        (span.start_x, y_top_zone_1, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_polygon_1,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. B - Span {span.span_index}",
                    }
                    rest_counter += 1
                    load_case_counter += 1

                # Rest area for zone 2
                zone_2_lanes = [y for y in y_positions_right[:max_lanes] if y_bottom_zone_2 <= y <= y_top_zone_2]
                if zone_2_lanes:
                    # Zone has lanes - create rest polygon below the lowest lane if there's remaining space
                    if lanes_covered_zone_2 * lane_width < width_zone_2:
                        lowest_lane_bottom = min(zone_2_lanes) - lane_width / 2
                        if lowest_lane_bottom > y_bottom_zone_2:
                            rest_polygon_2 = [
                                (span.start_x, y_bottom_zone_2, 0.0),
                                (span.end_x, y_bottom_zone_2, 0.0),
                                (span.end_x, lowest_lane_bottom, 0.0),
                                (span.start_x, lowest_lane_bottom, 0.0),
                            ]
                            results[f"BG4{load_case_counter:03d}"] = {
                                "polygon": rest_polygon_2,
                                "load": rest_value,
                                "title": f"rest {rest_counter} - Conf. B - Span {span.span_index}",
                            }
                            rest_counter += 1
                            load_case_counter += 1
                else:
                    # Zone has NO lanes - create rest polygon for entire zone
                    rest_polygon_2 = [
                        (span.start_x, y_bottom_zone_2, 0.0),
                        (span.end_x, y_bottom_zone_2, 0.0),
                        (span.end_x, y_top_zone_2, 0.0),
                        (span.start_x, y_top_zone_2, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_polygon_2,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. B - Span {span.span_index}",
                    }
                    load_case_counter += 1

            # Configuration C: center lane positioning (BG10000 logic)
            y_positions_center = generate_real_lane_positions_two_road_zones(params, "bg10000", lane_width)

            if y_positions_center and len(y_positions_center) > 0:
                # First position is the main (center) lane
                y_center_main = y_positions_center[0]
                center_y_min = y_center_main - lane_width / 2
                center_y_max = y_center_main + lane_width / 2
                center_polygon = [
                    (span.start_x, center_y_min, 0.0),
                    (span.end_x, center_y_min, 0.0),
                    (span.end_x, center_y_max, 0.0),
                    (span.start_x, center_y_max, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": center_polygon,
                    "load": main_value,
                    "title": f"RS 1 - Conf. C - Span {span.span_index}",
                }
                load_case_counter += 1

                # Track RS numbers for other lanes
                rs_counter = 2

                # Create other lanes (adjacent lanes if they exist)
                for y_center in y_positions_center[1:max_lanes]:
                    y_min = y_center - lane_width / 2
                    y_max = y_center + lane_width / 2
                    lane_polygon = [
                        (span.start_x, y_min, 0.0),
                        (span.end_x, y_min, 0.0),
                        (span.end_x, y_max, 0.0),
                        (span.start_x, y_max, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": other_value,
                        "title": f"RS {rs_counter} - Conf. C - Span {span.span_index}",
                    }
                    rs_counter += 1
                    load_case_counter += 1

                # Create rest polygons for remaining areas in each zone
                lanes_used = y_positions_center[:max_lanes]
                lanes_in_zone_1 = [y for y in lanes_used if y_bottom_zone_1 <= y <= y_top_zone_1]
                lanes_in_zone_2 = [y for y in lanes_used if y_bottom_zone_2 <= y <= y_top_zone_2]

                rest_counter = 1

                # Rest areas for zone 1
                if lanes_in_zone_1:
                    # Zone has lanes - create rest polygons for uncovered areas above and below lanes
                    min_y_covered = min(lanes_in_zone_1) - lane_width / 2
                    max_y_covered = max(lanes_in_zone_1) + lane_width / 2

                    # Lower rest area in zone 1
                    if min_y_covered > y_bottom_zone_1:
                        rest_lower = [
                            (span.start_x, y_bottom_zone_1, 0.0),
                            (span.end_x, y_bottom_zone_1, 0.0),
                            (span.end_x, min_y_covered, 0.0),
                            (span.start_x, min_y_covered, 0.0),
                        ]
                        results[f"BG4{load_case_counter:03d}"] = {
                            "polygon": rest_lower,
                            "load": rest_value,
                            "title": f"rest {rest_counter} - Conf. C - Span {span.span_index}",
                        }
                        rest_counter += 1
                        load_case_counter += 1

                    # Upper rest area in zone 1
                    if max_y_covered < y_top_zone_1:
                        rest_upper = [
                            (span.start_x, max_y_covered, 0.0),
                            (span.end_x, max_y_covered, 0.0),
                            (span.end_x, y_top_zone_1, 0.0),
                            (span.start_x, y_top_zone_1, 0.0),
                        ]
                        results[f"BG4{load_case_counter:03d}"] = {
                            "polygon": rest_upper,
                            "load": rest_value,
                            "title": f"rest {rest_counter} - Conf. C - Span {span.span_index}",
                        }
                        rest_counter += 1
                        load_case_counter += 1
                else:
                    # Zone has NO lanes - create rest polygon for entire zone
                    rest_polygon_1 = [
                        (span.start_x, y_bottom_zone_1, 0.0),
                        (span.end_x, y_bottom_zone_1, 0.0),
                        (span.end_x, y_top_zone_1, 0.0),
                        (span.start_x, y_top_zone_1, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_polygon_1,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. C - Span {span.span_index}",
                    }
                    rest_counter += 1
                    load_case_counter += 1

                # Rest areas for zone 2
                if lanes_in_zone_2:
                    # Zone has lanes - create rest polygons for uncovered areas above and below lanes
                    min_y_covered = min(lanes_in_zone_2) - lane_width / 2
                    max_y_covered = max(lanes_in_zone_2) + lane_width / 2

                    # Lower rest area in zone 2
                    if min_y_covered > y_bottom_zone_2:
                        rest_lower = [
                            (span.start_x, y_bottom_zone_2, 0.0),
                            (span.end_x, y_bottom_zone_2, 0.0),
                            (span.end_x, min_y_covered, 0.0),
                            (span.start_x, min_y_covered, 0.0),
                        ]
                        results[f"BG4{load_case_counter:03d}"] = {
                            "polygon": rest_lower,
                            "load": rest_value,
                            "title": f"rest {rest_counter} - Conf. C - Span {span.span_index}",
                        }
                        rest_counter += 1
                        load_case_counter += 1

                    # Upper rest area in zone 2
                    if max_y_covered < y_top_zone_2:
                        rest_upper = [
                            (span.start_x, max_y_covered, 0.0),
                            (span.end_x, max_y_covered, 0.0),
                            (span.end_x, y_top_zone_2, 0.0),
                            (span.start_x, y_top_zone_2, 0.0),
                        ]
                        results[f"BG4{load_case_counter:03d}"] = {
                            "polygon": rest_upper,
                            "load": rest_value,
                            "title": f"rest {rest_counter} - Conf. C - Span {span.span_index}",
                        }
                        rest_counter += 1
                        load_case_counter += 1
                else:
                    # Zone has NO lanes - create rest polygon for entire zone
                    rest_polygon_2 = [
                        (span.start_x, y_bottom_zone_2, 0.0),
                        (span.end_x, y_bottom_zone_2, 0.0),
                        (span.end_x, y_top_zone_2, 0.0),
                        (span.start_x, y_top_zone_2, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_polygon_2,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. C - Span {span.span_index}",
                    }
                    load_case_counter += 1

        else:
            # Single road zone - original logic
            y_top, width_road = obtain_y_coordinates_road(params)
            y_bottom = y_top - width_road
            max_lanes, lane_width = amount_of_notional_lanes(width_road)

            # Configuration A: leftmost lanes (BG8000 logic)
            y_positions_left = generate_real_lane_positions_bg8000(params, lane_width)

            if y_positions_left:
                # Generate lane load cases using helper
                lane_results, load_case_counter = _generate_lane_load_cases(
                    span, y_positions_left, lane_width, max_lanes, main_value, other_value, CONFIGURATION_A, load_case_counter
                )
                results.update(lane_results)

                # Create rest polygon for areas not covered by lanes
                max_lane_width = max_lanes * lane_width
                if max_lane_width < width_road:
                    y_rest_bottom = y_bottom + max_lane_width
                    case_name, case_data = _create_load_case_entry(
                        load_case_counter, span, y_rest_bottom, y_top, rest_value, REST_AREA_TITLE_PREFIX, 1, CONFIGURATION_A
                    )
                    results[case_name] = case_data
                    load_case_counter += 1

            # Configuration B: Rightmost lanes (BG9000 logic)
            y_positions_right = generate_real_lane_positions_bg9000(params, lane_width)

            if y_positions_right:
                # Generate lane load cases using helper
                lane_results, load_case_counter = _generate_lane_load_cases(
                    span, y_positions_right, lane_width, max_lanes, main_value, other_value, CONFIGURATION_B, load_case_counter
                )
                results.update(lane_results)

                # Rest polygon for area below lanes
                max_lane_width = max_lanes * lane_width
                if max_lane_width < width_road:
                    y_rest_bottom = y_top - max_lane_width
                    case_name, case_data = _create_load_case_entry(
                        load_case_counter, span, y_rest_bottom, y_bottom, rest_value, REST_AREA_TITLE_PREFIX, 1, CONFIGURATION_B
                    )
                    results[case_name] = case_data
                    load_case_counter += 1

            # Configuration C: center lanes with dynamic number of lanes on each side
            left_lanes, right_lanes, _ = amount_of_notional_lanes_from_center(width_road)
            total_lanes = 1 + left_lanes + right_lanes

            center_y = (y_top + y_bottom) / 2

            # Create center (main) lane
            center_y_min = center_y - lane_width / 2
            center_y_max = center_y + lane_width / 2
            case_name, case_data = _create_load_case_entry(
                load_case_counter, span, center_y_min, center_y_max, main_value, LANE_TITLE_PREFIX, 1, CONFIGURATION_C
            )
            results[case_name] = case_data
            load_case_counter += 1

            # Track RS numbers for other lanes
            rs_counter = 2

            # Create left side lanes
            for i in range(left_lanes):
                y_center = center_y - (i + 1) * lane_width
                y_min = y_center - lane_width / 2
                y_max = y_center + lane_width / 2
                case_name, case_data = _create_load_case_entry(
                    load_case_counter, span, y_min, y_max, other_value, LANE_TITLE_PREFIX, rs_counter, CONFIGURATION_C
                )
                results[case_name] = case_data
                rs_counter += 1
                load_case_counter += 1

            # Create right side lanes
            for i in range(right_lanes):
                y_center = center_y + (i + 1) * lane_width
                y_min = y_center - lane_width / 2
                y_max = y_center + lane_width / 2
                case_name, case_data = _create_load_case_entry(
                    load_case_counter, span, y_min, y_max, other_value, LANE_TITLE_PREFIX, rs_counter, CONFIGURATION_C
                )
                results[case_name] = case_data
                rs_counter += 1
                load_case_counter += 1

            # Create rest polygons for any remaining areas
            total_lanes_width = total_lanes * lane_width
            rest_counter = 1

            # Upper rest area (if exists)
            y_upper_rest_bottom = center_y + total_lanes_width / 2
            if y_upper_rest_bottom < y_top:
                case_name, case_data = _create_load_case_entry(
                    load_case_counter, span, y_upper_rest_bottom, y_top, rest_value, REST_AREA_TITLE_PREFIX, rest_counter, CONFIGURATION_C
                )
                results[case_name] = case_data
                rest_counter += 1
                load_case_counter += 1

            # Lower rest area (if exists)
            y_lower_rest_top = center_y - total_lanes_width / 2
            if y_lower_rest_top > y_bottom:
                case_name, case_data = _create_load_case_entry(
                    load_case_counter, span, y_bottom, y_lower_rest_top, rest_value, REST_AREA_TITLE_PREFIX, rest_counter, CONFIGURATION_C
                )
                results[case_name] = case_data
                load_case_counter += 1

    return results
