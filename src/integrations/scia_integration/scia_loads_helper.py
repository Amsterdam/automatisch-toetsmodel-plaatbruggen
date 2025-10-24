"""
Helper functions for load case logic and manipulation.

This module provides utility functions for working with load cases in the bridge analysis context.

All functions are independent of the VIKTOR SDK and suitable for use in the core logic layer.
"""

from typing import TYPE_CHECKING, Any

from src.integrations.scia_integration.scia_load_generators import extract_bridge_dimensions

if TYPE_CHECKING:
    from app.bridge.parametrization import BridgeParametrization
from src.combinations.load_factors import get_alpha_q_nen_en_1991_2, get_alpha_trend_nen_8701, get_psi_nen_8701
from src.common.constants import SIGNAGE_LOAD_FACTORS
from src.common.materials import get_material_densities
from src.geometry.load_zone_geometry import calculate_zone_geometry_properties, get_bridge_geom_data, get_load_zones_data_from_params
from src.geometry.model_creator import LoadZoneGeometryData
from src.integrations.scia_integration.constants.geometry import (
    DEFAULT_LANE_WIDTH,
    LANE_CENTER_OFFSET_FACTOR,
    MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES,
    TANDEM_SPACING_LONGITUDINAL,
    TANDEM_START_Y_OFFSET,
    TANDEM_START_Y_OFFSET_FACTOR,
    TANDEM_VEHICLE_LENGTH,
    TANDEM_WHEEL_SIZE,
    TANDEM_WHEEL_SPACING_LONGITUDINAL,
    TANDEM_WHEEL_SPACING_TRANSVERSE,
)
from src.integrations.scia_integration.constants.loads import (
    ALPHA_Q_MAIN_LANE_ONDERLIGGEND,
    ALPHA_Q_ONDERLIGGEND,
    ALPHA_Q_OTHER_LANE_ONDERLIGGEND,
    DEFAULT_UDL_VALUE,
    NOBS_DEFAULT,
    SIGNAGE_WEIGHT_OPTIONS,
    TANDEM_CONTACT_AREA_SIDE,
    TANDEM_LOAD_BASE_MAIN,
    TANDEM_LOAD_BASE_SECOND,
    TANDEM_LOAD_BASE_THIRD,
    UDL_OTHER_LANE_VALUE,
    UDL_REST_AREA_VALUE,
)
from src.integrations.scia_integration.constants.units import (
    KN_PER_SQM_TO_N_PER_SQM,
)

# Import for type checking only to avoid circular imports
if TYPE_CHECKING:
    from .scia_model_interface import SciaModelBuilder


# Standard tandem wheel offsets from bottom left corner
TANDEM_WHEEL_OFFSETS = [
    (0, 0),
    (TANDEM_WHEEL_SPACING_LONGITUDINAL, 0),
    (0, TANDEM_WHEEL_SPACING_TRANSVERSE),
    (TANDEM_WHEEL_SPACING_LONGITUDINAL, TANDEM_WHEEL_SPACING_TRANSVERSE),
]

# Bridge deck width properties for calculating lane width
min_width = 5.4
max_width = 6.0


# =======================================================================
# Helper functions for bridge layout properties
# =======================================================================
def amount_of_notional_lanes(width_bridgedeck: float) -> tuple[int, float]:
    """
    Calculate the number of notional lanes and their width based on the bridge deck width.

    Args:
        width_bridgedeck (float): The width of the bridge deck in meters.

    Returns:
        tuple[int, float]: A tuple containing the number of notional lanes and the width per lane in meters.

    """
    if width_bridgedeck < min_width:
        return 1, 3
    if min_width <= width_bridgedeck < max_width:
        return 2, width_bridgedeck / 2
    return int(width_bridgedeck // 3), 3


def amount_of_notional_lanes_from_center(width_bridgedeck: float) -> tuple[int, int, float]:
    """
    Calculate the number of notional lanes that can fit on either side of the bridge deck center.

    For BG4003 (center load case), we need to determine how many lanes can fit on either side of
    the center lane. The total width available is divided into two parts (left and right of center),
    and we calculate how many 3m lanes can fit in each part.

    Args:
        width_bridgedeck (float): The width of the bridge deck in meters.

    Returns:
        tuple[int, int, float]: A tuple containing:
            - Number of lanes that fit left of center
            - Number of lanes that fit right of center
            - Width per lane (always 3.0m as per standard)

    """
    # Center lane always takes DEFAULT_LANE_WIDTH
    center_lane_width = DEFAULT_LANE_WIDTH
    remaining_width = width_bridgedeck - center_lane_width

    # Calculate space on either side
    width_per_side = remaining_width / 2

    # Calculate number of full DEFAULT_LANE_WIDTH lanes that can fit on each side
    lanes_per_side = int(width_per_side // DEFAULT_LANE_WIDTH)

    return lanes_per_side, lanes_per_side, DEFAULT_LANE_WIDTH


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
    return TANDEM_START_Y_OFFSET_FACTOR * thickness_bridgedeck


def get_reference_period(params: "BridgeParametrization") -> int:
    """
    Return the reference period (in years) based on the veiligheidsniveau input.

    :param veiligheidsniveau: The value of the veiligheidsniveau field from parametrization.py
    :type veiligheidsniveau: str
    :returns: Reference period in years (30 or 15)
    :rtype: int
    """
    if params["design_code"] == "NEN 8700 afkeur":
        return 15
    return 30


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

    # Find all auto zones
    auto_zones_with_indices = [(i, zone) for i, zone in enumerate(load_zones_data) if zone.zone_type == "Auto"]

    if len(auto_zones_with_indices) < 2:
        raise ValueError(f"Expected 2 road zones, but found {len(auto_zones_with_indices)}")

    # Extract widths for the first two auto zones
    widths = []
    cumulative_width = 0.0

    for zone_position, (zone_index, zone) in enumerate(auto_zones_with_indices[:2]):
        # Accumulate widths of all zones before this auto zone
        if zone_position == 0:
            for i in range(zone_index):
                prev_zone = load_zones_data[i]
                width_value = getattr(prev_zone, "d1_width", None)
                prev_width = float(width_value) if isinstance(width_value, (int, float)) else 0.0
                cumulative_width += prev_width

        # Get the width of this auto zone
        width_value = getattr(zone, "d1_width", None)
        zone_width = float(width_value) if isinstance(width_value, (int, float)) else 0.0

        # If this auto zone is the last zone in the array, calculate remaining width
        if zone_index == len(load_zones_data) - 1:
            zone_width = dims.total_width - cumulative_width
        else:
            cumulative_width += zone_width

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
            # Get y-coordinates, ensure we have a valid list and first value
            y_coords = getattr(zone, "y_coords_top_current_zone", [])
            y_coord = float(y_coords[0]) if y_coords else 0.0

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
            # Get y-coordinates, ensure we have a valid list and first value
            y_coords = getattr(zone, "y_coords_top_current_zone", [])
            y_coord = float(y_coords[0]) if y_coords else 0.0
            auto_zone_y_coords.append(y_coord)

    # Return the first two y-coordinates if available, otherwise default to (0.0, 0.0)
    if len(auto_zone_y_coords) >= 2:
        return auto_zone_y_coords[0], auto_zone_y_coords[1]

    return 0.0, 0.0


# ========================================================================
# Helper functions for load value calculations
# ========================================================================
def calculate_real_tandem_values(
    params: "BridgeParametrization",
    length_bridgedeck: float,
    psi_nen_8701_factor: float,
    alpha_trend_factor: float,
) -> tuple[float, float, float]:
    """
    Calculate tandem values based on berekeningsniveau and other factors.

    :param params: Bridge parameters containing berekeningsniveau and signage settings
    :param length_bridgedeck: Length of the bridge deck
    :param psi_nen_8701_factor: NEN 8701 factor
    :param alpha_trend_factor: Alpha trend factor from NEN 8701
    :returns: Tuple of (load_main, load_second, load_third)
    """
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    base_main = TANDEM_LOAD_BASE_MAIN / contact_area
    base_second = TANDEM_LOAD_BASE_SECOND / contact_area
    base_third = TANDEM_LOAD_BASE_THIRD / contact_area

    if params.berekeningsniveau == "Werkelijke wegindeling":
        alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]
        load_main = base_main * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
        load_second = base_second * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
        load_third = base_third * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    elif params.berekeningsniveau == "Werkelijke wegindeling onderliggend wegennet":
        alpha_q_factor = ALPHA_Q_ONDERLIGGEND
        load_main = base_main * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
        load_second = base_second * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
        load_third = base_third * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    elif params.berekeningsniveau == "Werkelijke wegindeling met bebording":
        signage_index = SIGNAGE_WEIGHT_OPTIONS.index(params.signage)
        load_factor = SIGNAGE_LOAD_FACTORS[signage_index]
        load_main = base_main * load_factor
        load_second = base_second * load_factor
        load_third = base_third * load_factor
    else:  # Fallback for safety
        load_main = base_main
        load_second = base_second
        load_third = base_third

    return load_main, load_second, load_third


def calculate_real_udl_values(
    params: "BridgeParametrization",
    length_bridgedeck: float,
    udl_value: float,
    psi_nen_8701_factor: float,
    alpha_trend_factor: float,
) -> tuple[float, float, float]:
    """
    Calculate UDL values based on berekeningsniveau and other factors.

    :param params: Bridge parameters containing berekeningsniveau and signage settings
    :param length_bridgedeck: Length of the bridge deck
    :param udl_value: Base UDL value
    :param psi_nen_8701_factor: NEN 8701 factor
    :param alpha_trend_factor: Alpha trend factor from NEN 8701
    :returns: Tuple of (main_value, other_value, rest_value)
    """
    if params.berekeningsniveau == "Werkelijke wegindeling":
        alpha_q_factors = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)
        main_value = udl_value * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
        other_value = UDL_OTHER_LANE_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
        rest_value = UDL_REST_AREA_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
    elif params.berekeningsniveau == "Werkelijke wegindeling onderliggend wegennet":
        alpha_q_factors = [ALPHA_Q_MAIN_LANE_ONDERLIGGEND, ALPHA_Q_OTHER_LANE_ONDERLIGGEND]
        main_value = udl_value * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
        other_value = UDL_OTHER_LANE_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
        rest_value = UDL_REST_AREA_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
    elif params.berekeningsniveau == "Werkelijke wegindeling met bebording":
        # Get the selected signage option and map to load factor
        signage_index = SIGNAGE_WEIGHT_OPTIONS.index(params.signage)
        load_factor = SIGNAGE_LOAD_FACTORS[signage_index]
        # Apply the load factor to all values
        main_value = udl_value * load_factor
        other_value = UDL_OTHER_LANE_VALUE
        rest_value = UDL_REST_AREA_VALUE
    else:  # Fallback for safety
        main_value = udl_value
        other_value = UDL_OTHER_LANE_VALUE
        rest_value = UDL_REST_AREA_VALUE

    return main_value, other_value, rest_value


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
        if not material or not isinstance(thickness, int | float):
            result.append(0.0)
            continue
        density = density_lookup.get(str(material).lower(), 0.0)
        load = thickness * density if density > 0 and thickness > 0 else 0.0
        result.append(load)
    return result


def calculate_pavement_load_from_material(
    thickness: float,
    material: str,
) -> float:
    """
    Calculate the pavement load (kN/m²) from the material properties.

    :param thickness: Pavement thickness in meters
    :type thickness: float
    :param material: Pavement material name
    :type material: str
    :returns: Calculated load (kN/m²) (0.0 if missing or unknown material)
    :rtype: float
    """
    # Build a lookup for material densities (case-insensitive)
    density_lookup = {name.lower(): density for name, density in get_material_densities()}

    if not material or not isinstance(thickness, int | float):
        return 0.0

    density = density_lookup.get(str(material).lower(), 0.0)
    return thickness * density if density > 0 and thickness > 0 else 0.0


# This function is used to create the load cases 2001/2002/2003
def create_material_surface_load(
    builder: "SciaModelBuilder",
    load_config: dict[str, Any],
    bridge_geom_data: LoadZoneGeometryData,
) -> None:
    """
    Create a surface load for a specific material in a load zone span.

    :param builder: SCIA model builder instance
    :param load_config: Configuration containing all load parameters:
        - load_zone: Load zone data containing coordinates and properties
        - zone_index: Index of the load zone
        - span: Span index within the load zone
        - material_name: Name of the material for load naming
        - load_case_name: Name of the load case to apply the load to
    :param bridge_geom_data: Bridge geometry data
    """
    # Extract parameters from load_config
    load_zone = load_config["load_zone"]
    zone_index = load_config["zone_index"]
    span = load_config["span"]
    material_name = load_config["material_name"]
    load_case_name = load_config["load_case_name"]

    # Calculate coordinates for the surface load
    y_coord_top_left = round(getattr(load_zone, "y_coords_top_current_zone", [])[span], 2)
    y_coord_top_right = round(getattr(load_zone, "y_coords_top_current_zone", [])[span + 1], 2)
    y_coord_bottom_left = round(y_coord_top_left - getattr(load_zone, "zone_widths_per_d", [])[span], 2)
    y_coord_bottom_right = round(y_coord_top_right - getattr(load_zone, "zone_widths_per_d", [])[span + 1], 2)
    x_coord_left = round(bridge_geom_data.x_coords_d_points[span], 2)
    x_coord_right = round(bridge_geom_data.x_coords_d_points[span + 1], 2)

    corners = [
        (x_coord_left, y_coord_top_left, 0.0),
        (x_coord_right, y_coord_top_right, 0.0),
        (x_coord_right, y_coord_bottom_right, 0.0),
        (x_coord_left, y_coord_bottom_left, 0.0),
    ]

    builder.create_surface_load(
        name=f"{load_zone.zone_type}_{zone_index}_{material_name}_{span}_d{load_zone.pavement_thickness}",
        load_case_name=load_case_name,
        corner_points=corners,
        load_value=-calculate_pavement_load_from_material(load_zone.pavement_thickness, load_zone.pavement_material)
        * KN_PER_SQM_TO_N_PER_SQM,  # Convert to kN/m²
    )


# This function is used to create the load cases 2001/2002/2003
def add_material_loads(
    builder: "SciaModelBuilder",
    params: "BridgeParametrization",
    material_config: dict[str, str],
) -> None:
    """
    Add surface loads for specified materials to the SCIA model.

    :param builder: SCIA model builder instance
    :param params: Bridge parameters
    :param material_config: Dictionary mapping material names to their load case names
    """
    # Get load zone information from params using the utility functions
    load_zones_data_params = get_load_zones_data_from_params(params)
    bridge_geom_data = get_bridge_geom_data(params)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return

    # Update load zones data with geometry properties
    load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

    # Iterate through load zones and apply loads for specified materials
    for i, load_zone in enumerate(load_zones_data_params):
        pavement_material = getattr(load_zone, "pavement_material", "")

        if pavement_material in material_config:
            load_case_name = material_config[pavement_material]
            # Clean material name for use in load naming
            material_name = pavement_material.replace(" ", "_").replace("(", "").replace(")", "").lower()

            # Iterate through spans
            for span in range(len(getattr(load_zone, "y_coords_top_current_zone", [])) - 1):
                load_config = {
                    "load_zone": load_zone,
                    "zone_index": i,
                    "span": span,
                    "material_name": material_name,
                    "load_case_name": load_case_name,
                }

                create_material_surface_load(builder, load_config, bridge_geom_data)


# ========================================================================
# Tandem sequencer functions
# ========================================================================


def tandem_system_sequencer(
    length_bridgedeck: float, thickness_bridgedeck: float, length_vehicle: float = 0.0, spacing: float = TANDEM_SPACING_LONGITUDINAL
) -> list[float]:
    """
    Calculate the x-positions of the tandem systems in a notional lane along the length of the bridge deck.
    Default spacing between tandem systems is 0.5 meters. A tandem system exactly mid-span is always included.

    Args:
        length_bridgedeck (float): The length of the bridge deck in meters.
        thickness_bridgedeck (float): The thickness of the bridge deck in meters.
        length_vehicle (float): The length of the vehicle in meters.
        spacing (float): The spacing between tandem systems in meters.

    Returns:
        list[float]: A list containing the positions of the tandem systems along the bridge deck.

    """
    start_of_lanes = calculate_start_of_lanes(thickness_bridgedeck)
    tandem_systems = []

    # Calculate positions based on vehicle length
    mid_span_position = length_bridgedeck / 2 - length_vehicle / 2
    end_span_position = length_bridgedeck - start_of_lanes - length_vehicle

    # Generate positions from start_of_lanes to end_span_position (inclusive), step dx
    pos = start_of_lanes
    while pos < end_span_position - 1e-6:  # Use a small epsilon to avoid floating-point issues
        tandem_systems.append(round(pos, 6))
        pos += spacing
    # Always include end_span_position exactly
    tandem_systems.append(round(end_span_position, 6))

    # Ensure mid-span position is included (within tolerance)
    if not any(abs(p - mid_span_position) < 1e-6 for p in tandem_systems):
        tandem_systems.append(round(mid_span_position, 6))

    return sorted(set(tandem_systems))


# ========================================================================
# UNIFORMLY DISTRIBUTED TRAFFIC LOADS (UDL) FOR MAIN NOTIONAL LANES
# ========================================================================


def create_theoretical_udl_traffic_loads(  # noqa: PLR0912, PLR0913, C901
    params: "BridgeParametrization",
    length_bridgedeck: float,
    width_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    udl_value: float = DEFAULT_UDL_VALUE,
) -> dict[str, dict[str, Any]]:
    """
    Create UDLs for all notional lanes and remaining areas.

    Creates three categories of load polygons:
    - "main": First notional lane (9 kN/m²)
    - "other": Additional notional lanes (2.5 kN/m²)
    - "rest": Remaining bridge deck areas (2.5 kN/m²)

    :param length_bridgedeck: Bridge length in meters
    :param width_bridgedeck: Bridge width in meters
    :param width_firstsegment_zone3: Zone 3 width (for lane offset)
    :param width_firstsegment_zone2: Zone 2 width (for lane offset)
    :param lane_width: Lane width in meters (default DEFAULT_LANE_WIDTH)
    :param udl_value: UDL value for main lane in N/m² (default DEFAULT_UDL_VALUE)
    :returns: Dict with keys BG4001, BG4002, BG4003, each containing lane polygons and load values
    """
    # Create an empty results dictionary
    results = {}

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factors = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)
    # Obtain load values
    main_value = udl_value * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
    other_value = UDL_OTHER_LANE_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[0]
    rest_value = UDL_REST_AREA_VALUE * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factors[1]
    # Calculate amount of notional lanes and lane width when starting on one side of the bridge deck
    max_lanes, lane_width = amount_of_notional_lanes(width_bridgedeck)  # Maximum number of lanes to consider and lane width

    # BG4001: leftmost lanes (BG8000 logic)
    y_positions_left = generate_theoretical_lane_positions_bg8000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_left:
        load_polygons: dict[str, list[dict[str, list[tuple[float, float, float]] | float]]] = {"main": [], "other": [], "rest": []}

        # Create lane polygons for up to max_lanes, starting from leftmost
        for lane_idx, y_center in enumerate(y_positions_left[:max_lanes]):
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]

            # First lane is "main", others are "other"
            if lane_idx == 0:
                load_polygons["main"].append({"polygon": lane_polygon, "load": main_value})
            else:
                load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

        # Create rest polygon for areas not covered by lanes
        max_lane_width = max_lanes * lane_width
        if max_lane_width < width_bridgedeck:
            rest_polygon = [
                (0.0, y_positions_left[0] + max_lane_width - LANE_CENTER_OFFSET_FACTOR * lane_width, 0.0),
                (length_bridgedeck, y_positions_left[0] + max_lane_width - LANE_CENTER_OFFSET_FACTOR * lane_width, 0.0),
                (length_bridgedeck, width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (0.0, width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            ]
            load_polygons["rest"].append({"polygon": rest_polygon, "load": rest_value})

        results["BG4001"] = load_polygons

    # BG4002: Rightmost lanes (BG9000 logic)
    y_positions_right = generate_theoretical_lane_positions_bg9000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)
    if y_positions_right:
        load_polygons = {"main": [], "other": [], "rest": []}

        for lane_idx, y_center in enumerate(y_positions_right[:max_lanes]):
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]

            if lane_idx == 0:
                load_polygons["main"].append({"polygon": lane_polygon, "load": main_value})
            else:
                load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

        # Rest polygon for area below lanes
        if max_lane_width < width_bridgedeck:
            rest_polygon = [
                (0.0, -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
                (length_bridgedeck, y_positions_right[0] - max_lane_width + LANE_CENTER_OFFSET_FACTOR * lane_width, 0.0),
                (0.0, y_positions_right[0] - max_lane_width + LANE_CENTER_OFFSET_FACTOR * lane_width, 0.0),
            ]
            load_polygons["rest"].append({"polygon": rest_polygon, "load": rest_value})

        results["BG4002"] = load_polygons

    # BG4003: center lanes with dynamic number of lanes on each side
    # Calculate how many lanes can fit on each side of the center
    left_lanes, right_lanes, _ = amount_of_notional_lanes_from_center(width_bridgedeck)
    total_lanes = 1 + left_lanes + right_lanes  # Center lane + left lanes + right lanes

    # Get the center position and adjust for zone offsets
    center_y = width_bridgedeck / 2 - width_firstsegment_zone3 - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2

    load_polygons = {"main": [], "other": [], "rest": []}

    # Create center (main) lane
    center_y_min = center_y - lane_width / 2
    center_y_max = center_y + lane_width / 2
    center_polygon = [
        (0.0, center_y_min, 0.0),
        (length_bridgedeck, center_y_min, 0.0),
        (length_bridgedeck, center_y_max, 0.0),
        (0.0, center_y_max, 0.0),
    ]
    load_polygons["main"].append({"polygon": center_polygon, "load": main_value})

    # Create left side lanes
    for i in range(left_lanes):
        y_center = center_y - (i + 1) * lane_width
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        lane_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

    # Create right side lanes
    for i in range(right_lanes):
        y_center = center_y + (i + 1) * lane_width
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        lane_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

    # Create rest polygons for any remaining areas
    total_lanes_width = total_lanes * lane_width

    # Upper rest area (if exists)
    if center_y + total_lanes_width / 2 < width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3:
        upper_rest = [
            (0.0, center_y + total_lanes_width / 2, 0.0),
            (length_bridgedeck, center_y + total_lanes_width / 2, 0.0),
            (length_bridgedeck, width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (0.0, width_bridgedeck - LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
        ]
        load_polygons["rest"].append({"polygon": upper_rest, "load": rest_value})

    # Lower rest area (if exists)
    if center_y - total_lanes_width / 2 > -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3:
        lower_rest = [
            (0.0, -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (length_bridgedeck, -LANE_CENTER_OFFSET_FACTOR * width_firstsegment_zone2 - width_firstsegment_zone3, 0.0),
            (length_bridgedeck, center_y - total_lanes_width / 2, 0.0),
            (0.0, center_y - total_lanes_width / 2, 0.0),
        ]
        load_polygons["rest"].append({"polygon": lower_rest, "load": rest_value})

    results["BG4003"] = load_polygons

    return results


def create_real_udl_traffic_loads(  # noqa: PLR0912, C901
    params: "BridgeParametrization",
    length_bridgedeck: float,
    udl_value: float = DEFAULT_UDL_VALUE,
) -> dict[str, dict[str, Any]]:
    """
    Create real uniform distributed load (UDL) traffic loads for the bridge.

    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param length_bridgedeck: Length of the bridge deck
    :type length_bridgedeck: float
    :param width_bridgedeck: Width of the bridge deck
    :type width_bridgedeck: float
    :param width_firstsegment_zone3: Width of the first segment in zone 3
    :type width_firstsegment_zone3: float
    :param width_firstsegment_zone2: Width of the first segment in zone 2
    :type width_firstsegment_zone2: float
    :param udl_value: Uniform distributed load value (default: DEFAULT_UDL_VALUE)
    :type udl_value: float
    :returns: Dictionary containing real UDL traffic loads
    :rtype: dict[str, dict[str, Any]]
    """
    # Create an empty results dictionary
    results = {}

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    # Calculate UDL values based on berekeningsniveau
    main_value, other_value, rest_value = calculate_real_udl_values(params, length_bridgedeck, udl_value, psi_nen_8701_factor, alpha_trend_factor)
    # Calculate amount of notional lanes and lane width when starting on one side of the bridge deck

    y_top, width_road = obtain_y_coordinates_road(params)
    y_bottom = y_top - width_road
    max_lanes, lane_width = amount_of_notional_lanes(width_road)  # Maximum number of lanes to consider and lane width

    # BG4001: leftmost lanes (BG8000 logic)
    y_positions_left = generate_real_lane_positions_bg8000(params, lane_width)
    y_positions_right = generate_real_lane_positions_bg9000(params, lane_width)

    if y_positions_left:
        load_polygons: dict[str, list[dict[str, list[tuple[float, float, float]] | float]]] = {"main": [], "other": [], "rest": []}

        # Create lane polygons for up to max_lanes, starting from leftmost
        for lane_idx, y_center in enumerate(y_positions_left[:max_lanes]):
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]

            # First lane is "main", others are "other"
            if lane_idx == 0:
                load_polygons["main"].append({"polygon": lane_polygon, "load": main_value})
            else:
                load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

        # Create rest polygon for areas not covered by lanes
        max_lane_width = max_lanes * lane_width
        if max_lane_width < width_road:
            rest_polygon = [
                (0.0, y_top, 0.0),
                (length_bridgedeck, y_top, 0.0),
                (length_bridgedeck, y_bottom + max_lane_width, 0.0),
                (0.0, y_bottom + max_lane_width, 0.0),
            ]
            load_polygons["rest"].append({"polygon": rest_polygon, "load": rest_value})

        results["BG4001"] = load_polygons

    # BG4002: Rightmost lanes (BG9000 logic)
    if y_positions_right:
        load_polygons = {"main": [], "other": [], "rest": []}

        for lane_idx, y_center in enumerate(y_positions_right[:max_lanes]):
            y_min = y_center - lane_width / 2
            y_max = y_center + lane_width / 2
            lane_polygon = [
                (0.0, y_min, 0.0),
                (length_bridgedeck, y_min, 0.0),
                (length_bridgedeck, y_max, 0.0),
                (0.0, y_max, 0.0),
            ]

            if lane_idx == 0:
                load_polygons["main"].append({"polygon": lane_polygon, "load": main_value})
            else:
                load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

        # Rest polygon for area below lanes
        if max_lane_width < width_road:
            rest_polygon = [
                (0.0, y_top - max_lane_width, 0.0),
                (length_bridgedeck, y_top - max_lane_width, 0.0),
                (length_bridgedeck, y_bottom, 0.0),
                (0.0, y_bottom, 0.0),
            ]
            load_polygons["rest"].append({"polygon": rest_polygon, "load": rest_value})

        results["BG4002"] = load_polygons

    # BG4003: center lanes with dynamic number of lanes on each side
    # Calculate how many lanes can fit on each side of the center
    left_lanes, right_lanes, _ = amount_of_notional_lanes_from_center(width_road)
    total_lanes = 1 + left_lanes + right_lanes  # Center lane + left lanes + right lanes

    # Get the center position and adjust for zone offsets
    center_y = (y_top + y_bottom) / 2

    load_polygons = {"main": [], "other": [], "rest": []}

    # Create center (main) lane
    center_y_min = center_y - lane_width / 2
    center_y_max = center_y + lane_width / 2
    center_polygon = [
        (0.0, center_y_min, 0.0),
        (length_bridgedeck, center_y_min, 0.0),
        (length_bridgedeck, center_y_max, 0.0),
        (0.0, center_y_max, 0.0),
    ]
    load_polygons["main"].append({"polygon": center_polygon, "load": main_value})

    # Create left side lanes
    for i in range(left_lanes):
        y_center = center_y - (i + 1) * lane_width
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        lane_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

    # Create right side lanes
    for i in range(right_lanes):
        y_center = center_y + (i + 1) * lane_width
        y_min = y_center - lane_width / 2
        y_max = y_center + lane_width / 2
        lane_polygon = [
            (0.0, y_min, 0.0),
            (length_bridgedeck, y_min, 0.0),
            (length_bridgedeck, y_max, 0.0),
            (0.0, y_max, 0.0),
        ]
        load_polygons["other"].append({"polygon": lane_polygon, "load": other_value})

    # Create rest polygons for any remaining areas
    total_lanes_width = total_lanes * lane_width

    # Upper rest area (if exists)
    if center_y + total_lanes_width / 2 < width_road / 2:
        upper_rest = [
            (0.0, y_top, 0.0),
            (length_bridgedeck, y_top, 0.0),
            (length_bridgedeck, center_y + total_lanes_width / 2, 0.0),
            (0.0, center_y + total_lanes_width / 2, 0.0),
        ]
        load_polygons["rest"].append({"polygon": upper_rest, "load": rest_value})

        # Lower rest area (if exists)
        lower_rest = [
            (0.0, center_y - total_lanes_width / 2, 0.0),
            (length_bridgedeck, center_y - total_lanes_width / 2, 0.0),
            (length_bridgedeck, y_bottom, 0.0),
            (0.0, y_bottom, 0.0),
        ]
        load_polygons["rest"].append({"polygon": lower_rest, "load": rest_value})

    results["BG4003"] = load_polygons

    return results


# ========================================================================
# Theoretical tandem systems for BG8000 series
# ========================================================================


# Helper function to create wheel coordinates for a tandem
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


def generate_theoretical_lane_positions_bg8000(
    width_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for theoretical traffic lanes across bridge width.

    Creates lane center positions based on geometric division of bridge width.
    This provides the foundation for theoretical lane-based tandem loading.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers (shifted by -zone3_width)
    :rtype: list[float]
    :raises ValueError: If bridge_width or lane_width is not positive

    Examples:
        >>> generate_theoretical_lane_positions(30.0, DEFAULT_LANE_WIDTH, 2.0)
        [-0.5, 2.5, 5.5, 8.5, 11.5, 14.5, 17.5, 20.5, 23.5, 26.5]

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
        lane_centers.append(lane_center - zone3_width - LANE_CENTER_OFFSET_FACTOR * zone2_width)

    return lane_centers


def tandem_systems_theoretical_lanes_bg8000(  # noqa: PLR0913
    params: "BridgeParametrization",
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
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
    """
    wheel_size = TANDEM_CONTACT_AREA_SIDE

    # Get longitudinal positions (same as existing system)
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)

    # Get theoretical lane positions (NEW: replaces fixed positions)
    lane_y_positions = generate_theoretical_lane_positions_bg8000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]
    # Obtain load values
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    load_main = TANDEM_LOAD_BASE_MAIN / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = TANDEM_LOAD_BASE_SECOND / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = TANDEM_LOAD_BASE_THIRD / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    # Only generate for BG8 (first lane position)
    if lane_y_positions:
        y_lane_center = lane_y_positions[0]
        prefix = "BG8"
        for tandem_idx, x in enumerate(tandem_x_positions, 1):
            # Create main tandem wheels
            wheels_main = _create_tandem_wheels(x, y_lane_center, wheel_size)

            # Add load_case
            load_case: dict[str, Any] = {
                "load_case": f"{prefix}{tandem_idx:03d}",
            }

            # Add 200 kN tandem in next lane (if exists)
            wheels_200 = []
            if len(lane_y_positions) > 1:
                wheels_200 = _create_tandem_wheels(x, lane_y_positions[1], wheel_size)

            # Add 100 kN tandem in next-next lane (if exists)
            wheels_100 = []
            if len(lane_y_positions) > 2:
                wheels_100 = _create_tandem_wheels(x, lane_y_positions[2], wheel_size)

            load_case["loads"] = [
                {"wheels": wheels_main, "load": load_main},
                {"wheels": wheels_200, "load": load_second},
                {"wheels": wheels_100, "load": load_third},
            ]

            results.append(load_case)

    return results


# ========================================================================
# Theoretical tandem systems from the opposite side (BG9000)
# ========================================================================
def generate_theoretical_lane_positions_bg9000(
    width_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for theoretical traffic lanes across bridge width, starting from the right edge.

    This mirrors the original lane division, but lanes are counted from the right edge instead of the left.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers (shifted by -zone3_width), reversed
    :rtype: list[float]
    """
    if width_bridgedeck <= 0:
        raise ValueError("Bridge width must be positive")
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    num_lanes = int(width_bridgedeck // lane_width)
    lane_centers = []
    for lane_idx in range(num_lanes):
        # Start from the right edge
        lane_start = width_bridgedeck - lane_idx * lane_width
        lane_center = lane_start - (lane_width / 2)
        lane_centers.append(lane_center - zone3_width - LANE_CENTER_OFFSET_FACTOR * zone2_width)

    return lane_centers


def tandem_systems_theoretical_lanes_bg9000(  # noqa: PLR0913
    params: "BridgeParametrization",
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate tandem loads positioned at theoretical traffic lane centers, starting from the right edge.

    This function creates a critical loading scenario by mirroring the lane division and decreasing loads inwards.

    :param length_bridgedeck: Bridge length in meters
    :type length_bridgedeck: float
    :param width_bridgedeck: Bridge width in meters
    :type width_bridgedeck: float
    :param thickness_bridgedeck: Bridge thickness in meters
    :type thickness_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :returns: List of tandem load cases with full width coverage, reversed
    :rtype: list[dict[str, Any]]
    """
    wheel_size = TANDEM_CONTACT_AREA_SIDE
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)
    lane_y_positions = generate_theoretical_lane_positions_bg9000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    results = []
    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]
    # Obtain load values
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    load_main = TANDEM_LOAD_BASE_MAIN / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = TANDEM_LOAD_BASE_SECOND / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = TANDEM_LOAD_BASE_THIRD / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    # Only generate for BG9 (first lane position, reversed)
    if lane_y_positions:
        y_lane_center = lane_y_positions[0]
        prefix = "BG9"
        for tandem_idx, x in enumerate(tandem_x_positions, 1):
            # Create the main tandem wheels using our helper function
            wheels_main = _create_tandem_wheels(x, y_lane_center, wheel_size)

            load_case: dict[str, Any] = {
                "load_case": f"{prefix}{tandem_idx:03d}",
            }

            # 200 kN tandem in next lane (if exists)
            wheels_200 = []
            if len(lane_y_positions) > 1:
                wheels_200 = _create_tandem_wheels(x, lane_y_positions[1], wheel_size)

            # 100 kN tandem in next-next lane (if exists)
            wheels_100 = []
            if len(lane_y_positions) > 2:
                wheels_100 = _create_tandem_wheels(x, lane_y_positions[2], wheel_size)

            load_case["loads"] = [
                {"wheels": wheels_main, "load": load_main},
                {"wheels": wheels_200, "load": load_second},
                {"wheels": wheels_100, "load": load_third},
            ]

            results.append(load_case)

    return results


# ========================================================================
# Theoretical tandem systems from the center (BG10000)
# ========================================================================


def generate_theoretical_lane_positions_bg10000(
    width_bridgedeck: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
    zone3_width: float = 0.0,
    zone2_width: float = 0.0,
) -> list[float]:
    """
    Generate Y-positions for BG10000 load case: 300 kN in center, 200/100 kN adjacent if width permits.

    :param width_bridgedeck: Total bridge width in meters
    :type width_bridgedeck: float
    :param lane_width: Standard lane width in meters (default 3.0m)
    :type lane_width: float
    :param zone3_width: Width of zone 3 to shift all lane centers by (-zone3_width)
    :type zone3_width: float
    :returns: List of Y-coordinates for lane centers. Returns only center lane if width < 9m
    :rtype: list[float]
    """
    if width_bridgedeck <= 0:
        raise ValueError("Bridge width must be positive")
    if lane_width <= 0:
        raise ValueError("Lane width must be positive")

    # Center lane
    y_center = width_bridgedeck / 2 - zone3_width - LANE_CENTER_OFFSET_FACTOR * zone2_width

    # Only add adjacent lanes if we have at least MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES width (3 lanes of DEFAULT_LANE_WIDTH each)
    if width_bridgedeck >= MINIMUM_BRIDGE_WIDTH_FOR_MULTIPLE_LANES:
        # Left lane (adjacent to center)
        y_left = y_center - lane_width
        # Right lane (adjacent to center)
        y_right = y_center + lane_width
        return [y_center, y_left, y_right]
    # For narrow bridges, only return center lane
    return [y_center]


def tandem_systems_theoretical_lanes_bg10000(  # noqa: PLR0913
    params: "BridgeParametrization",
    length_bridgedeck: float,
    width_bridgedeck: float,
    thickness_bridgedeck: float,
    width_firstsegment_zone3: float,
    width_firstsegment_zone2: float,
    lane_width: float = DEFAULT_LANE_WIDTH,
) -> list[dict[str, Any]]:
    """
    Generate BG10000 load cases: 300 kN tandem in center always, 200/100 kN adjacent only if width permits.

    :param params: Bridge parametrization for load factors
    :param length_bridgedeck: Bridge length in meters
    :param width_bridgedeck: Bridge width in meters
    :param thickness_bridgedeck: Bridge thickness in meters
    :param width_firstsegment_zone3: Width of zone 3 in first segment
    :param width_firstsegment_zone2: Width of zone 2 in first segment
    :param lane_width: Standard lane width in meters (default 3.0m)
    :returns: List of BG10000 load cases. For narrow bridges (< 9m), only central tandem
    :rtype: list[dict[str, Any]]
    """
    wheel_size = TANDEM_CONTACT_AREA_SIDE
    tandem_x_positions = tandem_system_sequencer(length_bridgedeck, thickness_bridgedeck, length_vehicle=TANDEM_VEHICLE_LENGTH)
    lane_y_positions = generate_theoretical_lane_positions_bg10000(width_bridgedeck, lane_width, width_firstsegment_zone3, width_firstsegment_zone2)

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))
    alpha_q_factor = get_alpha_q_nen_en_1991_2(length_bridgedeck, nobs=NOBS_DEFAULT)[0]
    # Obtain load values
    contact_area = TANDEM_CONTACT_AREA_SIDE * TANDEM_CONTACT_AREA_SIDE
    load_main = TANDEM_LOAD_BASE_MAIN / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_second = TANDEM_LOAD_BASE_SECOND / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor
    load_third = TANDEM_LOAD_BASE_THIRD / contact_area * psi_nen_8701_factor * alpha_trend_factor * alpha_q_factor

    # Check if we have enough width for adjacent lanes (needs at least 9m)
    has_adjacent_lanes = len(lane_y_positions) > 1
    y_center = lane_y_positions[0]  # Center lane always exists

    prefix = "BG10"
    results = []
    idx = 1

    # For narrow bridges, only create central tandem at each position
    if not has_adjacent_lanes:
        for x in tandem_x_positions:
            # Create central 300kN tandem (always present)
            wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)

            load_case = {
                "load_case": f"{prefix}{idx:03d}",
                "loads": [{"wheels": wheels_300, "load": load_main}],
            }
            results.append(load_case)
            idx += 1
        return results

        # For wider bridges, create configurations sequentially
    y_left = lane_y_positions[1]
    y_right = lane_y_positions[2]

    # First, generate ALL Configuration A load cases (300 kN center, 200 kN left, 100 kN right)
    for x in tandem_x_positions:
        # Create central 300kN tandem
        wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)

        # Configuration A: 200 kN left, 100 kN right
        wheels_200_left = _create_tandem_wheels(x, y_left, wheel_size)
        wheels_100_right = _create_tandem_wheels(x, y_right, wheel_size)

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
        # Create central 300kN tandem
        wheels_300 = _create_tandem_wheels(x, y_center, wheel_size)

        # Configuration B: 100 kN left, 200 kN right
        wheels_100_left = _create_tandem_wheels(x, y_left, wheel_size)
        wheels_200_right = _create_tandem_wheels(x, y_right, wheel_size)

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


# ========================================================================
# Generation of tandem systems for real lane distribution (BG8000)
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
    if width_road <= 0 or None:
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


def tandem_systems_real_lanes_bg10000(  # noqa: C901, PLR0912
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

    # Obtain required factors for vertical traffic loading (LM1 and LM2)
    psi_nen_8701_factor = get_psi_nen_8701(length_bridgedeck, get_reference_period(params))
    alpha_trend_factor = get_alpha_trend_nen_8701(length_bridgedeck, (get_reference_period(params) + 2010))

    # Calculate loads based on berekeningsniveau
    load_main, load_second, load_third = calculate_real_tandem_values(params, length_bridgedeck, psi_nen_8701_factor, alpha_trend_factor)

    # Check if we have enough width for adjacent lanes (needs at least 9m)
    has_adjacent_lanes = len(lane_y_positions) > 1
    y_center = lane_y_positions[0]  # Center lane always exists

    prefix = "BG10"
    results = []
    idx = 1

    # For narrow roads, only create central tandem at each position
    if not has_adjacent_lanes:
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

        # For wider roads, create configurations sequentially
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


# ========================================================================
# Helper functions for service and accidental vehicle loads
# ========================================================================


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
