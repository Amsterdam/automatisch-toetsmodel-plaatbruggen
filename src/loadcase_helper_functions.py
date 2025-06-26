from typing import Any

"""
Helper functions for load case logic and manipulation.

This module provides utility functions for working with load cases in the bridge analysis context.

All functions are independent of the VIKTOR SDK and suitable for use in the core logic layer.
"""


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
            for dx, dy in [(0, 0), (1.2, 0), (0, 1.2), (1.2, 1.2)]:
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
            for dx, dy in [(0, 0), (1.2, 0), (0, 1.2), (1.2, 1.2)]:
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
            for dx, dy in [(0, 0), (1.2, 0), (0, 1.2), (1.2, 1.2)]:
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
                for dx, dy in [(0, 0), (1.2, 0), (0, 1.2), (1.2, 1.2)]:
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
