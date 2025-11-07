"""
Real lane tandem load generators for bridge traffic loading.

This module provides functions for generating tandem system loads based on
actual (real) road section geometry, as opposed to theoretical lane distributions.

All functions are independent of the VIKTOR SDK and suitable for use in the core logic layer.
"""

from typing import TYPE_CHECKING, Any

from src.combinations.load_factors import get_alpha_trend_nen_8701, get_psi_nen_8701
from src.integrations.scia_integration.constants.geometry import (
    DEFAULT_LANE_WIDTH,
    MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES,
    TANDEM_START_Y_OFFSET,
    TANDEM_VEHICLE_LENGTH,
    TANDEM_WHEEL_SIZE,
)
from src.integrations.scia_integration.constants.loads import (
    TANDEM_CONTACT_AREA_SIDE,
)
from src.integrations.scia_integration.load_system.lane_calculations import (
    get_reference_period,
)
from src.integrations.scia_integration.load_system.load_value_calculators import (
    calculate_real_tandem_values,
)
from src.integrations.scia_integration.load_system.road_zone_utils import (
    get_number_of_road_zones,
    get_widths_of_two_road_zones,
    obtain_y_coordinates_road,
    obtain_y_coordinates_two_road_zones,
)
from src.integrations.scia_integration.load_system.tandem_sequencer import TANDEM_WHEEL_OFFSETS, tandem_system_sequencer

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


# ========================================================================
# Helper function for tandem wheel creation
# ========================================================================


def _create_tandem_wheels(x_start: float, y_center: float, wheel_size: float) -> list[list[list[float]]]:
    """Helper function to create a tandem's wheel coordinates."""
    wheels = []
    tandem_start_y = y_center - TANDEM_START_Y_OFFSET
    for dx, dy in TANDEM_WHEEL_OFFSETS:
        x0 = x_start + dx
        y0 = tandem_start_y + dy
        wheel_coords = [
            [x0 + wheel_size, y0],
            [x0 + wheel_size, y0 + wheel_size],
            [x0, y0 + wheel_size],
            [x0, y0],
        ]
        wheels.append(wheel_coords)
    return wheels


# ========================================================================
# Helper functions for the real lane positions in case of two road zones
# ========================================================================


def _generate_lanes_bg8000_strategy(y_top: float, width: float, num_lanes: int, lane_width: float) -> list[float]:
    """Generate lanes from bottom upward."""
    if num_lanes <= 0:
        return []

    y_bottom = y_top - width
    lane_centers = []
    for lane_idx in range(num_lanes):
        lane_center = y_bottom + (lane_idx * lane_width) + (lane_width / 2)
        lane_centers.append(lane_center)
    return lane_centers


def _generate_lanes_bg9000_strategy(y_top: float, num_lanes: int, lane_width: float) -> list[float]:
    """Generate lanes from top downward."""
    if num_lanes <= 0:
        return []

    lane_centers = []
    for lane_idx in range(num_lanes):
        lane_start = y_top - (lane_idx * lane_width)
        lane_center = lane_start - (lane_width / 2)
        lane_centers.append(lane_center)
    return lane_centers


def _generate_lanes_bg10000_strategy1(y_top: float, width: float, num_lanes: int, lane_width: float) -> list[float]:
    """Generate lanes from interior to exterior."""
    if num_lanes <= 0:
        return []

    y_bottom = y_top - width
    lane_centers = []
    for lane_idx in range(num_lanes):
        lane_center = y_bottom + (lane_width / 2) + (lane_idx * lane_width)
        lane_centers.append(lane_center)
    return lane_centers


def _generate_lanes_bg10000_strategy2(y_top: float, num_lanes: int, lane_width: float) -> list[float]:
    """Generate lanes from interior to exterior."""
    if num_lanes <= 0:
        return []

    lane_centers = []
    for lane_idx in range(num_lanes):
        lane_center = y_top - (lane_width / 2) - (lane_idx * lane_width)
        lane_centers.append(lane_center)
    return lane_centers


# ========================================================================
# Generation of lane positions for real lane distribution (BG8000)
# ========================================================================


def generate_real_lane_positions_bg8000(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
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
    if width_road <= 0:
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


# ========================================================================
# Generation of lane positions for real lane distribution in case of two road zones
# ========================================================================


def generate_real_lane_positions_two_road_zones(  # noqa: C901
    params: "BridgeParametrization",
    positioning_strategy: str,
    lane_width: float = 3.0,
) -> list[float]:
    """
    Generate Y-positions for traffic lanes on dual carriageway bridges.

    Args:
        params: Bridge parametrization containing load zones data and geometry
        positioning_strategy: Strategy for lane positioning ("bg8000", "bg9000", "bg10000")
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of Y-coordinates for lane centers

    """
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Get widths and top y-coordinates for both road zones
    width_zone_1, width_zone_2 = get_widths_of_two_road_zones(params)
    y_top_zone_1, y_top_zone_2 = obtain_y_coordinates_two_road_zones(params)

    # Validate that widths are positive
    if width_zone_1 <= 0 or width_zone_2 <= 0:
        raise ValueError("Road zone widths must be positive values")

    # Calculate number of complete lanes that fit in each zone
    num_lanes_zone_1 = int(width_zone_1 // lane_width)
    num_lanes_zone_2 = int(width_zone_2 // lane_width)
    # Generate lane center positions based on strategy
    lane_centers = []

    if positioning_strategy == "bg8000":
        if num_lanes_zone_1 > 0:
            lane_centers.extend(_generate_lanes_bg8000_strategy(y_top_zone_1, width_zone_1, num_lanes_zone_1, lane_width))
        if num_lanes_zone_2 > 0:
            lane_centers.extend(_generate_lanes_bg8000_strategy(y_top_zone_2, width_zone_2, num_lanes_zone_2, lane_width))
        lane_centers = sorted(lane_centers)  # Sort lane centers to match the function's return (which is sorted)
    elif positioning_strategy == "bg9000":
        if num_lanes_zone_1 > 0:
            lane_centers.extend(_generate_lanes_bg9000_strategy(y_top_zone_1, num_lanes_zone_1, lane_width))
        if num_lanes_zone_2 > 0:
            lane_centers.extend(_generate_lanes_bg9000_strategy(y_top_zone_2, num_lanes_zone_2, lane_width))

    elif positioning_strategy == "bg10000":
        if num_lanes_zone_1 > 0:
            lane_centers.extend(_generate_lanes_bg10000_strategy1(y_top_zone_1, width_zone_1, num_lanes_zone_1, lane_width))
        if num_lanes_zone_2 > 0:
            lane_centers.extend(_generate_lanes_bg10000_strategy2(y_top_zone_2, num_lanes_zone_2, lane_width))

    else:
        raise ValueError(f"Unknown positioning strategy: {positioning_strategy}")

    return lane_centers


def tandem_systems_real_lanes_bg8000(
    params: "BridgeParametrization",
    length_bridgedeck: float,
    thickness_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate tandem load cases for BG8000 load group based on actual road lanes.

    This function creates separate load cases for each vehicle (tandem system) positioned according
    to the real traffic lanes defined in the bridge's road section. Each vehicle gets its own load case.

    Args:
        params: Bridge parametrization containing load zones data and geometry
        length_bridgedeck: Bridge length in meters
        thickness_bridgedeck: Bridge deck thickness in meters
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of load case dictionaries, where each dictionary contains:
            - load_case: Identifier string (e.g., "BG8001", "BG8002", "BG8003")
            - title: Title string (e.g., "rs 1 - Conf. A", "rs 2 - Conf. A", "rs 3 - Conf. A")
            - wheels: List of wheel coordinates (x, y, z) for the tandem system
            - load: Load intensity in N/m² for the wheels

    Note:
        - Uses real traffic lanes obtained from the actual road section geometry
        - Each vehicle (rs 1, rs 2, rs 3) gets its own load case
        - Load cases are numbered sequentially across all vehicles and x-positions
        - Tandem system dimensions and loads comply with BG8000 requirements
        - All load cases end with "Conf. A" to indicate Configuration A

    """
    wheel_size = TANDEM_CONTACT_AREA_SIDE

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)

    # Get real lane positions (NEW: replaces fixed positions)
    if get_number_of_road_zones(params) == 2:
        lane_y_positions = generate_real_lane_positions_two_road_zones(params, "bg8000", lane_width)
    else:
        lane_y_positions = generate_real_lane_positions_bg8000(params, lane_width)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))

    # Calculate loads based on berekeningsniveau
    load_main, load_second, load_third = calculate_real_tandem_values(params, length_bridgedeck, psi_nen_8701_factor, alpha_trend_factor)

    # Generate separate load cases for each vehicle
    if lane_y_positions:
        prefix = "BG8"
        load_case_counter = 1

        for x in tandem_x_positions:
            # Vehicle 1: Main vehicle (rs 1) - always exists if there are lanes
            wheels_main = []
            y_lane_center = lane_y_positions[0]
            tandem_start_y_main = y_lane_center - TANDEM_START_Y_OFFSET
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

            load_case_main: dict[str, Any] = {
                "load_case": f"{prefix}{load_case_counter:03d}",
                "title": f"rs 1 - Conf. A - x = {x:g} m",
                "wheels": wheels_main,
                "load": load_main,
            }
            results.append(load_case_main)
            load_case_counter += 1

            # Vehicle 2: 200 kN tandem in next lane (rs 2) - if exists
            if len(lane_y_positions) > 1:
                wheels_200 = []
                tandem_start_y_200 = lane_y_positions[1] - TANDEM_START_Y_OFFSET
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

                load_case_200: dict[str, Any] = {
                    "load_case": f"{prefix}{load_case_counter:03d}",
                    "title": f"rs 2 - Conf. A - x = {x:g} m",
                    "wheels": wheels_200,
                    "load": load_second,
                }
                results.append(load_case_200)
                load_case_counter += 1

            # Vehicle 3: 100 kN tandem in next-next lane (rs 3) - if exists
            if len(lane_y_positions) > 2:
                wheels_100 = []
                tandem_start_y_100 = lane_y_positions[2] - TANDEM_START_Y_OFFSET
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

                load_case_100: dict[str, Any] = {
                    "load_case": f"{prefix}{load_case_counter:03d}",
                    "title": f"rs 3 - Conf. A - x = {x:g} m",
                    "wheels": wheels_100,
                    "load": load_third,
                }
                results.append(load_case_100)
                load_case_counter += 1

    return results


# ========================================================================
# Generation of tandem systems for real lane distribution (BG9000)
# ========================================================================


def generate_real_lane_positions_bg9000(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
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
    params: "BridgeParametrization",
    length_bridgedeck: float,
    thickness_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate tandem load cases for BG9000 load group based on actual road lanes.

    This function creates separate load cases for each vehicle (tandem system) positioned according
    to the real traffic lanes defined in the bridge's road section. Each vehicle gets its own load case.

    Args:
        params: Bridge parametrization containing load zones data and geometry
        length_bridgedeck: Bridge length in meters
        thickness_bridgedeck: Bridge deck thickness in meters
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of load case dictionaries, where each dictionary contains:
            - load_case: Identifier string (e.g., "BG9001", "BG9002", "BG9003")
            - title: Title string (e.g., "rs 1 - Conf. B", "rs 2 - Conf. B", "rs 3 - Conf. B")
            - wheels: List of wheel coordinates (x, y, z) for the tandem system
            - load: Load intensity in N/m² for the wheels

    Note:
        - Uses real traffic lanes obtained from the actual road section geometry
        - Each vehicle (rs 1, rs 2, rs 3) gets its own load case
        - Load cases are numbered sequentially across all vehicles and x-positions
        - Tandem system dimensions and loads comply with BG9000 requirements
        - All load cases end with "Conf. B" to indicate Configuration B

    """
    wheel_size = TANDEM_CONTACT_AREA_SIDE

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)

    # Get real lane positions (NEW: replaces fixed positions)
    if get_number_of_road_zones(params) == 2:
        lane_y_positions = generate_real_lane_positions_two_road_zones(params, "bg9000", lane_width)
    else:
        lane_y_positions = generate_real_lane_positions_bg9000(params, lane_width)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))

    # Calculate loads based on berekeningsniveau
    load_main, load_second, load_third = calculate_real_tandem_values(params, length_bridgedeck, psi_nen_8701_factor, alpha_trend_factor)

    # Generate separate load cases for each vehicle
    if lane_y_positions:
        prefix = "BG9"
        load_case_counter = 1

        for x in tandem_x_positions:
            # Vehicle 1: Main vehicle (rs 1) - always exists if there are lanes
            wheels_main = []
            y_lane_center = lane_y_positions[0]
            tandem_start_y_main = y_lane_center - TANDEM_START_Y_OFFSET
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

            load_case_main: dict[str, Any] = {
                "load_case": f"{prefix}{load_case_counter:03d}",
                "title": f"rs 1 - Conf. B - x = {x:g} m",
                "wheels": wheels_main,
                "load": load_main,
            }
            results.append(load_case_main)
            load_case_counter += 1

            # Vehicle 2: 200 kN tandem in next lane (rs 2) - if exists
            if len(lane_y_positions) > 1:
                wheels_200 = []
                tandem_start_y_200 = lane_y_positions[1] - TANDEM_START_Y_OFFSET
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

                load_case_200: dict[str, Any] = {
                    "load_case": f"{prefix}{load_case_counter:03d}",
                    "title": f"rs 2 - Conf. B - x = {x:g} m",
                    "wheels": wheels_200,
                    "load": load_second,
                }
                results.append(load_case_200)
                load_case_counter += 1

            # Vehicle 3: 100 kN tandem in next-next lane (rs 3) - if exists
            if len(lane_y_positions) > 2:
                wheels_100 = []
                tandem_start_y_100 = lane_y_positions[2] - TANDEM_START_Y_OFFSET
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

                load_case_100: dict[str, Any] = {
                    "load_case": f"{prefix}{load_case_counter:03d}",
                    "title": f"rs 3 - Conf. B - x = {x:g} m",
                    "wheels": wheels_100,
                    "load": load_third,
                }
                results.append(load_case_100)
                load_case_counter += 1

    return results


# ========================================================================
# Generation of tandem systems for real lane distribution (BG10000)
# ========================================================================


def generate_real_lane_positions_bg10000(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[float]:
    """
    Generate Y-positions for BG10000 load case: 300 kN in center, 200/100 kN adjacent if width permits.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of Y-coordinates for lane centers. Returns only center lane if width < 9m
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

    # Only add adjacent lanes if we have at least 9m width (3 lanes of 3m each)
    if width_road >= MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES:
        # Left lane (adjacent to center)
        y_left = y_center - lane_width
        # Right lane (adjacent to center)
        y_right = y_center + lane_width
        return [y_center, y_left, y_right]
    # For narrow roads, only return center lane
    return [y_center]


def tandem_systems_real_lanes_bg10000(
    params: "BridgeParametrization",
    length_bridgedeck: float,
    thickness_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate BG10000 load cases: 300 kN tandem in center always, 200/100 kN adjacent only if width permits.

    This function creates separate load cases for each vehicle (tandem system). Each vehicle gets its own
    load case with lane indicators (rs 1, rs 2, rs 3) and configuration designation (Conf. C).

    :param params: Bridge parametrization for load factors and road dimensions
    :param length_bridgedeck: Bridge length in meters
    :param thickness_bridgedeck: Bridge thickness in meters
    :param lane_width: Standard lane width in meters (default 3.0m)
    :returns: List of BG10000 load cases. Each dictionary contains:
        - load_case: Identifier string (e.g., "BG10001", "BG10002", etc.)
        - title: Title string (e.g., "rs 1 - Conf. C", "rs 2 - Conf. C", "rs 3 - Conf. C")
        - wheels: List of wheel coordinates for the tandem system
        - load: Load intensity in N/m²
    :rtype: list[dict[str, Any]]
    """
    wheel_size = TANDEM_WHEEL_SIZE
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)

    # Get real lane positions (NEW: replaces fixed positions)
    if get_number_of_road_zones(params) == 2:
        lane_y_positions = generate_real_lane_positions_two_road_zones(params, "bg10000", lane_width)
    else:
        lane_y_positions = generate_real_lane_positions_bg10000(params, lane_width)

    # If no lanes could be positioned (all zones too narrow), return empty results
    if not lane_y_positions:
        return []

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))

    # Calculate loads based on berekeningsniveau
    load_main, load_second, load_third = calculate_real_tandem_values(params, length_bridgedeck, psi_nen_8701_factor, alpha_trend_factor)

    # Determine how many lanes we have
    num_lanes = len(lane_y_positions)
    y_center = lane_y_positions[0]  # Center lane always exists

    prefix = "BG10"
    results = []
    idx = 1

    # Case 1: Only 1 lane - just create central tandem
    if num_lanes == 1:
        for x in tandem_x_positions:
            # Central 300kN tandem (rs 1)
            wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)

            load_case = {
                "load_case": f"{prefix}{idx:03d}",
                "title": f"rs 1 - Conf. C - x = {x:g} m",
                "wheels": wheels_300,
                "load": load_main,
            }
            results.append(load_case)
            idx += 1
        return results

    # Case 2: Exactly 2 lanes - create center (300 kN) + one adjacent (200 kN)
    if num_lanes == 2:
        y_adjacent = lane_y_positions[1]
        for x in tandem_x_positions:
            # Center vehicle (rs 1)
            wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)
            load_case_center = {
                "load_case": f"{prefix}{idx:03d}",
                "title": f"rs 1 - Conf. C - x = {x:g} m",
                "wheels": wheels_300,
                "load": load_main,
            }
            results.append(load_case_center)
            idx += 1

            # Adjacent vehicle (rs 2)
            wheels_200 = _create_tandem_wheels(x, y_adjacent, wheel_size)
            load_case_adjacent = {
                "load_case": f"{prefix}{idx:03d}",
                "title": f"rs 2 - Conf. C - x = {x:g} m",
                "wheels": wheels_200,
                "load": load_second,
            }
            results.append(load_case_adjacent)
            idx += 1
        return results

    # Case 3: 3 or more lanes - create full configurations sequentially
    y_left = lane_y_positions[1]
    y_right = lane_y_positions[2]

    # First, generate ALL Configuration A load cases (300 kN center, 200 kN left, 100 kN right)
    for x in tandem_x_positions:
        # Center vehicle (rs 1)
        wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)
        load_case_center = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 1 - Conf. C - x = {x:g} m",
            "wheels": wheels_300,
            "load": load_main,
        }
        results.append(load_case_center)
        idx += 1

        # Left vehicle (rs 2) - Configuration A: 200 kN
        wheels_200_left = _create_tandem_wheels(x, y_left, wheel_size)
        load_case_left_a = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 2 - Conf. C - x = {x:g} m",
            "wheels": wheels_200_left,
            "load": load_second,
        }
        results.append(load_case_left_a)
        idx += 1

        # Right vehicle (rs 3) - Configuration A: 100 kN
        wheels_100_right = _create_tandem_wheels(x, y_right, wheel_size)
        load_case_right_a = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 3 - Conf. C - x = {x:g} m",
            "wheels": wheels_100_right,
            "load": load_third,
        }
        results.append(load_case_right_a)
        idx += 1

    # Then, generate ALL Configuration B load cases (300 kN center, 100 kN left, 200 kN right)
    for x in tandem_x_positions:
        # Center vehicle (rs 1)
        wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)
        load_case_center = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 1 - Conf. C - x = {x:g} m",
            "wheels": wheels_300,
            "load": load_main,
        }
        results.append(load_case_center)
        idx += 1

        # Left vehicle (rs 2) - Configuration B: 100 kN
        wheels_100_left = _create_tandem_wheels(x, y_left, wheel_size)
        load_case_left_b = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 2 - Conf. C - x = {x:g} m",
            "wheels": wheels_100_left,
            "load": load_third,
        }
        results.append(load_case_left_b)
        idx += 1

        # Right vehicle (rs 3) - Configuration B: 200 kN
        wheels_200_right = _create_tandem_wheels(x, y_right, wheel_size)
        load_case_right_b = {
            "load_case": f"{prefix}{idx:03d}",
            "title": f"rs 3 - Conf. C - x = {x:g} m",
            "wheels": wheels_200_right,
            "load": load_second,
        }
        results.append(load_case_right_b)
        idx += 1

    return results
