"""
Helper functions for load case logic and manipulation.

This module provides utility functions for working with load cases in the bridge analysis context.

All functions are independent of the VIKTOR SDK and suitable for use in the core logic layer.
"""

from typing import Any

from src.common.materials import get_material_densities

# ========================================================================
# THEORETICAL TRAFFIC LANE INTEGRATION
# ========================================================================
# These functions connect tandem loads to theoretical traffic lanes from
# src.geometry.load_zone_geometry for proper structural engineering analysis.


def generate_theoretical_lane_positions(width_bridgedeck: float, lane_width: float = 3.0) -> list[float]:
    """
    Generate Y-positions for theoretical traffic lanes across bridge width.

    Creates lane center positions based on geometric division of bridge width.
    This provides the foundation for theoretical lane-based tandem loading.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of Y-coordinates for lane centers
    :rtype: list[float]
    :raises ValueError: If bridge_width or lane_width is not positive

    Examples:
        >>> generate_theoretical_lane_positions(30.0, 3.0)
        [1.5, 4.5, 7.5, 10.5, 13.5, 16.5, 19.5, 22.5, 25.5, 28.5]

        >>> generate_theoretical_lane_positions(10.0, 3.0)
        [1.5, 4.5, 7.5]  # 3 complete lanes, 1m rest ignored

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
        lane_centers.append(lane_center)

    return lane_centers


# Standard tandem wheel offsets from bottom left corner
TANDEM_WHEEL_OFFSETS = [(0, 0), (1.2, 0), (0, 2), (1.2, 2)]


def tandem_systems_theoretical_lanes(
    length_bridgedeck: float, width_bridgedeck: float, thickness_bridgedeck: float, lane_width: float = 3.0
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
    load = 300 / (0.4 * 0.4)  # 300 kN over 0.4m x 0.4m = 1,875,000 N/m²
    wheel_size = 0.4

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)

    # Get theoretical lane positions (NEW: replaces fixed positions)
    lane_y_positions = generate_theoretical_lane_positions(width_bridgedeck, lane_width)

    results = []
    load_case_number = 1

    # Generate load cases for each lane position
    for y_lane_center in lane_y_positions:
        for x in tandem_x_positions:
            wheels = []

            # Position tandem system at lane center
            # Tandem dimensions: 1.2m x 1.2m (2x2 wheels with 1.2m spacing)
            tandem_start_y = y_lane_center - 0.6  # Center the 1.2m tandem in lane

            # Four wheels per tandem system, spaced 1.2m apart in x, 1.2m apart in y
            for dx, dy in TANDEM_WHEEL_OFFSETS:
                x0 = x + dx
                y0 = tandem_start_y + dy

                # Clockwise wheel coordinates: bottom right, top right, top left, bottom left
                wheel_coords = [
                    [x0 + wheel_size, y0],  # bottom right
                    [x0 + wheel_size, y0 + wheel_size],  # top right
                    [x0, y0 + wheel_size],  # top left
                    [x0, y0],  # bottom left
                ]
                wheels.append(wheel_coords)

            results.append(
                {
                    "load_case": f"TH{6000 + load_case_number:04d}",  # TH = Theoretical
                    "wheels": wheels,
                    "load": load,
                }
            )
            load_case_number += 1

    return results


# ========================================================================
# FUTURE INTEGRATION ARCHITECTURE
# ========================================================================
# The following function signatures are planned for future implementation:


def tandem_systems_shiftable_lanes(
    length_bridgedeck: float, width_bridgedeck: float, thickness_bridgedeck: float, num_shift_positions: int = 5
) -> list[dict[str, Any]]:
    """
    FUTURE IMPLEMENTATION: Generate tandem loads with freely shiftable lane positions.

    This will enable testing all possible transverse positions to find critical
    loading scenarios for maximum structural effects.

    :param num_shift_positions: Number of transverse positions to test
    :returns: Load cases with shifting tandem positions for optimization

    Planned Features:
        - Multiple transverse positions per longitudinal location
        - Load case naming: "SH6001", "SH6002", etc. (SH = Shiftable)
        - Integration with influence line analysis
        - Automatic critical position detection
    """
    # TODO: Implement in Phase 2
    # This will generate tandems at multiple Y positions per X position
    # for comprehensive coverage and critical loading analysis
    raise NotImplementedError("Shiftable lanes implementation planned for Phase 2")


def tandem_systems_actual_lanes(length_bridgedeck: float, actual_lane_positions: list[float], thickness_bridgedeck: float) -> list[dict[str, Any]]:
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
    # Always include the mid-span position
    mid_span_position_ = length_bridgedeck / 2
    end_span_position = length_bridgedeck - start_of_lanes - 1.6

    lane_length = length_bridgedeck - (2 * start_of_lanes)

    aantal_tandems = (lane_length - 1.6) // dx  # Calculate number of tandem systems based on spacing
    for i in range(int(aantal_tandems)):
        position = start_of_lanes + (i * dx)
        if position <= (length_bridgedeck - start_of_lanes - 1.6):  # Ensure position does not exceed end span
            tandem_systems.append(position)
    # Ensure mid-span position is included
    if mid_span_position_ not in tandem_systems:
        tandem_systems.append(mid_span_position_)
    # Ensure end-span position is included
    if end_span_position not in tandem_systems:
        tandem_systems.append(end_span_position)
    return tandem_systems


def tandem_systems_axes_single_lane(length_bridgedeck: float, width_bridgedeck: float, thickness_bridgedeck: float) -> list[dict[str, Any]]:
    """
    Calculate the wheel print coordinates and loads for each tandem system in a single notional lane.

    Args:
        length_bridgedeck (float): The length of the bridge deck in meters.
        width_bridgedeck (float): The width of the bridge deck in meters.
        thickness_bridgedeck (float): The thickness of the bridge deck in meters.

    Returns:
        list[dict[str, Any]]: List of dicts, each with keys: 'load_case', 'wheels', 'load'.
            'wheels' is a list of four lists [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] for each wheel (clockwise).

    """
    load = 300 / (0.4 * 0.4)
    wheel_size = 0.4
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
    y_base = calculate_start_of_lanes(thickness_bridgedeck)
    y_second = y_base + (width_bridgedeck - 2 * y_base - 2.4)
    y_positions = [y_base, y_second]
    results = []
    load_case_number = 1
    for y in y_positions:
        for x in tandem_x_positions:
            wheels = []
            # Four wheels per tandem system, spaced 1.2 m apart in x, 1.2 m apart in y
            for dx, dy in TANDEM_WHEEL_OFFSETS:
                x0 = x + dx
                y0 = y + dy
                # Clockwise: bottom right, top right, top left, bottom left
                wheel_coords = [
                    [x0 + wheel_size, y0],  # bottom right
                    [x0 + wheel_size, y0 + wheel_size],  # top right
                    [x0, y0 + wheel_size],  # top left
                    [x0, y0],  # bottom left
                ]
                wheels.append(wheel_coords)
            results.append(
                {
                    "load_case": f"BG{6000 + load_case_number:04d}",
                    "wheels": wheels,
                    "load": load,
                }
            )
            load_case_number += 1
    return results


def tandem_systems_axes_double_lane(length_bridgedeck: float, width_bridgedeck: float, thickness_bridgedeck: float) -> list[dict[str, Any]]:
    """
    Calculate the wheel print coordinates and loads for each load case in a double notional lane case.

    Each load case consists of two tandem systems at the same x-position: one on each lane.
    For each configuration, the exterior lane receives 300 kN and the interior 200 kN, then the lanes are swapped.

    Args:
        length_bridgedeck (float): The length of the bridge deck in meters.
        width_bridgedeck (float): The width of the bridge deck in meters.
        thickness_bridgedeck (float): The thickness of the bridge deck in meters.

    Returns:
        results(list[dict[str, object]]): List of dicts, each with keys: 'load_case', 'tandems', where 'tandems' is a list of two dicts
        (one per lane), each with keys 'wheels', 'load', 'lane'.

    """
    wheel_size = 0.4
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
    _, lane_width = amount_of_notional_lanes(width_bridgedeck)
    y_base = calculate_start_of_lanes(thickness_bridgedeck)
    y_second = y_base + lane_width
    y_positions = [y_base, y_second]  # [left lane, right lane]
    results = []
    load_case_number = 1
    # First configuration: 300 kN on left (exterior), 200 kN on right (interior)
    for x in tandem_x_positions:
        tandems = []
        for lane_idx, (y, load) in enumerate(zip(y_positions, [300, 200])):
            wheels = []
            for dx, dy in TANDEM_WHEEL_OFFSETS:
                x0 = x + dx
                y0 = y + dy
                wheel_coords = [
                    [x0 + wheel_size, y0],
                    [x0 + wheel_size, y0 + wheel_size],
                    [x0, y0 + wheel_size],
                    [x0, y0],
                ]
                wheels.append(wheel_coords)
            tandems.append(
                {
                    "wheels": wheels,
                    "load": load / (0.4 * 0.4),
                    "lane": lane_idx + 1,
                }
            )
        results.append(
            {
                "load_case": f"BG{6000 + load_case_number:04d}",
                "tandems": tandems,
            }
        )
        load_case_number += 1
    # Second configuration: 300 kN on right (exterior), 200 kN on left (interior)
    for x in tandem_x_positions:
        tandems = []
        for lane_idx, (y, load) in enumerate(zip(y_positions, [200, 300])):
            wheels = []
            for dx, dy in TANDEM_WHEEL_OFFSETS:
                x0 = x + dx
                y0 = y + dy
                wheel_coords = [
                    [x0 + wheel_size, y0],
                    [x0 + wheel_size, y0 + wheel_size],
                    [x0, y0 + wheel_size],
                    [x0, y0],
                ]
                wheels.append(wheel_coords)
            tandems.append(
                {
                    "wheels": wheels,
                    "load": load / (0.4 * 0.4),
                    "lane": lane_idx + 1,
                }
            )
        results.append(
            {
                "load_case": f"BG{6000 + load_case_number:04d}",
                "tandems": tandems,
            }
        )
        load_case_number += 1
    return results


def tandem_systems_axes_more_lanes(length_bridgedeck: float, width_bridgedeck: float, thickness_bridgedeck: float) -> list[dict[str, Any]]:
    """
    Calculate the wheel print coordinates and loads for each load case in a three notional lane case (wide bridge).

    Each load case consists of three tandem systems at the same x-position: one on each lane.
    Four configurations:
    1. 300 kN on left, 200 kN center, 100 kN right
    2. 100 kN on left, 200 kN center, 300 kN right
    3. 200 kN on left, 300 kN center, 100 kN right
    4. 100 kN on left, 300 kN center, 200 kN right

    Args:
        length_bridgedeck (float): The length of the bridge deck in meters.
        width_bridgedeck (float): The width of the bridge deck in meters.
        thickness_bridgedeck (float): The thickness of the bridge deck in meters.

    Returns:
        list[dict[str, object]]: List of dicts, each with keys: 'load_case', 'tandems', where 'tandems' is a list of three dicts (one per lane),
            each with keys 'wheels', 'load', 'lane'.

    """
    wheel_size = 0.4
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck)
    _, lane_width = amount_of_notional_lanes(width_bridgedeck)
    y_base = calculate_start_of_lanes(thickness_bridgedeck)
    y_positions = [y_base + i * lane_width for i in range(3)]
    results = []
    load_case_number = 1
    # Define the four configurations
    configurations = [
        [300, 200, 100],  # 300 kN on left
        [100, 200, 300],  # 300 kN on right
        [200, 300, 100],  # 300 kN in center, 200 left, 100 right
        [100, 300, 200],  # 300 kN in center, 100 left, 200 right
    ]
    for config in configurations:
        for x in tandem_x_positions:
            tandems = []
            for lane_idx, (y, load) in enumerate(zip(y_positions, config)):
                wheels = []
                for dx, dy in TANDEM_WHEEL_OFFSETS:
                    x0 = x + dx
                    y0 = y + dy
                    wheel_coords = [
                        [x0 + wheel_size, y0],
                        [x0 + wheel_size, y0 + wheel_size],
                        [x0, y0 + wheel_size],
                        [x0, y0],
                    ]
                    wheels.append(wheel_coords)
                tandems.append(
                    {
                        "wheels": wheels,
                        "load": load / (0.4 * 0.4),
                        "lane": lane_idx + 1,
                    }
                )
            results.append(
                {
                    "load_case": f"BG{6000 + load_case_number:04d}",
                    "tandems": tandems,
                }
            )
            load_case_number += 1
    return results

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