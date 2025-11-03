"""
UDL (Uniformly Distributed Load) traffic load generators.

This module provides functions for generating UDL traffic loads for both
theoretical and real lane distributions on bridge decks.

All functions are independent of the VIKTOR SDK and suitable for use in the core logic layer.
"""

from typing import TYPE_CHECKING, Any

from src.combinations.load_factors import get_alpha_q_nen_en_1991_2, get_alpha_trend_nen_8701, get_psi_nen_8701
from src.integrations.scia_integration.constants.geometry import (
    DEFAULT_LANE_WIDTH,
    LANE_CENTER_OFFSET_FACTOR,
)
from src.integrations.scia_integration.constants.loads import (
    DEFAULT_UDL_VALUE,
    NOBS_DEFAULT,
    UDL_OTHER_LANE_VALUE,
    UDL_REST_AREA_VALUE,
)
from src.integrations.scia_integration.load_system.lane_calculations import (
    amount_of_notional_lanes,
    amount_of_notional_lanes_from_center,
    get_reference_period,
)
from src.integrations.scia_integration.load_system.load_value_calculators import (
    calculate_real_udl_values,
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
# UNIFORMLY DISTRIBUTED TRAFFIC LOADS (UDL) FOR MAIN NOTIONAL LANES
# ========================================================================


def create_theoretical_udl_traffic_loads(  # noqa: PLR0912, PLR0913, C901, PLR0915
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

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factors = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)
    # Obtain load values
    main_value = udl_value * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
    other_value = UDL_OTHER_LANE_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
    rest_value = UDL_REST_AREA_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
    # Calculate amount of notional lanes and lane width when starting on one side of the bridge deck
    max_lanes, lane_width = amount_of_notional_lanes(width_bridgedeck)  # Maximum number of lanes to consider and lane width

    # Configuration A: leftmost lanes (BG8000 logic)
    y_positions_left = generate_theoretical_lane_positions_bg8000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_left:
        # Create lane polygons for up to max_lanes, starting from leftmost
        for lane_idx, y_center in enumerate(y_positions_left[:max_lanes]):
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]

            # First lane is "main", others are "other"
            rs_number = lane_idx + 1
            if lane_idx == 0:
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": lane_polygon,
                    "load": main_value,
                    "title": f"RS {rs_number} - Conf. A",
                }
            else:
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": lane_polygon,
                    "load": other_value,
                    "title": f"RS {rs_number} - Conf. A",
                }
            load_case_counter += 1

        # Create rest polygon for areas not covered by lanes
        max_lane_width = max_lanes * lane_width
        if max_lane_width < width_bridgedeck:
            rest_polygon = [
                (0.0, y_positions_left[0] + max_lane_width - LANE_CENTER_OFFSET_FACTOR * lane_width, 0.0),
                (length_bridgedeck, y_positions_left[0] + max_lane_width - LANE_CENTER_OFFSET_FACTOR * lane_width, 0.0),
                (length_bridgedeck, width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (0.0, width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            ]
            results[f"BG4{load_case_counter:03d}"] = {
                "polygon": rest_polygon,
                "load": rest_value,
                "title": "rest 1 - Conf. A",
            }
            load_case_counter += 1

    # Configuration B: Rightmost lanes (BG9000 logic)
    y_positions_right = generate_theoretical_lane_positions_bg9000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_right:
        for lane_idx, y_center in enumerate(y_positions_right[:max_lanes]):
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]

            rs_number = lane_idx + 1
            if lane_idx == 0:
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": lane_polygon,
                    "load": main_value,
                    "title": f"RS {rs_number} - Conf. B",
                }
            else:
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": lane_polygon,
                    "load": other_value,
                    "title": f"RS {rs_number} - Conf. B",
                }
            load_case_counter += 1

        # Rest polygon for area below lanes
        max_lane_width = max_lanes * lane_width
        if max_lane_width < width_bridgedeck:
            rest_polygon = [
                (0.0, -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, y_positions_right[0] - max_lane_width + LANE_CENTER_OFFSET_FACTOR * lane_width, 0.0),
                (0.0, y_positions_right[0] - max_lane_width + LANE_CENTER_OFFSET_FACTOR * lane_width, 0.0),
            ]
            results[f"BG4{load_case_counter:03d}"] = {
                "polygon": rest_polygon,
                "load": rest_value,
                "title": "rest 1 - Conf. B",
            }
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
    center_polygon = [
        (0.0, center_y_min, 0.0),
        (length_bridgedeck, center_y_min, 0.0),
        (length_bridgedeck, center_y_max, 0.0),
        (0.0, center_y_max, 0.0),
    ]
    results[f"BG4{load_case_counter:03d}"] = {
        "polygon": center_polygon,
        "load": main_value,
        "title": "RS 1 - Conf. C",
    }
    load_case_counter += 1

    # Track RS numbers for other lanes
    rs_counter = 2

    # Create left side lanes
    for i in range(left_lanes):
        y_center = center_y - (i + 1) * lane_width
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        lane_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        results[f"BG4{load_case_counter:03d}"] = {
            "polygon": lane_polygon,
            "load": other_value,
            "title": f"RS {rs_counter} - Conf. C",
        }
        rs_counter += 1
        load_case_counter += 1

    # Create right side lanes
    for i in range(right_lanes):
        y_center = center_y + (i + 1) * lane_width
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        lane_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        results[f"BG4{load_case_counter:03d}"] = {
            "polygon": lane_polygon,
            "load": other_value,
            "title": f"RS {rs_counter} - Conf. C",
        }
        rs_counter += 1
        load_case_counter += 1

    # Create rest polygons for any remaining areas
    total_lanes_width = total_lanes * lane_width
    rest_counter = 1

    # Upper rest area (if exists)
    if center_y + total_lanes_width / 2 < width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3:
        upper_rest = [
            (0.0, center_y + total_lanes_width / 2, 0.0),
            (length_bridgedeck, center_y + total_lanes_width / 2, 0.0),
            (length_bridgedeck, width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (0.0, width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
        ]
        results[f"BG4{load_case_counter:03d}"] = {
            "polygon": upper_rest,
            "load": rest_value,
            "title": f"rest {rest_counter} - Conf. C",
        }
        rest_counter += 1
        load_case_counter += 1

    # Lower rest area (if exists)
    if center_y - total_lanes_width / 2 > -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3:
        lower_rest = [
            (0.0, -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (length_bridgedeck, -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (length_bridgedeck, center_y - total_lanes_width / 2, 0.0),
            (0.0, center_y - total_lanes_width / 2, 0.0),
        ]
        results[f"BG4{load_case_counter:03d}"] = {
            "polygon": lower_rest,
            "load": rest_value,
            "title": f"rest {rest_counter} - Conf. C",
        }
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

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    # Calculate UDL values based on berekeningsniveau
    main_value, other_value, rest_value = calculate_real_udl_values(params, length_bridgedeck, udl_value, psi_nen_8701_factor, alpha_trend_factor)

    # Check if we have two road zones
    num_road_zones = get_number_of_road_zones(params)

    if num_road_zones == 2:
        # Get widths and coordinates for both zones
        width_zone_1, width_zone_2 = get_widths_of_two_road_zones(params)
        y_top_zone_1, y_top_zone_2 = obtain_y_coordinates_two_road_zones(params)

        y_bottom_zone_1 = y_top_zone_1 - width_zone_1
        y_bottom_zone_2 = y_top_zone_2 - width_zone_2

        # Calculate lane width based on combined width
        max_lanes, lane_width = amount_of_notional_lanes(width_zone_1 + width_zone_2)

        # Configuration A: leftmost lanes (BG8000 logic) - lanes from bottom upward
        y_positions_left = generate_real_lane_positions_two_road_zones(params, "bg8000", lane_width=3)

        if y_positions_left:
            # Create lane polygons for up to max_lanes
            for lane_idx, y_center in enumerate(y_positions_left[:max_lanes]):
                y_min = y_center - lane_width / 2
                y_max = y_center + lane_width / 2
                lane_polygon = [
                    (0.0, y_min, 0.0),
                    (length_bridgedeck, y_min, 0.0),
                    (length_bridgedeck, y_max, 0.0),
                    (0.0, y_max, 0.0),
                ]

                # First lane is "main", others are "other"
                rs_number = lane_idx + 1
                if lane_idx == 0:
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": main_value,
                        "title": f"RS {rs_number} - Conf. A",
                    }
                else:
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": other_value,
                        "title": f"RS {rs_number} - Conf. A",
                    }
                load_case_counter += 1

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
                            (0.0, highest_lane_top, 0.0),
                            (length_bridgedeck, highest_lane_top, 0.0),
                            (length_bridgedeck, y_top_zone_1, 0.0),
                            (0.0, y_top_zone_1, 0.0),
                        ]
                        results[f"BG4{load_case_counter:03d}"] = {
                            "polygon": rest_polygon_1,
                            "load": rest_value,
                            "title": f"rest {rest_counter} - Conf. A",
                        }
                        rest_counter += 1
                        load_case_counter += 1
            else:
                # Zone has NO lanes - create rest polygon for entire zone
                rest_polygon_1 = [
                    (0.0, y_bottom_zone_1, 0.0),
                    (length_bridgedeck, y_bottom_zone_1, 0.0),
                    (length_bridgedeck, y_top_zone_1, 0.0),
                    (0.0, y_top_zone_1, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": rest_polygon_1,
                    "load": rest_value,
                    "title": f"rest {rest_counter} - Conf. A",
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
                            (0.0, highest_lane_top, 0.0),
                            (length_bridgedeck, highest_lane_top, 0.0),
                            (length_bridgedeck, y_top_zone_2, 0.0),
                            (0.0, y_top_zone_2, 0.0),
                        ]
                        results[f"BG4{load_case_counter:03d}"] = {
                            "polygon": rest_polygon_2,
                            "load": rest_value,
                            "title": f"rest {rest_counter} - Conf. A",
                        }
                        rest_counter += 1
                        load_case_counter += 1
            else:
                # Zone has NO lanes - create rest polygon for entire zone
                rest_polygon_2 = [
                    (0.0, y_bottom_zone_2, 0.0),
                    (length_bridgedeck, y_bottom_zone_2, 0.0),
                    (length_bridgedeck, y_top_zone_2, 0.0),
                    (0.0, y_top_zone_2, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": rest_polygon_2,
                    "load": rest_value,
                    "title": f"rest {rest_counter} - Conf. A",
                }
                load_case_counter += 1

        # Configuration B: rightmost lanes (BG9000 logic) - lanes from top downward
        y_positions_right = generate_real_lane_positions_two_road_zones(params, "bg9000", lane_width)

        if y_positions_right:
            for lane_idx, y_center in enumerate(y_positions_right[:max_lanes]):
                y_min = y_center - lane_width / 2
                y_max = y_center + lane_width / 2
                lane_polygon = [
                    (0.0, y_min, 0.0),
                    (length_bridgedeck, y_min, 0.0),
                    (length_bridgedeck, y_max, 0.0),
                    (0.0, y_max, 0.0),
                ]

                rs_number = lane_idx + 1
                if lane_idx == 0:
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": main_value,
                        "title": f"RS {rs_number} - Conf. B",
                    }
                else:
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": other_value,
                        "title": f"RS {rs_number} - Conf. B",
                    }
                load_case_counter += 1

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
                            (0.0, y_bottom_zone_1, 0.0),
                            (length_bridgedeck, y_bottom_zone_1, 0.0),
                            (length_bridgedeck, lowest_lane_bottom, 0.0),
                            (0.0, lowest_lane_bottom, 0.0),
                        ]
                        results[f"BG4{load_case_counter:03d}"] = {
                            "polygon": rest_polygon_1,
                            "load": rest_value,
                            "title": f"rest {rest_counter} - Conf. B",
                        }
                        rest_counter += 1
                        load_case_counter += 1
            else:
                # Zone has NO lanes - create rest polygon for entire zone
                rest_polygon_1 = [
                    (0.0, y_bottom_zone_1, 0.0),
                    (length_bridgedeck, y_bottom_zone_1, 0.0),
                    (length_bridgedeck, y_top_zone_1, 0.0),
                    (0.0, y_top_zone_1, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": rest_polygon_1,
                    "load": rest_value,
                    "title": f"rest {rest_counter} - Conf. B",
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
                            (0.0, y_bottom_zone_2, 0.0),
                            (length_bridgedeck, y_bottom_zone_2, 0.0),
                            (length_bridgedeck, lowest_lane_bottom, 0.0),
                            (0.0, lowest_lane_bottom, 0.0),
                        ]
                        results[f"BG4{load_case_counter:03d}"] = {
                            "polygon": rest_polygon_2,
                            "load": rest_value,
                            "title": f"rest {rest_counter} - Conf. B",
                        }
                        rest_counter += 1
                        load_case_counter += 1
            else:
                # Zone has NO lanes - create rest polygon for entire zone
                rest_polygon_2 = [
                    (0.0, y_bottom_zone_2, 0.0),
                    (length_bridgedeck, y_bottom_zone_2, 0.0),
                    (length_bridgedeck, y_top_zone_2, 0.0),
                    (0.0, y_top_zone_2, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": rest_polygon_2,
                    "load": rest_value,
                    "title": f"rest {rest_counter} - Conf. B",
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
                (0.0, center_y_min, 0.0),
                (length_bridgedeck, center_y_min, 0.0),
                (length_bridgedeck, center_y_max, 0.0),
                (0.0, center_y_max, 0.0),
            ]
            results[f"BG4{load_case_counter:03d}"] = {
                "polygon": center_polygon,
                "load": main_value,
                "title": "RS 1 - Conf. C",
            }
            load_case_counter += 1

            # Track RS numbers for other lanes
            rs_counter = 2

            # Create other lanes (adjacent lanes if they exist)
            for y_center in y_positions_center[1:max_lanes]:
                y_min = y_center - lane_width / 2
                y_max = y_center + lane_width / 2
                lane_polygon = [
                    (0.0, y_min, 0.0),
                    (length_bridgedeck, y_min, 0.0),
                    (length_bridgedeck, y_max, 0.0),
                    (0.0, y_max, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": lane_polygon,
                    "load": other_value,
                    "title": f"RS {rs_counter} - Conf. C",
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
                        (0.0, y_bottom_zone_1, 0.0),
                        (length_bridgedeck, y_bottom_zone_1, 0.0),
                        (length_bridgedeck, min_y_covered, 0.0),
                        (0.0, min_y_covered, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_lower,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. C",
                    }
                    rest_counter += 1
                    load_case_counter += 1

                # Upper rest area in zone 1
                if max_y_covered < y_top_zone_1:
                    rest_upper = [
                        (0.0, max_y_covered, 0.0),
                        (length_bridgedeck, max_y_covered, 0.0),
                        (length_bridgedeck, y_top_zone_1, 0.0),
                        (0.0, y_top_zone_1, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_upper,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. C",
                    }
                    rest_counter += 1
                    load_case_counter += 1
            else:
                # Zone has NO lanes - create rest polygon for entire zone
                rest_polygon_1 = [
                    (0.0, y_bottom_zone_1, 0.0),
                    (length_bridgedeck, y_bottom_zone_1, 0.0),
                    (length_bridgedeck, y_top_zone_1, 0.0),
                    (0.0, y_top_zone_1, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": rest_polygon_1,
                    "load": rest_value,
                    "title": f"rest {rest_counter} - Conf. C",
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
                        (0.0, y_bottom_zone_2, 0.0),
                        (length_bridgedeck, y_bottom_zone_2, 0.0),
                        (length_bridgedeck, min_y_covered, 0.0),
                        (0.0, min_y_covered, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_lower,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. C",
                    }
                    rest_counter += 1
                    load_case_counter += 1

                # Upper rest area in zone 2
                if max_y_covered < y_top_zone_2:
                    rest_upper = [
                        (0.0, max_y_covered, 0.0),
                        (length_bridgedeck, max_y_covered, 0.0),
                        (length_bridgedeck, y_top_zone_2, 0.0),
                        (0.0, y_top_zone_2, 0.0),
                    ]
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": rest_upper,
                        "load": rest_value,
                        "title": f"rest {rest_counter} - Conf. C",
                    }
                    rest_counter += 1
                    load_case_counter += 1
            else:
                # Zone has NO lanes - create rest polygon for entire zone
                rest_polygon_2 = [
                    (0.0, y_bottom_zone_2, 0.0),
                    (length_bridgedeck, y_bottom_zone_2, 0.0),
                    (length_bridgedeck, y_top_zone_2, 0.0),
                    (0.0, y_top_zone_2, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": rest_polygon_2,
                    "load": rest_value,
                    "title": f"rest {rest_counter} - Conf. C",
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
            for lane_idx, y_center in enumerate(y_positions_left[:max_lanes]):
                y_min = y_center - lane_width / 2
                y_max = y_center + lane_width / 2
                lane_polygon = [
                    (0.0, y_min, 0.0),
                    (length_bridgedeck, y_min, 0.0),
                    (length_bridgedeck, y_max, 0.0),
                    (0.0, y_max, 0.0),
                ]

                rs_number = lane_idx + 1
                if lane_idx == 0:
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": main_value,
                        "title": f"RS {rs_number} - Conf. A",
                    }
                else:
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": other_value,
                        "title": f"RS {rs_number} - Conf. A",
                    }
                load_case_counter += 1

            # Create rest polygon for areas not covered by lanes
            max_lane_width = max_lanes * lane_width
            if max_lane_width < width_road:
                rest_polygon = [
                    (0.0, y_top, 0.0),
                    (length_bridgedeck, y_top, 0.0),
                    (length_bridgedeck, y_bottom + max_lane_width, 0.0),
                    (0.0, y_bottom + max_lane_width, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": rest_polygon,
                    "load": rest_value,
                    "title": "rest 1 - Conf. A",
                }
                load_case_counter += 1

        # Configuration B: Rightmost lanes (BG9000 logic)
        y_positions_right = generate_real_lane_positions_bg9000(params, lane_width)

        if y_positions_right:
            for lane_idx, y_center in enumerate(y_positions_right[:max_lanes]):
                y_min = y_center - lane_width / 2
                y_max = y_center + lane_width / 2
                lane_polygon = [
                    (0.0, y_min, 0.0),
                    (length_bridgedeck, y_min, 0.0),
                    (length_bridgedeck, y_max, 0.0),
                    (0.0, y_max, 0.0),
                ]

                rs_number = lane_idx + 1
                if lane_idx == 0:
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": main_value,
                        "title": f"RS {rs_number} - Conf. B",
                    }
                else:
                    results[f"BG4{load_case_counter:03d}"] = {
                        "polygon": lane_polygon,
                        "load": other_value,
                        "title": f"RS {rs_number} - Conf. B",
                    }
                load_case_counter += 1

            # Rest polygon for area below lanes
            max_lane_width = max_lanes * lane_width
            if max_lane_width < width_road:
                rest_polygon = [
                    (0.0, y_top - max_lane_width, 0.0),
                    (length_bridgedeck, y_top - max_lane_width, 0.0),
                    (length_bridgedeck, y_bottom, 0.0),
                    (0.0, y_bottom, 0.0),
                ]
                results[f"BG4{load_case_counter:03d}"] = {
                    "polygon": rest_polygon,
                    "load": rest_value,
                    "title": "rest 1 - Conf. B",
                }
                load_case_counter += 1

        # Configuration C: center lanes with dynamic number of lanes on each side
        left_lanes, right_lanes, _ = amount_of_notional_lanes_from_center(width_road)
        total_lanes = 1 + left_lanes + right_lanes

        center_y = (y_top + y_bottom) / 2

        # Create center (main) lane
        center_y_min = center_y - lane_width / 2
        center_y_max = center_y + lane_width / 2
        center_polygon = [
            (0.0, center_y_min, 0.0),
            (length_bridgedeck, center_y_min, 0.0),
            (length_bridgedeck, center_y_max, 0.0),
            (0.0, center_y_max, 0.0),
        ]
        results[f"BG4{load_case_counter:03d}"] = {
            "polygon": center_polygon,
            "load": main_value,
            "title": "RS 1 - Conf. C",
        }
        load_case_counter += 1

        # Track RS numbers for other lanes
        rs_counter = 2

        # Create left side lanes
        for i in range(left_lanes):
            y_center = center_y - (i + 1) * lane_width
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]
            results[f"BG4{load_case_counter:03d}"] = {
                "polygon": lane_polygon,
                "load": other_value,
                "title": f"RS {rs_counter} - Conf. C",
            }
            rs_counter += 1
            load_case_counter += 1

        # Create right side lanes
        for i in range(right_lanes):
            y_center = center_y + (i + 1) * lane_width
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]
            results[f"BG4{load_case_counter:03d}"] = {
                "polygon": lane_polygon,
                "load": other_value,
                "title": f"RS {rs_counter} - Conf. C",
            }
            rs_counter += 1
            load_case_counter += 1

        # Create rest polygons for any remaining areas
        total_lanes_width = total_lanes * lane_width
        rest_counter = 1

        # Upper rest area (if exists)
        if center_y + total_lanes_width / 2 < y_top:
            upper_rest = [
                (0.0, center_y + total_lanes_width / 2, 0.0),
                (length_bridgedeck, center_y + total_lanes_width / 2, 0.0),
                (length_bridgedeck, y_top, 0.0),
                (0.0, y_top, 0.0),
            ]
            results[f"BG4{load_case_counter:03d}"] = {
                "polygon": upper_rest,
                "load": rest_value,
                "title": f"rest {rest_counter} - Conf. C",
            }
            rest_counter += 1
            load_case_counter += 1

        # Lower rest area (if exists)
        if center_y - total_lanes_width / 2 > y_bottom:
            lower_rest = [
                (0.0, y_bottom, 0.0),
                (length_bridgedeck, y_bottom, 0.0),
                (length_bridgedeck, center_y - total_lanes_width / 2, 0.0),
                (0.0, center_y - total_lanes_width / 2, 0.0),
            ]
            results[f"BG4{load_case_counter:03d}"] = {
                "polygon": lower_rest,
                "load": rest_value,
                "title": f"rest {rest_counter} - Conf. C",
            }
            load_case_counter += 1

    return results
