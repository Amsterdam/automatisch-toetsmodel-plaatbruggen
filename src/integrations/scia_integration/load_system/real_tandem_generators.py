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


def generate_real_lane_positions_bg8000_two_road_zones(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[float]:
    """
    Generate y-positions of real traffic lanes for BG8000 load group on dual carriageway bridges.

    This function calculates the y-coordinates for lane centers based on the actual road sections defined
    in the bridge parametrization. It finds the two 'Auto' zones from the load zones data and uses their geometry
    to determine lane positions. Lanes are positioned from the bottom of each road zone upward.

    Args:
        params: Bridge parametrization containing load zones data and geometry
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of Y-coordinates for lane centers, combining lanes from both road zones.
        Each road zone contributes lanes based on its width (3m per lane minimum).

    Raises:
        ValueError: If road widths or lane width is not positive

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

    # Generate lane center positions for all lanes
    lane_centers = []

    # Process first road zone - lanes positioned from bottom upward
    if num_lanes_zone_1 > 0:
        y_bottom_zone_1 = y_top_zone_1 - width_zone_1
        for lane_idx in range(num_lanes_zone_1):
            lane_start = lane_idx * lane_width
            lane_center = lane_start + (lane_width / 2)  # Center of each lane
            lane_centers.append(y_bottom_zone_1 + lane_center)

    # Process second road zone - lanes positioned from bottom upward
    if num_lanes_zone_2 > 0:
        y_bottom_zone_2 = y_top_zone_2 - width_zone_2
        for lane_idx in range(num_lanes_zone_2):
            lane_start = lane_idx * lane_width
            lane_center = lane_start + (lane_width / 2)  # Center of each lane
            lane_centers.append(y_bottom_zone_2 + lane_center)

    return sorted(lane_centers)


def tandem_systems_real_lanes_bg8000(
    params: "BridgeParametrization",
    length_bridgedeck: float,
    thickness_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
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
    wheel_size = TANDEM_CONTACT_AREA_SIDE

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)

    # Get real lane positions (NEW: replaces fixed positions)
    if get_number_of_road_zones(params) == 2:
        lane_y_positions = generate_real_lane_positions_bg8000_two_road_zones(params, lane_width)
    else:
        lane_y_positions = generate_real_lane_positions_bg8000(params, lane_width)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))

    # Calculate loads based on berekeningsniveau
    load_main, load_second, load_third = calculate_real_tandem_values(params, length_bridgedeck, psi_nen_8701_factor, alpha_trend_factor)

    # Only generate for BG8 (first lane position)
    if lane_y_positions:
        y_lane_center = lane_y_positions[0]
        prefix = "BG8"
        for tandem_idx, x in enumerate(tandem_x_positions, 1):
            wheels_main = []
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

            # Add load_case
            load_case: dict[str, Any] = {
                "load_case": f"{prefix}{tandem_idx:03d}",
            }

            # Add 200 kN tandem in next lane (if exists)
            wheels_200 = []
            if len(lane_y_positions) > 1:
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

            # Add 100 kN tandem in next-next lane (if exists)
            wheels_100 = []
            if len(lane_y_positions) > 2:
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

            load_case["loads"] = [
                {"wheels": wheels_main, "load": load_main},
                {"wheels": wheels_200, "load": load_second},
                {"wheels": wheels_100, "load": load_third},
            ]

            results.append(load_case)

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


def generate_real_lane_positions_bg9000_two_road_zones(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[float]:
    """
    Generate y-positions of real traffic lanes for BG9000 load group on dual carriageway bridges.

    This function calculates the y-coordinates for lane centers based on the actual road sections defined
    in the bridge parametrization. It finds the two 'Auto' zones from the load zones data and uses their geometry
    to determine lane positions. Lanes are positioned from the top of each road zone downward (opposite direction
    from BG8000).

    Args:
        params: Bridge parametrization containing load zones data and geometry
        lane_width: Standard lane width in meters (default 3.0m)

    Returns:
        List of Y-coordinates for lane centers, combining lanes from both road zones.
        Each road zone contributes lanes based on its width (3m per lane minimum).
        Lanes are positioned starting from the top y-coordinate working downward.

    Raises:
        ValueError: If road widths or lane width is not positive

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

    # Generate lane center positions for all lanes
    lane_centers = []

    # Process first road zone - lanes positioned from top downward
    if num_lanes_zone_1 > 0:
        for lane_idx in range(num_lanes_zone_1):
            lane_start = y_top_zone_1 - lane_idx * lane_width
            lane_center = lane_start - (lane_width / 2)  # Center of each lane
            lane_centers.append(lane_center)

    # Process second road zone - lanes positioned from top downward
    if num_lanes_zone_2 > 0:
        for lane_idx in range(num_lanes_zone_2):
            lane_start = y_top_zone_2 - lane_idx * lane_width
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
    wheel_size = TANDEM_CONTACT_AREA_SIDE

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)

    # Get real lane positions (NEW: replaces fixed positions)
    if get_number_of_road_zones(params) == 2:
        lane_y_positions = generate_real_lane_positions_bg9000_two_road_zones(params, lane_width)
    else:
        lane_y_positions = generate_real_lane_positions_bg9000(params, lane_width)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))

    # Calculate loads based on berekeningsniveau
    load_main, load_second, load_third = calculate_real_tandem_values(params, length_bridgedeck, psi_nen_8701_factor, alpha_trend_factor)

    # Only generate for BG9 (first lane position)
    if lane_y_positions:
        y_lane_center = lane_y_positions[0]
        prefix = "BG9"
        for tandem_idx, x in enumerate(tandem_x_positions, 1):
            wheels_main = []
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

            # Add load_case
            load_case: dict[str, Any] = {
                "load_case": f"{prefix}{tandem_idx:03d}",
            }

            # Add 200 kN tandem in next lane (if exists)
            wheels_200 = []
            if len(lane_y_positions) > 1:
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

            # Add 100 kN tandem in next-next lane (if exists)
            wheels_100 = []
            if len(lane_y_positions) > 2:
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

            load_case["loads"] = [
                {"wheels": wheels_main, "load": load_main},
                {"wheels": wheels_200, "load": load_second},
                {"wheels": wheels_100, "load": load_third},
            ]

            results.append(load_case)

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


def generate_real_lane_positions_bg10000_two_road_zones(
    params: "BridgeParametrization",
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[float]:
    """
    Generate Y-positions for BG10000 load case on dual carriageway bridges.

    This function positions notional lanes starting from the interior (center-facing side)
    of each road zone and working outward toward the bridge edges. The highest loaded lane
    (300 kN tandem) is placed closest to the center of the bridge, with decreasing loads
    (200 kN, 100 kN) as lanes move toward the edges.

    The function places lanes on both road zones starting from their interior-facing edges
    (the edges closest to the bridge center) and working outward:
    - Zone 1 (bottom zone): from bottom edge (interior) upward toward top edge
    - Zone 2 (top zone): from top edge (interior) downward toward bottom edge

    :param params: Bridge parametrization containing load zones data and geometry
    :type params: BridgeParametrization
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of Y-coordinates for lane centers, ordered from interior to exterior
    :rtype: list[float]
    :raises ValueError: If road widths or lane width is not positive
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

    # Calculate bottom y-coordinates for both zones
    y_bottom_zone_1 = y_top_zone_1 - width_zone_1

    # Generate lane center positions
    lane_centers = []

    # Process first road zone (bottom zone) - lanes positioned from top (interior) downward (toward edge)
    # The top of the bottom zone faces the center of the bridge
    if num_lanes_zone_1 > 0:
        for lane_idx in range(num_lanes_zone_1):
            # Place lane center starting from half a lane width below the top edge, then each subsequent lane is one full lane width lower
            lane_center = y_bottom_zone_1 + (lane_width / 2) + (lane_idx * lane_width)
            lane_centers.append(lane_center)

    # Process second road zone (top zone) - lanes positioned from top (interior) downward (toward edge)
    # The top of the top zone (which is actually the lower boundary of zone 2) faces the center
    if num_lanes_zone_2 > 0:
        for lane_idx in range(num_lanes_zone_2):
            # Place lane center starting from half a lane width below the top edge, then each subsequent lane is one full lane width lower
            lane_center = y_top_zone_2 - (lane_width / 2) - (lane_idx * lane_width)
            lane_centers.append(lane_center)

    return lane_centers


def tandem_systems_real_lanes_bg10000(  # noqa: C901, PLR0912, PLR0915
    params: "BridgeParametrization",
    length_bridgedeck: float,
    thickness_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate BG10000 load cases: 300 kN tandem in center always, 200/100 kN adjacent only if width permits.

    :param params: Bridge parametrization for load factors and road dimensions
    :param length_bridgedeck: Bridge length in meters
    :param thickness_bridgedeck: Bridge thickness in meters
    :param lane_width: Standard lane width in meters (default 3.0m)
    :returns: List of BG10000 load cases. For narrow roads (<9m), only central tandem
    :rtype: list[dict[str, Any]]
    """
    wheel_size = TANDEM_WHEEL_SIZE
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)

    # Get real lane positions (NEW: replaces fixed positions)
    if get_number_of_road_zones(params) == 2:
        lane_y_positions = generate_real_lane_positions_bg10000_two_road_zones(params, lane_width)
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
            # Central 300kN tandem (always present)
            wheels_300 = []
            tandem_start_y_300 = y_center - TANDEM_START_Y_OFFSET
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

            load_case = {
                "load_case": f"{prefix}{idx:03d}",
                "loads": [{"wheels": wheels_300, "load": load_main}],
            }
            results.append(load_case)
            idx += 1
        return results

    # Case 2: Exactly 2 lanes - create center (300 kN) + one adjacent (200 kN)
    if num_lanes == 2:
        y_adjacent = lane_y_positions[1]
        for x in tandem_x_positions:
            wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)
            wheels_200 = _create_tandem_wheels(x, y_adjacent, wheel_size)

            load_case = {
                "load_case": f"{prefix}{idx:03d}",
                "loads": [
                    {"wheels": wheels_300, "load": load_main},
                    {"wheels": wheels_200, "load": load_second},
                ],
            }
            results.append(load_case)
            idx += 1
        return results

    # Case 3: 3 or more lanes - create full configurations sequentially
    y_left = lane_y_positions[1]
    y_right = lane_y_positions[2]

    # First, generate ALL Configuration A load cases (300 kN center, 200 kN left, 100 kN right)
    for x in tandem_x_positions:
        # Central 300kN tandem
        wheels_300 = []
        tandem_start_y_300 = y_center - TANDEM_START_Y_OFFSET
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

        # Configuration A: 200 kN left, 100 kN right
        wheels_200_left = []
        tandem_start_y_200_left = y_left - TANDEM_START_Y_OFFSET
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
        tandem_start_y_100_right = y_right - TANDEM_START_Y_OFFSET
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

    # Then, generate ALL Configuration B load cases (300 kN center, 100 kN left, 200 kN right)
    for x in tandem_x_positions:
        # Central 300kN tandem
        wheels_300 = []
        tandem_start_y_300 = y_center - TANDEM_START_Y_OFFSET
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

        # Configuration B: 100 kN left, 200 kN right
        wheels_100_left = []
        tandem_start_y_100_left = y_left - TANDEM_START_Y_OFFSET
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
        tandem_start_y_200_right = y_right - TANDEM_START_Y_OFFSET
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
