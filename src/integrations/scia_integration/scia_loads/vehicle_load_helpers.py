"""
Vehicle load helper functions for SCIA model building.

This module provides utilities for calculating vehicle load locations and
interpolating points along lines for vehicle load application.
"""


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
    # Order: bottom-right, top-right, top-left, bottom-left
    return [
        (center_x + half_area, center_y - half_area, 0.0),  # bottom-right
        (center_x + half_area, center_y + half_area, 0.0),  # top-right
        (center_x - half_area, center_y + half_area, 0.0),  # top-left
        (center_x - half_area, center_y - half_area, 0.0),  # bottom-left
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

    # Calculate wheel footprint corners for each wheel in the correct order
    return {
        "bottom_right_wheel_corners": _calculate_wheel_corners_vehicle(bottom_right_center[0], bottom_right_center[1], wheel_contact_area),
        "top_right_wheel_corners": _calculate_wheel_corners_vehicle(top_right_center[0], top_right_center[1], wheel_contact_area),
        "top_left_wheel_corners": _calculate_wheel_corners_vehicle(top_left_center[0], top_left_center[1], wheel_contact_area),
        "bottom_left_wheel_corners": _calculate_wheel_corners_vehicle(bottom_left_center[0], bottom_left_center[1], wheel_contact_area),
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
