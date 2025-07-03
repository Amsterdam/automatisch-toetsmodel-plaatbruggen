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


class TheoreticalLaneResult(TypedDict):
    """Result structure for theoretical traffic lane calculations."""

    num_lanes: int
    lane_width: float
    rest_width: float
    total_lanes_width: float


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


# ========================================================================
# THEORETICAL TRAFFIC LANE FUNCTIONS
# ========================================================================
#
# The functions below implement THEORETICAL traffic load distribution based on
# simple geometric division of bridge width. This provides a baseline traffic
# loading pattern for structural analysis.
#
# FUTURE ENHANCEMENT: PRACTICAL/REALISTIC LOAD ZONES
# ========================================================================
# Later implementation will add practical/realistic load zone functionality:
#
# 1. PRACTICAL LANE CONFIGURATION:
#    - Based on actual traffic engineering standards (NEN-EN 1991-2)
#    - Variable lane widths (3.0m, 3.25m, 3.5m depending on road type)
#    - Shoulder and emergency lane considerations
#    - Guardrail and safety barrier allowances
#
# 2. REALISTIC LOAD DISTRIBUTION:
#    - Integration with params.input.belastingzones data
#    - Zone-specific load intensities and patterns
#    - Pedestrian and cyclist load combinations
#    - Special vehicle load cases (emergency, maintenance)
#
# 3. ADVANCED LOAD MODELING:
#    - Dynamic amplification factors per zone type
#    - Load distribution length calculations
#    - Influence line-based load positioning
#    - Fatigue load models for high-traffic zones
#
# INTEGRATION POINTS FOR FUTURE DEVELOPMENT:
# - generate_practical_load_zones(params, traffic_data, design_standards)
# - apply_realistic_load_patterns(zones, load_cases, bridge_geometry)
# - optimize_load_positions(influence_lines, critical_sections)
#
# The theoretical functions below provide the foundation for these enhancements.
# ========================================================================


def calculate_theoretical_traffic_lanes(bridge_width: float, lane_width: float = 3.0) -> TheoreticalLaneResult:
    """
    Calculate theoretical traffic lane distribution based on bridge width.

    Divides bridge width by standard lane width to determine maximum number of
    theoretical traffic lanes that can fit. Remainder becomes rest/berm zone.

    Algorithm:
    - num_lanes = floor(bridge_width / lane_width)
    - total_lanes_width = num_lanes * lane_width
    - rest_width = bridge_width - total_lanes_width

    :param bridge_width: Total bridge width in meters
    :type bridge_width: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: Dictionary with lane calculation results
    :rtype: TheoreticalLaneResult
    :raises ValueError: If bridge_width or lane_width is not positive

    Examples:
        >>> calculate_theoretical_traffic_lanes(30.0)
        {'num_lanes': 10, 'lane_width': 3.0, 'rest_width': 0.0, 'total_lanes_width': 30.0}

        >>> calculate_theoretical_traffic_lanes(10.0)
        {'num_lanes': 3, 'lane_width': 3.0, 'rest_width': 1.0, 'total_lanes_width': 9.0}

    """
    if bridge_width <= 0:
        raise ValueError("Bridge width must be positive")

    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Calculate maximum number of complete lanes
    num_lanes = int(bridge_width // lane_width)

    # Calculate dimensions
    total_lanes_width = num_lanes * lane_width
    rest_width = bridge_width - total_lanes_width

    return TheoreticalLaneResult(
        num_lanes=num_lanes,
        lane_width=lane_width,
        rest_width=rest_width,
        total_lanes_width=total_lanes_width,
    )


def generate_theoretical_load_zones(bridge_width: float, num_d_points: int, lane_width: float = 3.0) -> list[LoadZoneDataRow]:
    """
    Generate theoretical load zone data structures for bridge analysis.

    Creates load zones based on theoretical traffic lane distribution:
    - Traffic lanes: "Auto" zones with standard lane width
    - Rest area: "Berm" zone for any remaining width
    - All zones placed sequentially from one side of bridge

    :param bridge_width: Total bridge width in meters
    :type bridge_width: float
    :param num_d_points: Number of D-points along bridge length
    :type num_d_points: int
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of load zone data structures
    :rtype: list[LoadZoneDataRow]
    :raises ValueError: If inputs are invalid

    Zone Properties:
        Traffic Lanes ("Auto"):
        - zone_type: "Auto"
        - pavement_thickness: 0.1m (asphalt)
        - pavement_material: "Asfalt"

        Rest Zone ("Berm"):
        - zone_type: "Berm"
        - pavement_thickness: 0.05m (gravel)
        - pavement_material: "Gravel"
    """
    if bridge_width <= 0:
        raise ValueError("Bridge width must be positive")

    if num_d_points <= 0:
        raise ValueError("Number of D-points must be positive")

    # Calculate lane distribution
    lane_calc = calculate_theoretical_traffic_lanes(bridge_width, lane_width)

    zones: list[LoadZoneDataRow] = []

    # Create traffic lane zones
    for lane_idx in range(lane_calc["num_lanes"]):
        zone: LoadZoneDataRow = {
            "zone_type": "Auto",
            "pavement_thickness": 0.1,  # 10cm asphalt for traffic lanes
            "pavement_material": "Asfalt",
            "zone_widths_per_d": [lane_width] * num_d_points,
            "y_coords_top_current_zone": [],  # Will be calculated by controller
        }

        # Set width for each D-point
        for d_idx in range(1, num_d_points + 1):
            d_field = f"d{d_idx}_width"
            zone[d_field] = lane_width  # type: ignore[assignment]

        zones.append(zone)

    # Create rest zone if there's remaining width
    if lane_calc["rest_width"] > 0.001:  # Small tolerance for floating point
        rest_zone: LoadZoneDataRow = {
            "zone_type": "Berm",
            "pavement_thickness": 0.05,  # 5cm gravel for rest area
            "pavement_material": "Gravel",
            "zone_widths_per_d": [lane_calc["rest_width"]] * num_d_points,
            "y_coords_top_current_zone": [],  # Will be calculated by controller
        }

        # Set width for each D-point
        for d_idx in range(1, num_d_points + 1):
            d_field = f"d{d_idx}_width"
            rest_zone[d_field] = lane_calc["rest_width"]  # type: ignore[assignment]

        zones.append(rest_zone)

    return zones
