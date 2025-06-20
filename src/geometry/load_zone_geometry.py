"""Module for geometric calculations related to load zones."""

from typing import TypedDict


# Define a protocol for the expected structure of zone_param_data
class LoadZoneDataRow(TypedDict, total=False):
    """
    TypedDict representing the structure of a single row of load zone data
    as passed from the controller to the plotting/geometry functions.
    """

    zone_type: str
    pavement_thickness: float  # New field for pavement thickness
    pavement_material: str  # New field for pavement material
    d1_width: float | None
    d2_width: float | None
    d3_width: float | None
    d4_width: float | None
    d5_width: float | None
    d6_width: float | None
    d7_width: float | None
    d8_width: float | None
    d9_width: float | None
    d10_width: float | None
    d11_width: float | None
    d12_width: float | None
    d13_width: float | None
    d14_width: float | None
    d15_width: float | None
    # Additional fields used internally by the plotting system
    zone_widths_per_d: list[float]  # Calculated widths for each D-point
    y_coords_top_current_zone: list[float]  # Y-coordinates for zone top boundary


def calculate_zone_bottom_y_coords(  # noqa: PLR0913
    zone_idx: int,
    num_load_zones: int,
    num_defined_d_points: int,
    y_coords_top_current_zone: list[float],
    y_bridge_bottom_at_d_points: list[float],
    zone_param_data: LoadZoneDataRow,
) -> list[float]:
    """
    Calculates the Y-coordinates for the bottom boundary of the current load zone.

    Args:
        zone_idx: Index of the current load zone.
        num_load_zones: Total number of load zones.
        num_defined_d_points: Number of D-points defining the bridge/zone width.
        y_coords_top_current_zone: List of Y-coordinates for the top boundary of this zone at each D-point.
        y_bridge_bottom_at_d_points: List of Y-coordinates for the absolute bottom edge of the bridge at each D-point.
        zone_param_data: Parameter data for the current load zone, conforming to LoadZoneDataRow.

    Returns:
        A list of Y-coordinates for the bottom boundary of the current load zone.

    """
    if zone_idx == num_load_zones - 1:
        # The last zone extends to the bottom of the bridge deck.
        return list(y_bridge_bottom_at_d_points)

    y_coords_bottom: list[float] = []
    for d_idx_loop in range(num_defined_d_points):
        d_field_name = f"d{d_idx_loop + 1}_width"
        val_from_dict = zone_param_data.get(d_field_name)
        zone_width_at_this_d_point: float = val_from_dict if isinstance(val_from_dict, int | float) else 0.0

        # Calculate the Y-coordinate for the bottom of this zone at this D-point.
        # Assumes Y decreases downwards.
        y_bottom_val = y_coords_top_current_zone[d_idx_loop] - zone_width_at_this_d_point
        y_coords_bottom.append(y_bottom_val)
    return y_coords_bottom
