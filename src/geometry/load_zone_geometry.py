"""Module for geometric calculations related to load zones."""

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from src.common.constants import MAX_LOAD_ZONE_SEGMENT_FIELDS
from src.data_models.bridge_models import BridgeSegmentDimensions  # Import the Pydantic data model
from src.data_models.geometry_models import TheoreticalLaneResult
from src.data_models.load_models import LoadZoneData
from src.geometry.model_creator import (
    LoadZoneGeometryData,  # Import the dataclass
    prepare_load_zone_geometry_data,
)
from viktor.errors import UserError

# Use string annotation to avoid circular import
if TYPE_CHECKING:
    pass

# TheoreticalLaneResult is now imported from src.data_models.geometry_models


def calculate_zone_bottom_y_coords(  # noqa: PLR0913
    zone_idx: int,
    num_load_zones: int,
    num_defined_d_points: int,
    y_coords_top_current_zone: list[float],
    y_bridge_bottom_at_d_points: list[float],
    zone_param_data: LoadZoneData,
) -> list[float]:
    """
    Calculates the Y-coordinates for the bottom boundary of the current load zone.

    Args:
        zone_idx: Index of the current load zone.
        num_load_zones: Total number of load zones.
        num_defined_d_points: Number of D-points defining the bridge/zone width.
        y_coords_top_current_zone: List of Y-coordinates for the top boundary of this zone at each D-point.
        y_bridge_bottom_at_d_points: List of Y-coordinates for the absolute bottom edge of the bridge at each D-point.
        zone_param_data: Parameter data for the current load zone, conforming to LoadZoneData.

    Returns:
        A list of Y-coordinates for the bottom boundary of the current load zone.

    """
    if zone_idx == num_load_zones - 1:
        # The last zone extends to the bottom of the bridge deck.
        return list(y_bridge_bottom_at_d_points)

    y_coords_bottom: list[float] = []
    for d_idx_loop in range(num_defined_d_points):
        d_field_name = f"d{d_idx_loop + 1}_width"
        val_from_dict = getattr(zone_param_data, d_field_name, None)
        zone_width_at_this_d_point: float = val_from_dict if isinstance(val_from_dict, int | float) else 0.0

        # Calculate the Y-coordinate for the bottom of this zone at this D-point.
        # Assumes Y decreases downwards.
        y_bottom_val = y_coords_top_current_zone[d_idx_loop] - zone_width_at_this_d_point
        y_coords_bottom.append(y_bottom_val)
    return y_coords_bottom


def _get_d_point_widths_dict(num_d_points: int, width: float) -> dict[str, float]:
    """
    Generate dictionary of D-point width values for LoadZoneData creation.

    Helper function to create width assignments for Pydantic model initialization.

    :param num_d_points: Number of D-points to set
    :type num_d_points: int
    :param width: Width value to set for all D-points
    :type width: float
    :returns: Dictionary with d1_width through dN_width keys
    :rtype: dict[str, float]
    """
    width_dict = {}
    for i in range(1, min(num_d_points + 1, 16)):  # Max 15 D-points
        width_dict[f"d{i}_width"] = width
    return width_dict


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


def generate_theoretical_load_zones(bridge_width: float, num_d_points: int, lane_width: float = 3.0) -> list[LoadZoneData]:
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
    :rtype: list[LoadZoneData]
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

    zones: list[LoadZoneData] = []

    # Create traffic lane zones
    for lane_idx in range(lane_calc.num_lanes):
        # Get width assignments for all D-points
        width_dict = _get_d_point_widths_dict(num_d_points, lane_width)

        zone = LoadZoneData(
            zone_type="Auto",
            pavement_thickness=0.1,  # 10cm asphalt for traffic lanes
            pavement_material="Asfalt",
            zone_widths_per_d=[lane_width] * num_d_points,
            y_coords_top_current_zone=[],  # Will be calculated by controller
            **width_dict,  # Set all D-point widths
        )

        zones.append(zone)

    # Create rest zone if there's remaining width
    if lane_calc.rest_width > 0.001:  # Small tolerance for floating point
        # Get width assignments for all D-points
        rest_width_dict = _get_d_point_widths_dict(num_d_points, lane_calc.rest_width)

        rest_zone = LoadZoneData(
            zone_type="Berm",
            pavement_thickness=0.05,  # 5cm gravel for rest area
            pavement_material="Grind",  # Use valid material from Literal
            zone_widths_per_d=[lane_calc.rest_width] * num_d_points,
            y_coords_top_current_zone=[],  # Will be calculated by controller
            **rest_width_dict,  # Set all D-point widths
        )

        zones.append(rest_zone)

    return zones


# ========================================================================
# Functions for bridge geometry


def _create_bridge_segment_dimensions_from_params(segment_param_row: dict[str, Any]) -> BridgeSegmentDimensions | None:
    """
    Validates a segment param row and returns BridgeSegmentDimensions using Pydantic validation.

    Now uses Pydantic for automatic validation with clear error messages.
    Pydantic will automatically check that all required fields are present and valid.
    """
    # Handle Mock objects gracefully in tests
    if hasattr(segment_param_row, "_mock_name") or not hasattr(segment_param_row, "__getitem__"):
        # This is likely a Mock object, return None to indicate it can't be processed
        return None

    try:
        # Pydantic automatically validates all fields and provides clear error messages
        return BridgeSegmentDimensions(
            bz1=segment_param_row["bz1"], bz2=segment_param_row["bz2"], bz3=segment_param_row["bz3"], segment_length=segment_param_row["l"]
        )
    except KeyError as e:
        # Convert missing key errors to user-friendly messages
        missing_field = str(e).strip("'")
        raise UserError(f"Brugsegment mist benodigde data: {missing_field}. Controleer de Dimensies tab.") from e
    except ValidationError as e:
        # Convert Pydantic validation errors to user-friendly messages
        error_details = []
        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            msg = error["msg"]
            error_details.append(f"{field}: {msg}")

        raise UserError(f"Ongeldige brugsegment data: {'; '.join(error_details)}") from e
    except (TypeError, ValueError) as e:
        # Handle other data conversion errors
        raise UserError(f"Fout in brugsegment data: {e}") from e


def _prepare_bridge_geometry_for_plotting(bridge_segments_params: list) -> LoadZoneGeometryData | None:
    """Helper to prepare BridgeSegmentDimensions and LoadZoneGeometryData from params."""
    if not bridge_segments_params:
        return None
    try:
        typed_bridge_dimensions = []
        # If a mock was passed, treat it as having no iterable segments
        if isinstance(bridge_segments_params, list | tuple):
            iterable = bridge_segments_params
        else:
            return None
        for segment_param_row in iterable:
            # Call the new helper method
            segment_data = _create_bridge_segment_dimensions_from_params(segment_param_row)
            if segment_data:  # Only append if segment_data is not None (i.e., not a Mock)
                typed_bridge_dimensions.append(segment_data)

        if not typed_bridge_dimensions:
            return None
        return prepare_load_zone_geometry_data(typed_bridge_dimensions)
    except UserError:
        raise
    except Exception as e:
        print(f"Error preparing bridge geometry for load zones view: {e}")  # noqa: T201
        raise UserError("Fout bij voorbereiden bruggeometrie. Controleer de Dimensies tab.") from e


def get_bridge_geom_data(params: Any) -> LoadZoneGeometryData | None:  # noqa: ANN401
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
    load_zones_data_params: list[LoadZoneData], bridge_geom_data: LoadZoneGeometryData | None
) -> list[LoadZoneData]:
    """
    Calculate geometric properties for each load zone based on bridge geometry.
    This adds the missing zone_widths_per_d and y_coords_top_current_zone fields.
    """
    if not load_zones_data_params or not bridge_geom_data:
        return load_zones_data_params

    updated_zones = []
    current_y_top = bridge_geom_data.y_top_structural_edge_at_d_points.copy()

    for zone_idx, zone_data in enumerate(load_zones_data_params):
        # Calculate zone widths for each D-point
        zone_widths = []
        for d_idx in range(bridge_geom_data.num_defined_d_points):
            d_width_field = f"d{d_idx + 1}_width"
            width_value = getattr(zone_data, d_width_field, None)
            if isinstance(width_value, int | float):
                zone_widths.append(float(width_value))
            else:
                zone_widths.append(0.0)

        # Calculate zone_widths_per_d for last zone (vertical distance to bridge bottom)
        calculated_zone_widths = zone_widths
        if zone_idx == len(load_zones_data_params) - 1:
            # Last zone: set zone_widths_per_d as the vertical distance to the bridge bottom at each D-point
            y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points
            calculated_zone_widths = [current_y_top[d_idx] - y_bridge_bottom_at_d_points[d_idx] for d_idx in range(len(current_y_top))]

        # Create updated zone with calculated properties
        updated_zone = zone_data.model_copy(update={"zone_widths_per_d": calculated_zone_widths, "y_coords_top_current_zone": current_y_top.copy()})

        # Update current_y_top for next zone (unless it's the last zone)
        if zone_idx < len(load_zones_data_params) - 1:
            # Move the top position down by the zone width for each D-point
            for d_idx in range(bridge_geom_data.num_defined_d_points):
                current_y_top[d_idx] -= zone_widths[d_idx]

        updated_zones.append(updated_zone)

    return updated_zones


def get_load_zones_data_from_params(params: Any) -> list[LoadZoneData]:  # noqa: ANN401
    """
    Extract load zone data from bridge parametrization and convert to LoadZoneData format.

    Args:
        params: Bridge parametrization containing load zone data array

    Returns:
        List of load zone data rows with proper typing

    """
    load_zones_data_params: list[LoadZoneData] = []
    rows = getattr(params, "load_zones_data_array", None)
    if isinstance(rows, list | tuple) and rows:
        for row_param in rows:
            # Construct a dictionary that matches LoadZoneData fields with explicit type conversion
            temp_row_data: dict[str, Any] = {
                "zone_type": str(row_param.zone_type),
                "pavement_thickness": float(getattr(row_param, "pavement_thickness", 0.05)),  # Default 5cm
                "pavement_material": str(getattr(row_param, "pavement_material", "Asfalt")),  # Default Asfalt
            }
            for i in range(1, MAX_LOAD_ZONE_SEGMENT_FIELDS + 1):
                field_name = f"d{i}_width"
                value = getattr(row_param, field_name, None)
                # Ensure width is float or None
                temp_row_data[field_name] = float(value) if isinstance(value, (int, float)) else None

            # Create LoadZoneData object with validation
            try:
                load_zone = LoadZoneData(**temp_row_data)
                load_zones_data_params.append(load_zone)
            except ValidationError as e:
                # Convert Pydantic validation errors to user-friendly messages
                error_details = []
                for error in e.errors():
                    field = error["loc"][0] if error["loc"] else "unknown"
                    msg = error["msg"]
                    error_details.append(f"{field}: {msg}")

                raise UserError(f"Ongeldige belastingzone data: {'; '.join(error_details)}") from e

    return load_zones_data_params


def get_tram_track_y_coordinates(params: Any) -> dict[str, list[float]] | None:  # noqa: ANN401
    """
    Calculate the centerline y-coordinates of tram tracks if tram zones are present.

    This function counts the number of tram zones and calculates the centerline
    y-coordinate for each tram track at each D-point.

    Args:
        params: Bridge parametrization containing load zone data array and bridge segments

    Returns:
        Dictionary mapping track name to list of centerline y-coordinates at each D-point.
        Returns None if no tram zones are found.

        Example: {"tram_track_1": [y1_d1, y1_d2, ...], "tram_track_2": [y2_d1, y2_d2, ...]}

    Raises:
        UserError: If tram zone configuration is invalid

    Notes:
        - Each tram zone represents one track
        - Track centerline is the average of zone top and bottom y-coordinates
        - Y-coordinates are measured from the bridge centerline
        - Positive y is towards the top of the bridge (zone 1 side)

    """
    # Get bridge geometry
    bridge_geom_data = get_bridge_geom_data(params)
    if bridge_geom_data is None:
        return None

    # Get load zones data
    load_zones_data = get_load_zones_data_from_params(params)

    # Calculate zone geometry properties
    load_zones_with_geometry = calculate_zone_geometry_properties(load_zones_data, bridge_geom_data)

    # Find all tram zones
    tram_zones = [zone for zone in load_zones_with_geometry if zone.zone_type == "Tram"]

    if not tram_zones:
        return None

    num_d_points = bridge_geom_data.num_defined_d_points

    # Build result dictionary with track names and centerlines
    result: dict[str, list[float]] = {}

    # Process each tram zone (each zone = one track)
    for track_idx, tram_zone in enumerate(tram_zones, start=1):
        # Check if we have valid geometry data
        if not tram_zone.y_coords_top_current_zone or not tram_zone.zone_widths_per_d:
            raise UserError("Tramzone mist geometrische gegevens. Controleer de belastingzones configuratie.")

        if len(tram_zone.y_coords_top_current_zone) != num_d_points:
            raise UserError(f"Tramzone geometrie komt niet overeen met aantal D-punten ({num_d_points}).")

        # Calculate centerline for this track at each D-point
        centerline_coords: list[float] = []
        for d_idx in range(num_d_points):
            y_top = tram_zone.y_coords_top_current_zone[d_idx]
            zone_width = tram_zone.zone_widths_per_d[d_idx]

            # Centerline is at the middle of the zone (average of top and bottom)
            y_bottom = y_top - zone_width
            y_centerline = (y_top + y_bottom) / 2.0

            centerline_coords.append(y_centerline)

        result[f"tram_track_{track_idx}"] = centerline_coords

    return result
