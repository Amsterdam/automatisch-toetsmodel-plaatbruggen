"""
Helper functions for load case logic and manipulation.

This module provides utility functions for working with load cases in the bridge analysis context.

All functions are independent of the VIKTOR SDK and suitable for use in the core logic layer.
"""

from typing import TYPE_CHECKING, Any

# Type alias to avoid importing from app layer
from app.bridge.parametrization import BridgeParametrization
from src.combinations.load_factors import get_alpha_q_nen_en_1991_2, get_alpha_trend_nen_8701, get_psi_nen_8701
from src.common.materials import get_material_densities
from src.geometry.load_zone_geometry import calculate_zone_geometry_properties, get_bridge_geom_data, get_load_zones_data_from_params
from src.geometry.model_creator import LoadZoneGeometryData


def get_reference_period(params: BridgeParametrization) -> int:
    """
    Return the reference period (in years) based on the veiligheidsniveau input.

    :param veiligheidsniveau: The value of the veiligheidsniveau field from parametrization.py
    :type veiligheidsniveau: str
    :returns: Reference period in years (30 or 15)
    :rtype: int
    """
    if params["design_code"] == "NEN 8700 afkeur":
        return 15
    return 30


if TYPE_CHECKING:
    from .scia_model_interface import SciaModelBuilder

# ========================================================================
# UNIFORMLY DISTRIBUTED TRAFFIC LOADS (UDL) FOR MAIN NOTIONAL LANES
# ========================================================================


def create_theoretical_udl_traffic_loads(  # noqa: PLR0912, PLR0913, C901
    params: BridgeParametrization,
    length_bridgedeck: float,
    width_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    udl_value: float = 9000.0,
) -> dict[str, dict[str, Any]]:
    """
    Create UDLs for all notional lanes and remaining areas.

    Creates three categories of load polygons:
    - "main": First notional lane (9 kN/m²)
    - "other": Additional notional lanes (2.5 kN/m²)
    - "rest": Remaining bridge deck areas (2.5 kN/m²)

    :param length_bridgedeck: Bridge length in meters
    :param width_bridgedeck: Bridge width in meters
    :param width_firstsegment_zone3: Zone 3 width (for lane offset)
    :param width_firstsegment_zone2: Zone 2 width (for lane offset)
    :param lane_width: Lane width in meters (default 3.0)
    :param udl_value: UDL value for main lane in N/m² (default 9000.0)
    :returns: Dict with keys BG4001, BG4002, BG4003, each containing lane polygons and load values
    """
    # Create an empty results dictionary
    results = {}

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factors = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=20000)
    # Obtain load values
    main_value = udl_value * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
    other_value = 2500.0 * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
    rest_value = 2500.0 * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
    # Calculate amount of notional lanes and lane width when starting on one side of the bridge deck
    max_lanes, lane_width = amount_of_notional_lanes(width_bridgedeck)  # Maximum number of lanes to consider and lane width

    # BG4001: leftmost lanes (BG8000 logic)
    y_positions_left = generate_theoretical_lane_positions_bg8000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_left:
        load_polygons: dict[str, list[dict[str, list[tuple[float, float, float]] | float]]] = {"main": [], "other": [], "rest": []}

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
            if lane_idx == 0:
                load_polygons["main"].append({"polygon": lane_polygon, "load": main_value})
            else:
                load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

        # Create rest polygon for areas not covered by lanes
        max_lane_width = max_lanes * lane_width
        if max_lane_width < width_bridgedeck:
            rest_polygon = [
                (0.0, y_positions_left[0] + max_lane_width - 0.5 * lane_width, 0.0),
                (length_bridgedeck, y_positions_left[0] + max_lane_width - 0.5 * lane_width, 0.0),
                (length_bridgedeck, width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (0.0, width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            ]
            load_polygons["rest"].append({"polygon": rest_polygon, "load": rest_value})

        results["BG4001"] = load_polygons

    # BG4002: Rightmost lanes (BG9000 logic)
    y_positions_right = generate_theoretical_lane_positions_bg9000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_right:
        load_polygons = {"main": [], "other": [], "rest": []}

        for lane_idx, y_center in enumerate(y_positions_right[:max_lanes]):
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]

            if lane_idx == 0:
                load_polygons["main"].append({"polygon": lane_polygon, "load": main_value})
            else:
                load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

        # Rest polygon for area below lanes
        if max_lane_width < width_bridgedeck:
            rest_polygon = [
                (0.0, -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, y_positions_right[0] - max_lane_width + 0.5 * lane_width, 0.0),
                (0.0, y_positions_right[0] - max_lane_width + 0.5 * lane_width, 0.0),
            ]
            load_polygons["rest"].append({"polygon": rest_polygon, "load": rest_value})

        results["BG4002"] = load_polygons

    # BG4003: center lanes with dynamic number of lanes on each side
    # Calculate how many lanes can fit on each side of the center
    left_lanes, right_lanes, _ = amount_of_notional_lanes_from_center(width_bridgedeck)
    total_lanes = 1 + left_lanes + right_lanes  # Center lane + left lanes + right lanes

    # Get the center position and adjust for zone offsets
    center_y = width_bridgedeck / 2 - width_firstsegment_zone3 - 0.5 * width_firstsegment_zone2

    load_polygons = {"main": [], "other": [], "rest": []}

    # Create center (main) lane
    center_y_min = center_y - lane_width / 2
    center_y_max = center_y + lane_width / 2
    center_polygon = [
        (0.0, center_y_min, 0.0),
        (length_bridgedeck, center_y_min, 0.0),
        (length_bridgedeck, center_y_max, 0.0),
        (0.0, center_y_max, 0.0),
    ]
    load_polygons["main"].append({"polygon": center_polygon, "load": main_value})

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
        load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

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
        load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

    # Create rest polygons for any remaining areas
    total_lanes_width = total_lanes * lane_width

    # Upper rest area (if exists)
    if center_y + total_lanes_width / 2 < width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3:
        upper_rest = [
            (0.0, center_y + total_lanes_width / 2, 0.0),
            (length_bridgedeck, center_y + total_lanes_width / 2, 0.0),
            (length_bridgedeck, width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (0.0, width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
        ]
        load_polygons["rest"].append({"polygon": upper_rest, "load": rest_value})

    # Lower rest area (if exists)
    if center_y - total_lanes_width / 2 > -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3:
        lower_rest = [
            (0.0, -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (length_bridgedeck, -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (length_bridgedeck, center_y - total_lanes_width / 2, 0.0),
            (0.0, center_y - total_lanes_width / 2, 0.0),
        ]
        load_polygons["rest"].append({"polygon": lower_rest, "load": rest_value})

    results["BG4003"] = load_polygons

    return results


def create_real_udl_traffic_loads(  # noqa: PLR0912, C901
    params: BridgeParametrization,
    length_bridgedeck: float,
    udl_value: float = 9000.0,
) -> dict[str, dict[str, Any]]:
    """
    Create real uniform distributed load (UDL) traffic loads for the bridge.

    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param length_bridgedeck: Length of the bridge deck
    :type length_bridgedeck: float
    :param width_bridgedeck: Width of the bridge deck
    :type width_bridgedeck: float
    :param width_firstsegment_zone3: Width of the first segment in zone 3
    :type width_firstsegment_zone3: float
    :param width_firstsegment_zone2: Width of the first segment in zone 2
    :type width_firstsegment_zone2: float
    :param udl_value: Uniform distributed load value (default: 9000.0)
    :type udl_value: float
    :returns: Dictionary containing real UDL traffic loads
    :rtype: dict[str, dict[str, Any]]
    """
    # Create an empty results dictionary
    results = {}

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factors = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=20000)
    # Obtain load values
    main_value = udl_value * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
    other_value = 2500.0 * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
    rest_value = 2500.0 * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
    # Calculate amount of notional lanes and lane width when starting on one side of the bridge deck

    y_top, width_road = obtain_y_coordinates_road(params)
    y_bottom = y_top - width_road
    max_lanes, lane_width = amount_of_notional_lanes(width_road)  # Maximum number of lanes to consider and lane width

    # BG4001: leftmost lanes (BG8000 logic)
    y_positions_left = generate_real_lane_positions_bg8000(params, lane_width)
    y_positions_right = generate_real_lane_positions_bg9000(params, lane_width)

    if y_positions_left:
        load_polygons: dict[str, list[dict[str, list[tuple[float, float, float]] | float]]] = {"main": [], "other": [], "rest": []}

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
            if lane_idx == 0:
                load_polygons["main"].append({"polygon": lane_polygon, "load": main_value})
            else:
                load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

        # Create rest polygon for areas not covered by lanes
        max_lane_width = max_lanes * lane_width
        if max_lane_width < width_road:
            rest_polygon = [
                (0.0, y_top, 0.0),
                (length_bridgedeck, y_top, 0.0),
                (length_bridgedeck, y_bottom + max_lane_width, 0.0),
                (0.0, y_bottom + max_lane_width, 0.0),
            ]
            load_polygons["rest"].append({"polygon": rest_polygon, "load": rest_value})

        results["BG4001"] = load_polygons

    # BG4002: Rightmost lanes (BG9000 logic)
    if y_positions_right:
        load_polygons = {"main": [], "other": [], "rest": []}

        for lane_idx, y_center in enumerate(y_positions_right[:max_lanes]):
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]

            if lane_idx == 0:
                load_polygons["main"].append({"polygon": lane_polygon, "load": main_value})
            else:
                load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

        # Rest polygon for area below lanes
        if max_lane_width < width_road:
            rest_polygon = [
                (0.0, y_top - max_lane_width, 0.0),
                (length_bridgedeck, y_top - max_lane_width, 0.0),
                (length_bridgedeck, y_bottom, 0.0),
                (0.0, y_bottom, 0.0),
            ]
            load_polygons["rest"].append({"polygon": rest_polygon, "load": rest_value})

        results["BG4002"] = load_polygons

    # BG4003: center lanes with dynamic number of lanes on each side
    # Calculate how many lanes can fit on each side of the center
    left_lanes, right_lanes, _ = amount_of_notional_lanes_from_center(width_road)
    total_lanes = 1 + left_lanes + right_lanes  # Center lane + left lanes + right lanes

    # Get the center position and adjust for zone offsets
    center_y = (y_top + y_bottom) / 2

    load_polygons = {"main": [], "other": [], "rest": []}

    # Create center (main) lane
    center_y_min = center_y - lane_width / 2
    center_y_max = center_y + lane_width / 2
    center_polygon = [
        (0.0, center_y_min, 0.0),
        (length_bridgedeck, center_y_min, 0.0),
        (length_bridgedeck, center_y_max, 0.0),
        (0.0, center_y_max, 0.0),
    ]
    load_polygons["main"].append({"polygon": center_polygon, "load": main_value})

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
        load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

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
        load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

    # Create rest polygons for any remaining areas
    total_lanes_width = total_lanes * lane_width

    # Upper rest area (if exists)
    if center_y + total_lanes_width / 2 < width_road / 2:
        upper_rest = [
            (0.0, y_top, 0.0),
            (length_bridgedeck, y_top, 0.0),
            (length_bridgedeck, center_y + total_lanes_width / 2, 0.0),
            (0.0, center_y + total_lanes_width / 2, 0.0),
        ]
        load_polygons["rest"].append({"polygon": upper_rest, "load": rest_value})

        # Lower rest area (if exists)
        lower_rest = [
            (0.0, center_y - total_lanes_width / 2, 0.0),
            (length_bridgedeck, center_y - total_lanes_width / 2, 0.0),
            (length_bridgedeck, y_bottom, 0.0),
            (0.0, y_bottom, 0.0),
        ]
        load_polygons["rest"].append({"polygon": lower_rest, "load": rest_value})

    results["BG4003"] = load_polygons

    return results


# ========================================================================
# THEORETICAL TRAFFIC LANE INTEGRATION
# ========================================================================
# These functions connect tandem loads to theoretical traffic lanes from
# src.geometry.load_zone_geometry for proper structural engineering analysis.


def generate_theoretical_lane_positions_bg8000(
    width_bridgedeck: float,
    lane_width: float = 3.0,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for theoretical traffic lanes across bridge width.

    Creates lane center positions based on geometric division of bridge width.
    This provides the foundation for theoretical lane-based tandem loading.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers (shifted by -zone3_width)
    :rtype: list[float]
    :raises ValueError: If bridge_width or lane_width is not positive

    Examples:
        >>> generate_theoretical_lane_positions(30.0, 3.0, 2.0)
        [-0.5, 2.5, 5.5, 8.5, 11.5, 14.5, 17.5, 20.5, 23.5, 26.5]

    """
    if width_bridgedeck <= 0:
        raise ValueError("Bridge width must be positive")
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Calculate number of complete lanes
    num_lanes = int(width_bridgedeck // lane_width)

    # Generate lane center positions
    lane_centers = []
    for lane_idx in range(num_lanes):
        lane_start = lane_idx * lane_width
        lane_center = lane_start + (lane_width / 2)  # Center of each lane
        lane_centers.append(lane_center - zone3_width - 0.5 * zone2_width)

    return lane_centers


# Standard tandem wheel offsets from bottom left corner
TANDEM_WHEEL_OFFSETS = [(0, 0), (1.2, 0), (0, 2), (1.2, 2)]


def tandem_systems_theoretical_lanes_bg8000(  # noqa: PLR0913
    params: BridgeParametrization,
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = 3.0,
) -> list[dict[str, Any]]:
    """
    Generate tandem loads positioned at theoretical traffic lane centers.

    This function replaces the fixed Eurocode notional lane positions with
    theoretical lane positions based on geometric bridge width division.
    Provides comprehensive coverage across full bridge width.

    :param length_bridgedeck: Bridge length in meters
    :type length_bridgedeck: float
    :param width_bridgedeck: Bridge width in meters
    :type width_bridgedeck: float
    :param thickness_bridgedeck: Bridge thickness in meters
    :type thickness_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of tandem load cases with full width coverage
    :rtype: list[dict[str, Any]]

    Load Case Structure:
        Each load case contains:
        - load_case: "TH6001", "TH6002", etc. (TH = Theoretical)
        - wheels: List of 4 wheel coordinates per tandem
        - load: Load intensity in N/m²
    """
    wheel_size = 0.4

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)

    # Get theoretical lane positions (NEW: replaces fixed positions)
    lane_y_positions = generate_theoretical_lane_positions_bg8000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=20000)[0]
    # Obtain load values
    load_main = 300000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = 200000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = 100000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    # Only generate for BG8 (first lane position)
    if lane_y_positions:
        y_lane_center = lane_y_positions[0]
        prefix = "BG8"
        for tandem_idx, x in enumerate(tandem_x_positions, 1):
            wheels_main = []
            tandem_start_y_main = y_lane_center - 1.2
            for dx, dy in TANDEM_WHEEL_OFFSETS:
                x0 = x + dx
                y0 = tandem_start_y_main + dy
                wheel_coords = [
                    [x0 + wheel_size, y0],
                    [x0 + wheel_size, y0 + wheel_size],
                    [x0, y0 + wheel_size],
                    [x0, y0],
                ]
                wheels_main.append(wheel_coords)

            # Add load_case
            load_case: dict[str, Any] = {
                "load_case": f"{prefix}{tandem_idx:03d}",
            }

            # Add 200 kN tandem in next lane (if exists)
            wheels_200 = []
            if len(lane_y_positions) > 1:
                tandem_start_y_200 = lane_y_positions[1] - 1.2
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = tandem_start_y_200 + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels_200.append(wheel_coords)

            # Add 100 kN tandem in next-next lane (if exists)
            wheels_100 = []
            if len(lane_y_positions) > 2:
                tandem_start_y_100 = lane_y_positions[2] - 1.2
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = tandem_start_y_100 + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels_100.append(wheel_coords)

            load_case["loads"] = [
                {"wheels": wheels_main, "load": load_main},
                {"wheels": wheels_200, "load": load_second},
                {"wheels": wheels_100, "load": load_third},
            ]

            results.append(load_case)

    return results


# ========================================================================
# PHASE 2: REVERSED NOTIONAL LANES (CRITICAL LOADING FROM OPPOSITE SIDE) FOR BG9000
# ========================================================================
def generate_theoretical_lane_positions_bg9000(
    width_bridgedeck: float,
    lane_width: float = 3.0,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for theoretical traffic lanes across bridge width, starting from the right edge.

    This mirrors the original lane division, but lanes are counted from the right edge instead of the left.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers (shifted by -zone3_width), reversed
    :rtype: list[float]
    """
    if width_bridgedeck <= 0:
        raise ValueError("Bridge width must be positive")
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    num_lanes = int(width_bridgedeck // lane_width)
    lane_centers = []
    for lane_idx in range(num_lanes):
        # Start from the right edge
        lane_start = width_bridgedeck - lane_idx * lane_width
        lane_center = lane_start - (lane_width / 2)
        lane_centers.append(lane_center - zone3_width - 0.5 * zone2_width)

    return lane_centers


def tandem_systems_theoretical_lanes_bg9000(  # noqa: PLR0913
    params: BridgeParametrization,
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = 3.0,
) -> list[dict[str, Any]]:
    """
    Generate tandem loads positioned at theoretical traffic lane centers, starting from the right edge.

    This function creates a critical loading scenario by mirroring the lane division and decreasing loads inwards.

    :param length_bridgedeck: Bridge length in meters
    :type length_bridgedeck: float
    :param width_bridgedeck: Bridge width in meters
    :type width_bridgedeck: float
    :param thickness_bridgedeck: Bridge thickness in meters
    :type thickness_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of tandem load cases with full width coverage, reversed
    :rtype: list[dict[str, Any]]
    """
    wheel_size = 0.4
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
    lane_y_positions = generate_theoretical_lane_positions_bg9000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=20000)[0]
    # Obtain load values
    load_main = 300000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = 200000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = 100000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    # Only generate for BG9 (first lane position, reversed)
    if lane_y_positions:
        y_lane_center = lane_y_positions[0]
        prefix = "BG9"
        for tandem_idx, x in enumerate(tandem_x_positions, 1):
            wheels_main = []
            tandem_start_y_main = y_lane_center - 1.2
            for dx, dy in TANDEM_WHEEL_OFFSETS:
                x0 = x + dx
                y0 = tandem_start_y_main + dy
                wheel_coords = [
                    [x0 + wheel_size, y0],
                    [x0 + wheel_size, y0 + wheel_size],
                    [x0, y0 + wheel_size],
                    [x0, y0],
                ]
                wheels_main.append(wheel_coords)

            load_case: dict[str, Any] = {
                "load_case": f"{prefix}{tandem_idx:03d}",
            }

            # 200 kN tandem in next lane (if exists)
            wheels_200 = []
            if len(lane_y_positions) > 1:
                tandem_start_y_200 = lane_y_positions[1] - 1.2
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = tandem_start_y_200 + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels_200.append(wheel_coords)

            # 100 kN tandem in next-next lane (if exists)
            wheels_100 = []
            if len(lane_y_positions) > 2:
                tandem_start_y_100 = lane_y_positions[2] - 1.2
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = tandem_start_y_100 + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels_100.append(wheel_coords)

            load_case["loads"] = [
                {"wheels": wheels_main, "load": load_main},
                {"wheels": wheels_200, "load": load_second},
                {"wheels": wheels_100, "load": load_third},
            ]

            results.append(load_case)

    return results


def generate_theoretical_lane_positions_bg10000(
    width_bridgedeck: float,
    lane_width: float = 3.0,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for BG10000 load case: 3 lanes, 300 kN in center, 200/100 kN adjacent.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers (center, left, right)
    :rtype: list[float]
    """
    if width_bridgedeck <= 0:
        raise ValueError("Bridge width must be positive")
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Center lane
    y_center = width_bridgedeck / 2 - zone3_width - 0.5 * zone2_width
    # Left lane (adjacent to center)
    y_left = y_center - lane_width
    # Right lane (adjacent to center)
    y_right = y_center + lane_width

    return [y_center, y_left, y_right]


def tandem_systems_theoretical_lanes_bg10000(  # noqa: PLR0913
    params: BridgeParametrization,
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = 3.0,
) -> list[dict[str, Any]]:
    """
    Generate BG10000 load cases: 300 kN tandem in center, 200/100 kN adjacent.

    :param length_bridgedeck: Bridge length in meters
    :type length_bridgedeck: float
    :param width_bridgedeck: Bridge width in meters
    :type width_bridgedeck: float
    :param thickness_bridgedeck: Bridge thickness in meters
    :type thickness_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of BG10000 load cases
    :rtype: list[dict[str, Any]]
    """
    wheel_size = 0.4
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
    lane_y_positions = generate_theoretical_lane_positions_bg10000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=20000)[0]
    # Obtain load values
    load_main = 300000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = 200000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = 100000 / (0.4 * 0.4) * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor

    # Order: center (300 kN), left/right (200/100 kN)
    y_center, y_left, y_right = lane_y_positions
    prefix = "BG10"
    results = []
    idx = 1
    # First, configuration A: 200 kN left, 100 kN right
    for x in tandem_x_positions:
        wheels_300 = []
        tandem_start_y_300 = y_center - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_300 + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_300.append(wheel_coords)

        wheels_200_left = []
        tandem_start_y_200_left = y_left - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_200_left + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_200_left.append(wheel_coords)

        wheels_100_right = []
        tandem_start_y_100_right = y_right - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_100_right + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_100_right.append(wheel_coords)

        load_case_a = {
            "load_case": f"{prefix}{idx:03d}",
            "loads": [
                {"wheels": wheels_300, "load": load_main},
                {"wheels": wheels_200_left, "load": load_second},
                {"wheels": wheels_100_right, "load": load_third},
            ],
        }
        results.append(load_case_a)
        idx += 1

    # Then, configuration B: 100 kN left, 200 kN right
    for x in tandem_x_positions:
        wheels_300 = []
        tandem_start_y_300 = y_center - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_300 + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_300.append(wheel_coords)

        wheels_100_left = []
        tandem_start_y_100_left = y_left - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_100_left + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_100_left.append(wheel_coords)

        wheels_200_right = []
        tandem_start_y_200_right = y_right - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_200_right + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_200_right.append(wheel_coords)

        load_case_b = {
            "load_case": f"{prefix}{idx:03d}",
            "loads": [
                {"wheels": wheels_300, "load": load_main},
                {"wheels": wheels_100_left, "load": load_third},
                {"wheels": wheels_200_right, "load": load_second},
            ],
        }
        results.append(load_case_b)
        idx += 1
    return results


# ========================================================================
# Generation of tandem systems for real lane distribution
# ========================================================================


def obtain_y_coordinates_road(
    params: BridgeParametrization,
) -> tuple[float, float]:
    """
    A helper function to obtain the top y-coordinate and width of the road section from the load zones data.

    Args:
        params: Bridge parametrization containing load zones data.

    Returns:
        Tuple containing:
            - Y-coordinate for the top of the road section (0.0 if no valid road section)
            - Width of the first segment (d1_width) of the road section (0.0 if no valid road section)

    Note:
        If no valid road section or bridge geometry is found, returns (0.0, 0.0) as a safe default.

    """
    # Obtain top and bottom Y-coordinates for the road using the provided parameters.
    load_zones_data_params = get_load_zones_data_from_params(params)
    bridge_geom_data = get_bridge_geom_data(params)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return 0.0, 0.0

    # Update load zones data with geometry properties
    load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

    # Find the 'Auto' zone and get its y-coordinates and width
    for zone in load_zones_data_params:
        if zone["zone_type"] == "Auto":
            # Get y-coordinates, ensure we have a valid list and first value
            y_coords = zone.get("y_coords_top_current_zone", [])
            y_coord = float(y_coords[0]) if y_coords else 0.0

            # Get d1_width, ensure it's a valid number
            width_value = zone.get("d1_width")
            d1_width = float(width_value) if isinstance(width_value, (int, float)) else 0.0

            return y_coord, d1_width

    return 0.0, 0.0


def generate_real_lane_positions_bg8000(
    params: BridgeParametrization,
    lane_width: float = 3.0,
) -> list[float]:
    """
    Generate y-positions of real traffic lanes for BG8000 load group based on actual road section geometry.

    This function calculates the y-coordinates for lane centers based on the actual road section defined
    in the bridge parametrization. It finds the 'Auto' zone from the load zones data and uses its geometry
    to determine lane positions.

    Args:
        params: Bridge parametrization containing load zones data and geometry
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of Y-coordinates for lane centers, starting from the top of the road section
        and working downward, with each position adjusted for the actual road geometry.

    Raises:
        ValueError: If road width or lane width is not positive

    """
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")
        # Get load zone information from params using the utility functions

    # Calculate number of complete lanes
    y_top, width_road = obtain_y_coordinates_road(params)
    if width_road <= 0 or None:
        raise ValueError("Road width must be a positive value")
    y_bottom = y_top - width_road
    num_lanes = int(width_road // lane_width)

    # Generate lane center positions
    lane_centers = []
    for lane_idx in range(num_lanes):
        lane_start = lane_idx * lane_width
        lane_center = lane_start + (lane_width / 2)  # Center of each lane
        lane_centers.append(y_bottom + lane_center)

    return lane_centers


def tandem_systems_real_lanes_bg8000(
    params: BridgeParametrization,
    length_bridgedeck: float,
    thickness_bridgedeck: float,
    lane_width: float = 3.0,
) -> list[dict[str, Any]]:
    """
    Generate tandem load cases for BG8000 load group based on actual road lanes.

    This function creates tandem system load cases positioned according to the real traffic lanes
    defined in the bridge's road section. It specifically handles the BG8000 load group requirements,
    placing tandem systems in the most critical lane position.

    Args:
        params: Bridge parametrization containing load zones data and geometry
        length_bridgedeck: Bridge length in meters
        thickness_bridgedeck: Bridge deck thickness in meters
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of load case dictionaries, where each dictionary contains:
            - load_case: Identifier string (e.g., "BG8001", "BG8002")
            - wheels: List of wheel coordinates (x, y, z) for the tandem system
            - load: Load intensity in N/m² for the wheels

    Note:
        - Uses real traffic lanes obtained from the actual road section geometry
        - Only generates load cases for the first (most critical) lane position
        - Tandem system dimensions and loads comply with BG8000 requirements
        - Wheel positions account for the standard 1.2m offset from lane center

    """
    wheel_size = 0.4

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)

    # Get theoretical lane positions (NEW: replaces fixed positions)
    lane_y_positions = generate_real_lane_positions_bg8000(params, lane_width)

    results = []
    # Only generate for BG8 (first lane position)
    if lane_y_positions:
        y_lane_center = lane_y_positions[0]
        prefix = "BG8"
        for tandem_idx, x in enumerate(tandem_x_positions, 1):
            wheels_main = []
            tandem_start_y_main = y_lane_center - 1.2
            for dx, dy in TANDEM_WHEEL_OFFSETS:
                x0 = x + dx
                y0 = tandem_start_y_main + dy
                wheel_coords = [
                    [x0 + wheel_size, y0],
                    [x0 + wheel_size, y0 + wheel_size],
                    [x0, y0 + wheel_size],
                    [x0, y0],
                ]
                wheels_main.append(wheel_coords)

            # Add load_case
            load_case: dict[str, Any] = {
                "load_case": f"{prefix}{tandem_idx:03d}",
            }

            # Add 200 kN tandem in next lane (if exists)
            wheels_200 = []
            if len(lane_y_positions) > 1:
                tandem_start_y_200 = lane_y_positions[1] - 1.2
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = tandem_start_y_200 + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels_200.append(wheel_coords)

            # Add 100 kN tandem in next-next lane (if exists)
            wheels_100 = []
            if len(lane_y_positions) > 2:
                tandem_start_y_100 = lane_y_positions[2] - 1.2
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = tandem_start_y_100 + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels_100.append(wheel_coords)

            load_case["loads"] = [
                {"wheels": wheels_main, "load": 300000 / (0.4 * 0.4)},
                {"wheels": wheels_200, "load": 200000 / (0.4 * 0.4)},
                {"wheels": wheels_100, "load": 100000 / (0.4 * 0.4)},
            ]

            results.append(load_case)

    return results


def generate_real_lane_positions_bg9000(
    params: BridgeParametrization,
    lane_width: float = 3.0,
) -> list[float]:
    """
    Generate y-positions of real traffic lanes for BG9000 load group based on actual road section geometry.

    This function calculates the y-coordinates for lane centers based on the actual road section defined
    in the bridge parametrization. It finds the 'Auto' zone from the load zones data and uses its geometry
    to determine lane positions.

    Args:
        params: Bridge parametrization containing load zones data and geometry
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of Y-coordinates for lane centers, starting from the top of the road section
        and working downward, with each position adjusted for the actual road geometry.

    Raises:
        ValueError: If road width or lane width is not positive

    """
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Calculate number of complete lanes
    y_top, width_road = obtain_y_coordinates_road(params)
    num_lanes = int(width_road // lane_width)

    if width_road <= 0:
        raise ValueError("Road width must be a positive value")

    # Generate lane center positions
    lane_centers = []
    for lane_idx in range(num_lanes):
        lane_start = y_top - lane_idx * lane_width
        lane_center = lane_start - (lane_width / 2)  # Center of each lane
        lane_centers.append(lane_center)

    return lane_centers


def tandem_systems_real_lanes_bg9000(
    params: BridgeParametrization,
    length_bridgedeck: float,
    thickness_bridgedeck: float,
    lane_width: float = 3.0,
) -> list[dict[str, Any]]:
    """
    Generate tandem load cases for BG9000 load group based on actual road lanes.

    This function creates tandem system load cases positioned according to the real traffic lanes
    defined in the bridge's road section. It specifically handles the BG9000 load group requirements,
    placing tandem systems in the most critical lane position.

    Args:
        params: Bridge parametrization containing load zones data and geometry
        length_bridgedeck: Bridge length in meters
        thickness_bridgedeck: Bridge deck thickness in meters
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of load case dictionaries, where each dictionary contains:
            - load_case: Identifier string (e.g., "BG9001", "BG9002")
            - wheels: List of wheel coordinates (x, y, z) for the tandem system
            - load: Load intensity in N/m² for the wheels

    Note:
        - Uses real traffic lanes obtained from the actual road section geometry
        - Only generates load cases for the first (most critical) lane position
        - Tandem system dimensions and loads comply with BG9000 requirements
        - Wheel positions account for the standard 1.2m offset from lane center

    """
    wheel_size = 0.4

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)

    # Get theoretical lane positions (NEW: replaces fixed positions)
    lane_y_positions = generate_real_lane_positions_bg9000(params, lane_width)

    results = []
    # Only generate for BG9 (first lane position)
    if lane_y_positions:
        y_lane_center = lane_y_positions[0]
        prefix = "BG9"
        for tandem_idx, x in enumerate(tandem_x_positions, 1):
            wheels_main = []
            tandem_start_y_main = y_lane_center - 1.2
            for dx, dy in TANDEM_WHEEL_OFFSETS:
                x0 = x + dx
                y0 = tandem_start_y_main + dy
                wheel_coords = [
                    [x0 + wheel_size, y0],
                    [x0 + wheel_size, y0 + wheel_size],
                    [x0, y0 + wheel_size],
                    [x0, y0],
                ]
                wheels_main.append(wheel_coords)

            # Add load_case
            load_case: dict[str, Any] = {
                "load_case": f"{prefix}{tandem_idx:03d}",
            }

            # Add 200 kN tandem in next lane (if exists)
            wheels_200 = []
            if len(lane_y_positions) > 1:
                tandem_start_y_200 = lane_y_positions[1] - 1.2
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = tandem_start_y_200 + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels_200.append(wheel_coords)

            # Add 100 kN tandem in next-next lane (if exists)
            wheels_100 = []
            if len(lane_y_positions) > 2:
                tandem_start_y_100 = lane_y_positions[2] - 1.2
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = tandem_start_y_100 + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels_100.append(wheel_coords)

            load_case["loads"] = [
                {"wheels": wheels_main, "load": 300000 / (0.4 * 0.4)},
                {"wheels": wheels_200, "load": 200000 / (0.4 * 0.4)},
                {"wheels": wheels_100, "load": 100000 / (0.4 * 0.4)},
            ]

            results.append(load_case)

    return results


def generate_real_lane_positions_bg10000(
    params: BridgeParametrization,
    lane_width: float = 3.0,
) -> list[float]:
    """
    Generate Y-positions for BG10000 load case: 3 lanes, 300 kN in center, 200/100 kN adjacent.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers (center, left, right)
    :rtype: list[float]
    """
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Get road coordinates and validate them
    y_top, width_road = obtain_y_coordinates_road(params)

    # Ensure we have valid road dimensions before continuing
    if width_road <= 0:
        raise ValueError("Road width must be positive")

    # Calculate bottom y-coordinate from validated dimensions
    y_bottom = y_top - width_road

    # Center lane
    y_center = (y_top + y_bottom) / 2
    # Left lane (adjacent to center)
    y_left = y_center - lane_width
    # Right lane (adjacent to center)
    y_right = y_center + lane_width

    return [y_center, y_left, y_right]


def tandem_systems_real_lanes_bg10000(
    params: BridgeParametrization,
    length_bridgedeck: float,
    thickness_bridgedeck: float,
    lane_width: float = 3.0,
) -> list[dict[str, Any]]:
    """
    Generate BG10000 load cases: 300 kN tandem in center, 200/100 kN adjacent.

    :param length_bridgedeck: Bridge length in meters
    :type length_bridgedeck: float
    :param width_bridgedeck: Bridge width in meters
    :type width_bridgedeck: float
    :param thickness_bridgedeck: Bridge thickness in meters
    :type thickness_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of BG10000 load cases
    :rtype: list[dict[str, Any]]
    """
    wheel_size = 0.4
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
    lane_y_positions = generate_real_lane_positions_bg10000(params, lane_width)

    # Order: center (300 kN), left/right (200/100 kN)
    y_center, y_left, y_right = lane_y_positions
    prefix = "BG10"
    results = []
    idx = 1
    # First, configuration A: 200 kN left, 100 kN right
    for x in tandem_x_positions:
        wheels_300 = []
        tandem_start_y_300 = y_center - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_300 + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_300.append(wheel_coords)

        wheels_200_left = []
        tandem_start_y_200_left = y_left - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_200_left + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_200_left.append(wheel_coords)

        wheels_100_right = []
        tandem_start_y_100_right = y_right - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_100_right + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_100_right.append(wheel_coords)

        load_case_a = {
            "load_case": f"{prefix}{idx:03d}",
            "loads": [
                {"wheels": wheels_300, "load": 300000 / (0.4 * 0.4)},
                {"wheels": wheels_200_left, "load": 200000 / (0.4 * 0.4)},
                {"wheels": wheels_100_right, "load": 100000 / (0.4 * 0.4)},
            ],
        }
        results.append(load_case_a)
        idx += 1

    # Then, configuration B: 100 kN left, 200 kN right
    for x in tandem_x_positions:
        wheels_300 = []
        tandem_start_y_300 = y_center - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_300 + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_300.append(wheel_coords)

        wheels_100_left = []
        tandem_start_y_100_left = y_left - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_100_left + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_100_left.append(wheel_coords)

        wheels_200_right = []
        tandem_start_y_200_right = y_right - 1.2
        for dx, dy in TANDEM_WHEEL_OFFSETS:
            x0 = x + dx
            y0 = tandem_start_y_200_right + dy
            wheel_coords = [
                [x0 + wheel_size, y0],
                [x0 + wheel_size, y0 + wheel_size],
                [x0, y0 + wheel_size],
                [x0, y0],
            ]
            wheels_200_right.append(wheel_coords)

        load_case_b = {
            "load_case": f"{prefix}{idx:03d}",
            "loads": [
                {"wheels": wheels_300, "load": 300000 / (0.4 * 0.4)},
                {"wheels": wheels_100_left, "load": 100000 / (0.4 * 0.4)},
                {"wheels": wheels_200_right, "load": 200000 / (0.4 * 0.4)},
            ],
        }
        results.append(load_case_b)
        idx += 1
    return results


# ========================================================================
# ORIGINAL EUROCODE FUNCTIONS (PRESERVED FOR COMPLIANCE)
# ========================================================================
# These functions maintain Eurocode notional lane compliance and are kept
# for regulatory requirements and comparison purposes.


def amount_of_notional_lanes(width_bridgedeck: float) -> tuple[int, float]:
    """
    Calculate the number of notional lanes and their width based on the bridge deck width.

    Args:
        width_bridgedeck (float): The width of the bridge deck in meters.

    Returns:
        tuple[int, float]: A tuple containing the number of notional lanes and the width per lane in meters.

    """
    if width_bridgedeck < 5.4:
        return 1, 3
    if 5.4 <= width_bridgedeck < 6.0:
        return 2, width_bridgedeck / 2
    return int(width_bridgedeck // 3), 3


def amount_of_notional_lanes_from_center(width_bridgedeck: float) -> tuple[int, int, float]:
    """
    Calculate the number of notional lanes that can fit on either side of the bridge deck center.

    For BG4003 (center load case), we need to determine how many lanes can fit on either side of
    the center lane. The total width available is divided into two parts (left and right of center),
    and we calculate how many 3m lanes can fit in each part.

    Args:
        width_bridgedeck (float): The width of the bridge deck in meters.

    Returns:
        tuple[int, int, float]: A tuple containing:
            - Number of lanes that fit left of center
            - Number of lanes that fit right of center
            - Width per lane (always 3.0m as per standard)

    """
    # Center lane always takes 3.0m
    center_lane_width = 3.0
    remaining_width = width_bridgedeck - center_lane_width

    # Calculate space on either side
    width_per_side = remaining_width / 2

    # Calculate number of full 3.0m lanes that can fit on each side
    lanes_per_side = int(width_per_side // 3.0)

    return lanes_per_side, lanes_per_side, 3.0


def calculate_possibilities_lane_orientation(width_bridgedeck: float) -> int:
    """
    Calculate the number of possibilities according to which the tandemsystems can be applied.

    Args:
        width_bridgedeck (float): The width of the bridge deck in meters.

    Returns:
        int: An integer containing the amount of lane orientations possible.

    """
    amount_of_lanes = amount_of_notional_lanes(width_bridgedeck)
    if amount_of_lanes[0] == 1 or amount_of_lanes[0] == 2:
        return 2
    return 4


def calculate_start_of_lanes(thickness_bridgedeck: float) -> float:
    """
    Calculate the distance from the edge of the bridge deck, from where the tandem systems start.
    Assuming a spread under 45 degrees, the distance is equal to 0.9 times the thickness of the bridge deck.

    Args:
        thickness_bridgedeck (float): The thickness of the bridge deck in meters.

    Returns:
        distance(float): The distance in meters from the edge of the bridge deck to the start of the tandem systems.

    """
    return 0.9 * thickness_bridgedeck


def tandem_system_sequencer(length_bridgedeck: float, thickness_bridgedeck: float) -> list[float]:
    """
    Calculate the x-positions of the tandem systems in a notional lane along the length of the bridge deck.
    Default spacing between tandem systems is 0.5 meters. A tandem system exactly mid-span is always included.

    Args:
        length_bridgedeck (float): The length of the bridge deck in meters.
        thickness_bridgedeck (float): The thickness of the bridge deck in meters.

    Returns:
        list[float]: A list containing the positions of the tandem systems along the bridge deck.

    """
    start_of_lanes = calculate_start_of_lanes(thickness_bridgedeck)
    tandem_systems = []
    dx = 0.5  # Default spacing between tandem systems in meters
    mid_span_position = length_bridgedeck / 2
    end_span_position = length_bridgedeck - start_of_lanes - 1.6

    # Generate positions from start_of_lanes to end_span_position (inclusive), step dx
    pos = start_of_lanes
    while pos < end_span_position - 1e-6:  # Use a small epsilon to avoid floating-point issues
        tandem_systems.append(round(pos, 6))
        pos += dx
    # Always include end_span_position exactly
    tandem_systems.append(round(end_span_position, 6))

    # Ensure mid-span position is included (within tolerance)
    if not any(abs(p - mid_span_position) < 1e-6 for p in tandem_systems):
        tandem_systems.append(round(mid_span_position, 6))

    return sorted(set(tandem_systems))


def calculate_pavement_load_from_dynamic_array(
    load_zones_array: list[dict[str, Any]],
    thickness_field: str = "pavement_thickness",
    material_field: str = "pavement_material",
) -> list[float]:
    """
    Calculate the load (kN/m²) for each row in the load zones dynamic array.

    :param load_zones_array: List of dicts from the Belastingzones DynamicArray (params.load_zones_data_array)
    :type load_zones_array: list[dict[str, Any]]
    :param thickness_field: Name of the thickness field in each row (default: "pavement_thickness")
    :type thickness_field: str
    :param material_field: Name of the material field in each row (default: "pavement_material")
    :type material_field: str
    :returns: List of calculated loads (kN/m²) for each row (0.0 if missing or unknown material)
    :rtype: list[float]
    """
    # Build a lookup for material densities (case-insensitive)
    density_lookup = {name.lower(): density for name, density in get_material_densities()}
    result: list[float] = []
    for row in load_zones_array:
        thickness = row.get(thickness_field, 0.0)
        material = row.get(material_field, "")
        if not material or not isinstance(thickness, int | float):
            result.append(0.0)
            continue
        density = density_lookup.get(str(material).lower(), 0.0)
        load = thickness * density if density > 0 and thickness > 0 else 0.0
        result.append(load)
    return result


def calculate_pavement_load_from_material(
    thickness: float,
    material: str,
) -> float:
    """
    Calculate the pavement load (kN/m²) from the material properties.

    :param thickness: Pavement thickness in meters
    :type thickness: float
    :param material: Pavement material name
    :type material: str
    :returns: Calculated load (kN/m²) (0.0 if missing or unknown material)
    :rtype: float
    """
    # Build a lookup for material densities (case-insensitive)
    density_lookup = {name.lower(): density for name, density in get_material_densities()}

    if not material or not isinstance(thickness, int | float):
        return 0.0

    density = density_lookup.get(str(material).lower(), 0.0)
    return thickness * density if density > 0 and thickness > 0 else 0.0


# This function is used to create the load cases 2001/2002/2003
def create_material_surface_load(
    builder: "SciaModelBuilder",
    load_config: dict[str, Any],
    bridge_geom_data: LoadZoneGeometryData,
) -> None:
    """
    Create a surface load for a specific material in a load zone span.

    :param builder: SCIA model builder instance
    :param load_config: Configuration containing all load parameters:
        - load_zone: Load zone data containing coordinates and properties
        - zone_index: Index of the load zone
        - span: Span index within the load zone
        - material_name: Name of the material for load naming
        - load_case_name: Name of the load case to apply the load to
    :param bridge_geom_data: Bridge geometry data
    """
    # Extract parameters from load_config
    load_zone = load_config["load_zone"]
    zone_index = load_config["zone_index"]
    span = load_config["span"]
    material_name = load_config["material_name"]
    load_case_name = load_config["load_case_name"]

    # Calculate coordinates for the surface load
    y_coord_top_left = round(load_zone["y_coords_top_current_zone"][span], 2)
    y_coord_top_right = round(load_zone["y_coords_top_current_zone"][span + 1], 2)
    y_coord_bottom_left = round(y_coord_top_left - load_zone["zone_widths_per_d"][span], 2)
    y_coord_bottom_right = round(y_coord_top_right - load_zone["zone_widths_per_d"][span + 1], 2)
    x_coord_left = round(bridge_geom_data.x_coords_d_points[span], 2)
    x_coord_right = round(bridge_geom_data.x_coords_d_points[span + 1], 2)

    corners = [
        (x_coord_left, y_coord_top_left, 0.0),
        (x_coord_right, y_coord_top_right, 0.0),
        (x_coord_right, y_coord_bottom_right, 0.0),
        (x_coord_left, y_coord_bottom_left, 0.0),
    ]

    builder.create_surface_load(
        name=f"{load_zone['zone_type']}_{zone_index}_{material_name}_{span}_d{load_zone['pavement_thickness']}",
        load_case_name=load_case_name,
        corner_points=corners,
        load_value=-calculate_pavement_load_from_material(load_zone["pavement_thickness"], load_zone["pavement_material"]) * 1000,  # Convert to kN/m²
    )


# This function is used to create the load cases 2001/2002/2003
def add_material_loads(
    builder: "SciaModelBuilder",
    params: BridgeParametrization,
    material_config: dict[str, str],
) -> None:
    """
    Add surface loads for specified materials to the SCIA model.

    :param builder: SCIA model builder instance
    :param params: Bridge parameters
    :param material_config: Dictionary mapping material names to their load case names
    """
    # Get load zone information from params using the utility functions
    load_zones_data_params = get_load_zones_data_from_params(params)
    bridge_geom_data = get_bridge_geom_data(params)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return

    # Update load zones data with geometry properties
    load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

    # Iterate through load zones and apply loads for specified materials
    for i, load_zone in enumerate(load_zones_data_params):
        pavement_material = load_zone.get("pavement_material", "")

        if pavement_material in material_config:
            load_case_name = material_config[pavement_material]
            # Clean material name for use in load naming
            material_name = pavement_material.replace(" ", "_").replace("(", "").replace(")", "").lower()

            # Iterate through spans
            for span in range(len(load_zone["y_coords_top_current_zone"]) - 1):
                load_config = {
                    "load_zone": load_zone,
                    "zone_index": i,
                    "span": span,
                    "material_name": material_name,
                    "load_case_name": load_case_name,
                }
                create_material_surface_load(builder, load_config, bridge_geom_data)


# Helper function to calculate wheel corners for vehicle loads
def _calculate_wheel_corners_vehicle(center_x: float, center_y: float, wheel_contact_area: float) -> list[tuple[float, float, float]]:
    """
    Calculate the four corner coordinates of a wheel footprint.

    :param center_x: X-coordinate of wheel center
    :param center_y: Y-coordinate of wheel center
    :param wheel_contact_area: Size of the wheel contact area (assumed square)
    :returns: List of corner coordinates as (x, y, z) tuples (clockwise from top_left)
    """
    half_area = wheel_contact_area / 2
    return [
        (center_x - half_area, center_y + half_area, 0.0),  # top_left
        (center_x + half_area, center_y + half_area, 0.0),  # top_right
        (center_x + half_area, center_y - half_area, 0.0),  # bottom_right
        (center_x - half_area, center_y - half_area, 0.0),  # bottom_left
    ]


# Helper function to calculate vehicle load locations
def calc_vehicle_load_locations(
    x_coord: float, y_coord: float, vehicle_length: float, vehicle_width: float, wheel_contact_area: float
) -> dict[str, list[tuple[float, float, float]]]:
    """
    Calculate vehicle load locations based on vehicle position.

    Creates a 4-wheel vehicle footprint positioned at the given coordinates.
    Vehicle dimensions: vehicle_length x vehicle_width with wheels at each corner.
    Each wheel has a wheel_contact_area x wheel_contact_area footprint.

    :param x_coord: X-coordinate of vehicle's front-left corner
    :param y_coord: Y-coordinate of vehicle's front-left corner (top edge)
    :param vehicle_length: Length of the vehicle in meters
    :param vehicle_width: Width of the vehicle in meters
    :param wheel_contact_area: Size of the wheel contact area (assumed square)
    :returns: Dictionary containing wheel corner coordinates for each of the 4 wheels
    :rtype: dict[str, list[tuple[float, float, float]]]

    Vehicle Layout:
            ┌────────────────────┐
            │ TL             TR  │
            │                    │ vehicle_width
    front   │                    │ rear
            │                    │
            │ BL             BR  │
            └────────────────────┘
                vehicle_length
    """
    # Calculate wheel center positions
    # Front wheels (left column)
    top_left_center = (x_coord, y_coord)
    bottom_left_center = (x_coord, y_coord - vehicle_width)

    # Rear wheels (right column)
    top_right_center = (x_coord + vehicle_length, y_coord)
    bottom_right_center = (x_coord + vehicle_length, y_coord - vehicle_width)

    # Calculate wheel footprint corners for each wheel
    return {
        "top_left_wheel_corners": _calculate_wheel_corners_vehicle(top_left_center[0], top_left_center[1], wheel_contact_area),
        "top_right_wheel_corners": _calculate_wheel_corners_vehicle(top_right_center[0], top_right_center[1], wheel_contact_area),
        "bottom_left_wheel_corners": _calculate_wheel_corners_vehicle(bottom_left_center[0], bottom_left_center[1], wheel_contact_area),
        "bottom_right_wheel_corners": _calculate_wheel_corners_vehicle(bottom_right_center[0], bottom_right_center[1], wheel_contact_area),
    }


def interpolate_points_along_line(line_points: list[tuple[float, float, float]], interval: float) -> list[tuple[float, float, float]]:
    """
    Interpolate points along a line at regular intervals using NumPy.

    :param line_points: List of (x, y, z) tuples representing the line
    :param interval: Distance between interpolated points in meters
    :return: List of interpolated points at regular intervals
    """
    import numpy as np

    if len(line_points) < 2:
        return line_points

    # Convert to numpy array for easier manipulation
    points = np.array(line_points)

    # Calculate cumulative distances along the line
    distances = np.zeros(len(points))
    for i in range(1, len(points)):
        segment_length = np.linalg.norm(points[i] - points[i - 1])
        distances[i] = distances[i - 1] + segment_length

    # Total line length
    total_length = distances[-1]

    # Create array of distances at regular intervals
    num_intervals = int(total_length / interval) + 1
    regular_distances = np.linspace(0, total_length, num_intervals)

    # Interpolate x, y, z coordinates at regular intervals
    x_interp = np.interp(regular_distances, distances, points[:, 0])
    y_interp = np.interp(regular_distances, distances, points[:, 1])
    z_interp = np.interp(regular_distances, distances, points[:, 2])

    # Combine back into list of tuples, converting numpy types to regular Python floats
    return [(float(x), float(y), float(z)) for x, y, z in zip(x_interp, y_interp, z_interp)]
