"""
Helper functions for load case logic and manipulation.

This module provides utility functions for working with load cases in the bridge analysis context.

All functions are independent of the VIKTOR SDK and suitable for use in the core logic layer.
"""

from typing import TYPE_CHECKING, Any

from src.common.materials import get_material_densities
from src.geometry.load_zone_geometry import calculate_zone_geometry_properties, get_bridge_geom_data, get_load_zones_data_from_params 
from src.geometry.model_creator import LoadZoneGeometryData

# Type alias to avoid importing from app layer
BridgeParametrization = Any

if TYPE_CHECKING:
    from .scia_model_interface import SciaModelBuilder


# ========================================================================
# UNIFORMLY DISTRIBUTED TRAFFIC LOADS (UDL) FOR MAIN NOTIONAL LANES
# ========================================================================
def create_udl_traffic_loads(  # noqa: PLR0913
    length_bridgedeck: float,
    width_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = 3.0,
    udl_value: float = 9000.0,
) -> dict[str, dict[str, Any]]:
    """
    Create UDLs (9 kN/m²) for the three main notional lanes, matching BG8000 (left), BG9000 (right), BG10000 (center).

    :param length_bridgedeck: Bridge length in meters
    :param width_bridgedeck: Bridge width in meters
    :param width_firstsegment_zone3: Zone 3 width (for lane offset)
    :param width_firstsegment_zone2: Zone 2 width (for lane offset)
    :param lane_width: Lane width in meters (default 3.0)
    :param udl_value: UDL value in N/m² (default 9000.0)
    :returns: Dict with keys BG4001, BG4002, BG4003, each containing lane polygon and load value
    """
    results = {}
    rest_value = 2500.0

    # BG4001: leftmost lane (BG8000 logic)
    y_positions_left = generate_theoretical_lane_positions_bg8000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_left:
        y_center = y_positions_left[0]
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        main_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        rest_polygons = []
        rest_polygons.append(
            [
                (0.0, y_max, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (length_bridgedeck, width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (0.0, width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            ]
        )
        results["BG4001"] = {
            "main": {"polygon": main_polygon, "load": udl_value},
            "rest": [{"polygon": p, "load": rest_value} for p in rest_polygons],
        }

    # BG4002: rightmost lane (BG9000 logic)
    y_positions_right = generate_theoretical_lane_positions_bg9000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_right:
        y_center = y_positions_right[0]
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        main_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        rest_polygons = []
        rest_polygons.append(
            [
                (0.0, -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (0.0, y_min, 0.0),
            ]
        )
        results["BG4002"] = {
            "main": {"polygon": main_polygon, "load": udl_value},
            "rest": [{"polygon": p, "load": rest_value} for p in rest_polygons],
        }

    # BG4003: center lane (BG10000 logic)
    y_positions_center = generate_theoretical_lane_positions_bg10000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_center:
        y_center = y_positions_center[0]
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        main_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        rest_polygons = []
        rest_polygons.append(
            [
                (0.0, y_max, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (length_bridgedeck, width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (0.0, width_bridgedeck - 0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            ]
        )
        rest_polygons.append(
            [
                (0.0, -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, -0.5 * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (0.0, y_min, 0.0),
            ]
        )
        results["BG4003"] = {
            "main": {"polygon": main_polygon, "load": udl_value},
            "rest": [{"polygon": p, "load": rest_value} for p in rest_polygons],
        }

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

    Future Integration Points:
        - Phase 2: Add lane shifting capability for critical loading
        - Phase 3: Connect to params.input.belastingzones actual lanes
    """
    wheel_size = 0.4

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)

    # Get theoretical lane positions (NEW: replaces fixed positions)
    lane_y_positions = generate_theoretical_lane_positions_bg8000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

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
                {"wheels": wheels_main, "load": 300000 / (0.4 * 0.4)},
                {"wheels": wheels_200, "load": 200000 / (0.4 * 0.4)},
                {"wheels": wheels_100, "load": 100000 / (0.4 * 0.4)},
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
# FUTURE INTEGRATION ARCHITECTURE
# ========================================================================
# The following function signatures are planned for future implementation:


def tandem_systems_actual_lanes(
    length_bridgedeck: float,
    actual_lane_positions: list[float],
    thickness_bridgedeck: float,
) -> list[dict[str, Any]]:
    """
    FUTURE IMPLEMENTATION: Generate tandem loads based on actual traffic lane data.

    This will connect to params.input.belastingzones to use real lane configurations
    from the bridge parametrization for practical loading scenarios.

    :param actual_lane_positions: Y-coordinates from load zone car lanes
    :returns: Load cases based on actual lane configuration

    Planned Features:
        - Integration with params.input.belastingzones
        - Load case naming: "AC6001", "AC6002", etc. (AC = Actual)
        - Variable lane widths support
        - Different load intensities per lane type
    """
    # TODO: Implement in Phase 3
    # This will extract lane positions from params.input.belastingzones
    # and generate tandems at actual traffic lane locations
    raise NotImplementedError("Actual lanes implementation planned for Phase 3")


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
        amount = 1
        width_per_lane = 3.0
    elif 5.4 <= width_bridgedeck < 6.0:
        amount = 2
        width_per_lane = width_bridgedeck / 2
    else:
        amount = int(width_bridgedeck // 3)
        width_per_lane = 3.0
    return amount, width_per_lane


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
        if not material or not isinstance(thickness, (int, float)):
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

    if not material or not isinstance(thickness, (int, float)):
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
