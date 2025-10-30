"""
Road zone utility functions for bridge load analysis.

This module provides functions for extracting road zone information from
bridge parametrization, including zone counts, widths, and coordinates.
"""

from typing import TYPE_CHECKING, Any

from src.geometry.load_zone_geometry import (
    LoadZoneData,
    calculate_zone_geometry_properties,
    get_bridge_geom_data,
    get_load_zones_data_from_params,
)
from src.integrations.scia_integration.load_system.scia_load_generators import extract_bridge_dimensions

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization


def extract_auto_zone_y_coord(zone: LoadZoneData) -> float:
    """
    Extract the top y-coordinate of an auto zone.

    This function retrieves the top y-coordinate from the zone's y_coords_top_current_zone attribute.
    If the attribute is not available or empty, it returns 0.0.

    :param zone: The load zone object containing y-coordinates
    :type zone: BridgeParametrization
    :returns: The top y-coordinate of the auto zone, or 0.0 if not available
    :rtype: float
    """
    y_coords = getattr(zone, "y_coords_top_current_zone", [])
    return float(y_coords[0]) if y_coords else 0.0


def get_number_of_road_zones(params: "BridgeParametrization") -> int:
    """
    Determine the number of road zones defined by the user.

    This function counts the number of load zones with zone_type "Auto" in the
    load zones array, which represents the actual road/traffic zones on the bridge.
    Typically, there will be 1 or 2 road zones (one for a single carriageway,
    or two for dual carriageways separated by a median/tramway/grass strip).

    :param params: Bridge parametrization containing load zones data
    :type params: BridgeParametrization
    :returns: Number of road zones (zones with zone_type "Auto")
    :rtype: int
    """
    load_zones_data = get_load_zones_data_from_params(params)

    # Count zones where zone_type is "Auto"
    return sum(1 for zone in load_zones_data if zone.zone_type == "Auto")


def _find_auto_zones_with_indices(load_zones_data: list) -> list[tuple[int, Any]]:
    """
    Find all auto zones and return them with their indices.

    This helper function filters the load zones data to find all zones with zone_type "Auto"
    and returns them along with their original indices in the load zones array.

    :param load_zones_data: List of load zone objects
    :type load_zones_data: list
    :returns: List of tuples containing (zone_index, zone_object) for each auto zone
    :rtype: list[tuple[int, any]]
    """
    return [(i, zone) for i, zone in enumerate(load_zones_data) if zone.zone_type == "Auto"]


def _calculate_zone_width(  # noqa: PLR0913
    zone_position: int,
    zone_index: int,
    zone: LoadZoneData,
    load_zones_data: list,
    auto_zones_with_indices: list[tuple[int, Any]],
    total_bridge_width: float,
) -> float:
    """
    Calculate the width of a specific auto zone.

    This helper function calculates the width of an auto zone by:
    1. Accumulating widths of all zones before it
    2. Getting the zone's d1_width value
    3. If the zone is the last zone in the array, calculating remaining width

    :param zone_position: Position of this zone in the auto zones list (0-indexed)
    :type zone_position: int
    :param zone_index: Index of this zone in the full load zones array
    :type zone_index: int
    :param zone: The zone object to calculate width for
    :type zone: LoadZoneData
    :param load_zones_data: Complete list of all load zones
    :type load_zones_data: list
    :param auto_zones_with_indices: List of all auto zones with their indices
    :type auto_zones_with_indices: list[tuple[int, Any]]
    :param total_bridge_width: Total width of the bridge in meters
    :type total_bridge_width: float
    :returns: Width of the zone in meters
    :rtype: float
    """
    cumulative_width = 0.0

    # For each auto zone, accumulate widths of all zones before it
    if zone_position == 0:
        # First auto zone: accumulate all zones before it
        for i in range(zone_index):
            prev_zone = load_zones_data[i]
            width_value = getattr(prev_zone, "d1_width", None)
            prev_width = float(width_value) if isinstance(width_value, (int, float)) else 0.0
            cumulative_width += prev_width
    else:
        # Second auto zone: accumulate all zones between first and second auto zone
        # (including the first auto zone itself)
        prev_auto_index = auto_zones_with_indices[zone_position - 1][0]
        for i in range(prev_auto_index, zone_index):
            prev_zone = load_zones_data[i]
            width_value = getattr(prev_zone, "d1_width", None)
            prev_width = float(width_value) if isinstance(width_value, (int, float)) else 0.0
            cumulative_width += prev_width

    # Get the width of this auto zone
    width_value = getattr(zone, "d1_width", None)
    zone_width = float(width_value) if isinstance(width_value, (int, float)) else 0.0

    # If this auto zone is the last zone in the array, calculate remaining width
    if zone_index == len(load_zones_data) - 1:
        zone_width = total_bridge_width - cumulative_width

    return zone_width


def get_widths_of_two_road_zones(params: "BridgeParametrization") -> tuple[float, float]:
    """
    Get the widths of two road zones when the user has defined two auto zones.

    This function extracts the d1_width values for the two road zones (zone_type "Auto").
    If the second auto zone is the last zone in the array, its width is calculated as
    the remaining width of the bridge after accounting for all previous zones.

    :param params: Bridge parametrization containing load zones data and bridge geometry
    :type params: BridgeParametrization
    :returns: Tuple of (width_1, width_2) for the two road zones in meters
    :rtype: tuple[float, float]
    :raises ValueError: If fewer than two road zones are defined
    """
    load_zones_data = get_load_zones_data_from_params(params)
    bridge_geom_data = get_bridge_geom_data(params)

    if bridge_geom_data is None:
        raise ValueError("Bridge geometry data is not available")

    # Update load zones data with geometry properties
    load_zones_data = calculate_zone_geometry_properties(load_zones_data, bridge_geom_data)

    # Extract bridge dimensions
    dims = extract_bridge_dimensions(params)

    # Find all auto zones using helper function
    auto_zones_with_indices = _find_auto_zones_with_indices(load_zones_data)

    if len(auto_zones_with_indices) < 2:
        raise ValueError(f"Expected 2 road zones, but found {len(auto_zones_with_indices)}")

    # Extract widths for the first two auto zones using helper function
    widths = []
    for zone_position, (zone_index, zone) in enumerate(auto_zones_with_indices[:2]):
        zone_width = _calculate_zone_width(
            zone_position=zone_position,
            zone_index=zone_index,
            zone=zone,
            load_zones_data=load_zones_data,
            auto_zones_with_indices=auto_zones_with_indices,
            total_bridge_width=dims.total_width,
        )
        widths.append(zone_width)

    width_1, width_2 = widths[0], widths[1]

    return width_1, width_2


def obtain_y_coordinates_road(
    params: "BridgeParametrization",
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

    # Extract bridge dimensions
    dims = extract_bridge_dimensions(params)

    # Find the 'Auto' zone and get its y-coordinates and width
    # It can be that the auto zone is the last zone, in this case it has no valid d1_width
    # so we need to accumulate the widths of the previous zones and use the total bridge width to find the d1_width
    cumulative_width = 0.0
    for zone in load_zones_data_params:
        # Get d1_width, ensure it's a valid number
        width_value = getattr(zone, "d1_width", None)
        d1_width = float(width_value) if isinstance(width_value, (int, float)) else 0.0

        # if zone is not last zone in load_zones_data_params, accumulate widths
        if zone != load_zones_data_params[-1]:
            cumulative_width += d1_width
        # if it is the last zone the width is the remaining width of the bridge
        elif zone == load_zones_data_params[-1]:
            d1_width = dims.total_width - cumulative_width

        if zone.zone_type == "Auto":
            # Use the helper function to extract y-coordinate
            y_coord = extract_auto_zone_y_coord(zone)
            return y_coord, d1_width

    return 0.0, 0.0


def obtain_y_coordinates_two_road_zones(
    params: "BridgeParametrization",
) -> tuple[float, float]:
    """
    Obtain the top y-coordinates of two road zones from the load zones data.

    This helper function finds the two auto zones (zone_type "Auto") and extracts
    the top y-coordinate for each zone. These coordinates are used to position
    traffic lanes on dual carriageway bridges where there are two separate roadways.

    :param params: Bridge parametrization containing load zones data
    :type params: BridgeParametrization
    :returns: Tuple containing (y_top_zone_1, y_top_zone_2) - the top y-coordinates
              for the first and second road zones. Returns (0.0, 0.0) if zones are not found.
    :rtype: tuple[float, float]

    Note:
        If fewer than two road zones are found or bridge geometry is unavailable,
        returns (0.0, 0.0) as a safe default.

    """
    # Obtain load zones data and bridge geometry
    load_zones_data_params = get_load_zones_data_from_params(params)
    bridge_geom_data = get_bridge_geom_data(params)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return 0.0, 0.0

    # Update load zones data with geometry properties
    load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

    # Find all auto zones and extract their y-coordinates
    auto_zone_y_coords: list[float] = []

    for zone in load_zones_data_params:
        if zone.zone_type == "Auto":
            # Use the helper function to extract y-coordinate
            y_coord = extract_auto_zone_y_coord(zone)
            auto_zone_y_coords.append(y_coord)

    # Return the first two y-coordinates if available, otherwise default to (0.0, 0.0)
    if len(auto_zone_y_coords) >= 2:
        return auto_zone_y_coords[0], auto_zone_y_coords[1]

    return 0.0, 0.0
