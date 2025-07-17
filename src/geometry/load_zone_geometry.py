"""Module for geometric calculations related to load zones."""

from typing import Any, TypedDict, cast

from viktor.errors import UserError

from app.bridge.parametrization import (
    MAX_LOAD_ZONE_SEGMENT_FIELDS,  # Import the constant
    BridgeParametrization,
)
from src.geometry.model_creator import (
    BridgeSegmentDimensions,  # Import the dataclass
    LoadZoneGeometryData,  # Import the dataclass
    prepare_load_zone_geometry_data,
)


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
# MINIMAL THEORETICAL LANE DIVISION ("THEORETISCHE RIJ INDELING")
# ========================================================================
#
# ⚠️  IMPORTANT: This is only a MINIMAL BASELINE implementation! ⚠️
#
# The functions below implement the most basic geometric division of bridge
# width into theoretical traffic lanes. This is NOT the complete theoretical
# lane division as required by Eurocode standards.
#
# IMPLEMENTATION STATUS:
# ✅ MINIMAL BASELINE: Simple geometric division (bridge_width ÷ 3)
# ❌ TRUE THEORETICAL: Advanced Eurocode-compliant theoretical modeling
# ❌ REALISTIC DIVISION: Actual lane configuration based on real traffic data
#
# ========================================================================
# TODO: COMPLETE "THEORETISCHE RIJ INDELING" (TRUE THEORETICAL DIVISION)
# ========================================================================
# The TRUE theoretical lane division must implement:
#
# 1. LANE SHIFTING & VARIABLE TESTING:
#    - Multiple lane position combinations for critical load cases
#    - Lateral shifting of traffic lanes to find maximum effects
#    - Variable lane configurations (1, 2, 3+ lane scenarios)
#    - Load position optimization across bridge width
#
# 2. DOMINANT ROAD LOAD SCENARIOS (EN 1991-2):
#    - Freight-dominant lanes (heavy traffic corridors)
#    - Mixed traffic patterns (passenger + freight combinations)
#    - Asymmetric loading (one lane heavier than others)
#    - Special transport routes (exceptional loads)
#
# 3. EUROCODE COMPLIANCE (EN 1991-2 Section 4):
#    - Load Model 1 (LM1) with proper lane factors
#    - Tandem system + UDL distribution per lane
#    - ψ factors for multi-lane scenarios
#    - Critical lane combinations and envelope analysis
#
# ========================================================================
# TODO: COMPLETE "WERKELIJKE RIJ INDELING" (REALISTIC LANE DIVISION)
# ========================================================================
# The REALISTIC lane division must implement:
#
# 1. ACTUAL TRAFFIC ENGINEERING (NEN-EN 1991-2):
#    - Real lane widths based on road classification
#    - Shoulder and emergency lane configurations
#    - Guardrail, barrier, and safety zone allowances
#    - Integration with params.input.belastingzones data
#
# 2. SITE-SPECIFIC LOAD PATTERNS:
#    - Measured traffic data integration
#    - Route-specific vehicle classifications
#    - Time-dependent loading patterns
#    - Environmental and seasonal variations
#
# 3. ADVANCED ANALYSIS FEATURES:
#    - Dynamic amplification factors per zone
#    - Influence line-based critical positioning
#    - Fatigue load models for high-traffic zones
#    - Multi-directional traffic scenarios
#
# ========================================================================
# CURRENT IMPLEMENTATION: MINIMAL BASELINE ONLY
# ========================================================================
# What this implementation provides:
# - Simple geometric division: bridge_width ÷ lane_width
# - Sequential lane placement from one side
# - Basic "Auto" and "Berm" zone types
# - Foundation for advanced implementations
#
# What this implementation DOES NOT provide:
# - Eurocode-compliant theoretical modeling
# - Lane shifting or variable positioning
# - Dominant road load scenarios
# - Realistic traffic engineering standards
# - Integration with actual traffic data
#
# Use this ONLY as a starting point for structural analysis!
# ========================================================================


def _set_d_point_widths(zone: LoadZoneDataRow, num_d_points: int, width: float) -> None:  # noqa: C901, PLR0912
    """
    Set width values for all D-points in a load zone.

    Helper function to reduce complexity by setting d1_width through d15_width
    explicitly for TypedDict compatibility.

    :param zone: Load zone data structure to modify
    :type zone: LoadZoneDataRow
    :param num_d_points: Number of D-points to set
    :type num_d_points: int
    :param width: Width value to set for all D-points
    :type width: float
    """
    if num_d_points >= 1:
        zone["d1_width"] = width
    if num_d_points >= 2:
        zone["d2_width"] = width
    if num_d_points >= 3:
        zone["d3_width"] = width
    if num_d_points >= 4:
        zone["d4_width"] = width
    if num_d_points >= 5:
        zone["d5_width"] = width
    if num_d_points >= 6:
        zone["d6_width"] = width
    if num_d_points >= 7:
        zone["d7_width"] = width
    if num_d_points >= 8:
        zone["d8_width"] = width
    if num_d_points >= 9:
        zone["d9_width"] = width
    if num_d_points >= 10:
        zone["d10_width"] = width
    if num_d_points >= 11:
        zone["d11_width"] = width
    if num_d_points >= 12:
        zone["d12_width"] = width
    if num_d_points >= 13:
        zone["d13_width"] = width
    if num_d_points >= 14:
        zone["d14_width"] = width
    if num_d_points >= 15:
        zone["d15_width"] = width


def calculate_theoretical_traffic_lanes(bridge_width: float, lane_width: float = 3.0) -> TheoreticalLaneResult:
    """
    Calculate MINIMAL theoretical traffic lane distribution based on bridge width.

    ⚠️  MINIMAL BASELINE IMPLEMENTATION ONLY! ⚠️

    This function provides the most basic geometric division of bridge width
    into theoretical traffic lanes. This is NOT the complete theoretical lane
    division as required by Eurocode standards.

    CURRENT ALGORITHM: Simple geometric division
    - num_lanes = floor(bridge_width / lane_width)
    - total_lanes_width = num_lanes * lane_width
    - rest_width = bridge_width - total_lanes_width

    MISSING FEATURES (for complete theoretical division):
    - Lane shifting for critical load cases
    - Variable lane configurations
    - Dominant road load scenarios
    - Eurocode-compliant lane factors
    - Load position optimization

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
    Generate MINIMAL theoretical load zone data structures for bridge analysis.

    ⚠️  MINIMAL BASELINE IMPLEMENTATION ONLY! ⚠️

    This function creates the most basic theoretical load zones from simple
    geometric division. This is NOT the complete theoretical or realistic
    load zone configuration required for proper bridge analysis.

    CURRENT APPROACH: Simple sequential placement
    - Traffic lanes: "Auto" zones with standard lane width
    - Rest area: "Berm" zone for any remaining width
    - All zones placed sequentially from one side of bridge

    MISSING FEATURES (for complete implementation):
    - Eurocode-compliant theoretical lane modeling
    - Lane shifting and variable positioning
    - Dominant road load scenarios
    - Integration with params.input.belastingzones
    - Realistic traffic engineering standards

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

        # Set width for each D-point (explicit assignment for TypedDict compatibility)
        _set_d_point_widths(zone, num_d_points, lane_width)

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

        # Set width for each D-point (explicit assignment for TypedDict compatibility)
        _set_d_point_widths(rest_zone, num_d_points, lane_calc["rest_width"])

        zones.append(rest_zone)

    return zones


# ========================================================================
# Functions for bridge geometry


# Define TypedDict for a row from params.bridge_segments_array
class BridgeSegmentParamRow(TypedDict):
    """
    Represents the structure of a single row item from params.bridge_segments_array.
    This TypedDict is used to provide type hinting for these row objects.
    """

    bz1: float
    bz2: float
    bz3: float
    l: float  # noqa: E741 # 'l' matches the field name in BridgeParametrization (input.dimensions.array.l)
    # Add other fields like dz, dz_2, col_6, is_first_segment if accessed, with appropriate types


def _create_bridge_segment_dimensions_from_params(segment_param_row: BridgeSegmentParamRow) -> BridgeSegmentDimensions:
    """Validates a segment param row and returns BridgeSegmentDimensions or raises UserError."""
    # The attribute check `hasattr` is still useful as a runtime check before typed access,
    # though MyPy will now also check based on BridgeSegmentParamRow.
    required_attrs = ["bz1", "bz2", "bz3", "l"]
    # For TypedDict, we'd ideally check presence of keys.
    # However, VIKTOR param objects are often Munch-like, so hasattr can work at runtime.
    # For Mypy, the key is using dictionary access below.
    if not all(key in segment_param_row for key in required_attrs):
        raise UserError("Een of meer brugsegmenten missen benodigde data (bz1, bz2, bz3, l) in Dimensies.")
    return BridgeSegmentDimensions(
        bz1=segment_param_row["bz1"], bz2=segment_param_row["bz2"], bz3=segment_param_row["bz3"], segment_length=segment_param_row["l"]
    )


def _prepare_bridge_geometry_for_plotting(bridge_segments_params: list) -> LoadZoneGeometryData | None:
    """Helper to prepare BridgeSegmentDimensions and LoadZoneGeometryData from params."""
    if not bridge_segments_params:
        return None
    try:
        typed_bridge_dimensions = []
        for segment_param_row in bridge_segments_params:
            # Call the new helper method
            segment_data = _create_bridge_segment_dimensions_from_params(segment_param_row)
            typed_bridge_dimensions.append(segment_data)

        if not typed_bridge_dimensions:
            return None
        return prepare_load_zone_geometry_data(typed_bridge_dimensions)
    except UserError:
        raise
    except Exception as e:
        print(f"Error preparing bridge geometry for load zones view: {e}")  # noqa: T201
        raise UserError("Fout bij voorbereiden bruggeometrie. Controleer de Dimensies tab.") from e


def get_bridge_geom_data(params: BridgeParametrization) -> LoadZoneGeometryData | None:
    """
    Extract and prepare bridge geometry data from bridge parametrization.

    Args:
        params: Bridge parametrization containing bridge segments array

    Returns:
        LoadZoneGeometryData object with processed bridge geometry, or None if no segments

    """
    return _prepare_bridge_geometry_for_plotting(params.bridge_segments_array)


# ========================================================================
# Functions for load zones - load_zone_data from params


def calculate_zone_geometry_properties(
    load_zones_data_params: list[LoadZoneDataRow], bridge_geom_data: LoadZoneGeometryData | None
) -> list[LoadZoneDataRow]:
    """
    Calculate geometric properties for each load zone based on bridge geometry.
    This adds the missing zone_widths_per_d and y_coords_top_current_zone fields.
    """
    if not load_zones_data_params or not bridge_geom_data:
        return load_zones_data_params

    updated_zones = []
    current_y_top = bridge_geom_data.y_top_structural_edge_at_d_points.copy()

    for zone_idx, zone_data in enumerate(load_zones_data_params):
        # Create a copy of the zone data
        updated_zone = dict(zone_data)

        # Calculate zone widths for each D-point
        zone_widths = []
        for d_idx in range(bridge_geom_data.num_defined_d_points):
            d_width_field = f"d{d_idx + 1}_width"
            width_value = zone_data.get(d_width_field)
            if isinstance(width_value, (int, float)):
                zone_widths.append(float(width_value))
            else:
                zone_widths.append(0.0)

        # Add calculated geometric properties
        updated_zone["zone_widths_per_d"] = zone_widths
        updated_zone["y_coords_top_current_zone"] = current_y_top.copy()
        # update zone_widths_per_d if it is the last zonde
        if zone_idx == len(load_zones_data_params) - 1:
            # Last zone: set zone_widths_per_d as the vertical distance to the bridge bottom at each D-point
            y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points
            updated_zone["zone_widths_per_d"] = [
            current_y_top[d_idx] - y_bridge_bottom_at_d_points[d_idx]
            for d_idx in range(len(current_y_top))
            ]

        # Update current_y_top for next zone (unless it's the last zone)
        if zone_idx < len(load_zones_data_params) - 1:
            # Move the top position down by the zone width for each D-point
            for d_idx in range(bridge_geom_data.num_defined_d_points):
                current_y_top[d_idx] -= zone_widths[d_idx]

        updated_zones.append(cast(LoadZoneDataRow, updated_zone))

    return updated_zones


def get_load_zones_data_from_params(params: BridgeParametrization) -> list[LoadZoneDataRow]:
    """
    Extract load zone data from bridge parametrization and convert to LoadZoneDataRow format.

    Args:
        params: Bridge parametrization containing load zone data array

    Returns:
        List of load zone data rows with proper typing

    """
    load_zones_data_params: list[LoadZoneDataRow] = []
    if params.load_zones_data_array:
        for row_param in params.load_zones_data_array:
            # Construct a dictionary that matches LoadZoneDataRow fields
            temp_row_data: dict[str, Any] = {
                "zone_type": row_param.zone_type,
                "pavement_thickness": getattr(row_param, "pavement_thickness", 0.05),  # Default 5cm
                "pavement_material": getattr(row_param, "pavement_material", "Asfalt"),  # Default Asfalt
            }
            for i in range(1, MAX_LOAD_ZONE_SEGMENT_FIELDS + 1):
                field_name = f"d{i}_width"
                value = getattr(row_param, field_name, None)
                # LoadZoneDataRow has dX_width as float | None, so store None if getattr returns None
                temp_row_data[field_name] = value

            row_data = cast(LoadZoneDataRow, temp_row_data)
            load_zones_data_params.append(row_data)

    return load_zones_data_params
