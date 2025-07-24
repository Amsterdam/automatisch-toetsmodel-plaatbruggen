"""
Module for creating SCIA loads.

This module provides functions for creating SCIA loads by calling the SciaModelBuilder.
These functions are pure Python and can be used by the app layer to construct the actual SCIA model.
"""

from typing import Any

from src.geometry.load_zone_geometry import calculate_zone_geometry_properties, get_bridge_geom_data, get_load_zones_data_from_params

from .scia_bridge_geometry import (
    convert_tandem_data_to_scia_format,
    extract_tandem_parameters_from_bridge,
    generate_tandem_loads_for_bridge,
)
from .scia_loads_helper import add_material_loads, calc_vehicle_load_locations, interpolate_points_along_line
from .scia_model_interface import SciaModelBuilder

# Type alias to avoid importing from app layer
BridgeParametrization = Any


def add_theoretical_tandem_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    _load_cases: dict[str, Any],
) -> None:
    """
    Create theoretical tandem loads and apply them to their existing load cases.

    This function assumes that the required load cases have already been created
    by `create_all_load_cases`.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
    :param load_cases: Dictionary of created load cases.
    """
    # 1. Extract bridge parameters needed for load geometry calculation
    bridge_params = extract_tandem_parameters_from_bridge(params)

    # 2. Generate tandem loads based on theoretical lanes
    raw_tandem_data = generate_tandem_loads_for_bridge(bridge_params, mode="theoretical")

    # 3. Convert tandem data to SCIA format for surface loads
    scia_tandem_data = convert_tandem_data_to_scia_format(raw_tandem_data)

    # 4. Create surface loads using the builder, applying them to the correct load case
    for tandem in scia_tandem_data:
        load_case_name = tandem["load_case"]
        for i, patch_load in enumerate(tandem["patch_loads"]):
            builder.create_surface_load(
                name=f"{load_case_name}_Wheel_{i + 1}",
                load_case_name=load_case_name,
                corner_points=patch_load["corners"],
                load_value=-patch_load["load_value"],  # Negative for downward load
            )


def add_actual_tandem_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
    _load_cases: dict[str, Any],
) -> list[Any]:
    """PLACEHOLDER: Add actual tandem loads based on user-defined lanes."""
    # This will be implemented when user-defined lanes are supported.
    return []


def add_parapet_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add permanent line loads for parapets (railing) to the SCIA model.

    Places line loads:
    - On edge 1 of all zone 3 plates (Z3)
    - On edge 3 of all zone 1 plates (Z1)

    :param builder: SCIA model builder instance
    :param params: Bridge parameters (should provide plate_definitions)
    :param load_cases: Dictionary of created load cases.
    """
    load_value = params.input.belastingzones.lijnlast_leuning * 1000  # Convert to kN/m

    # Get the parapet load case name from the load cases dictionary
    parapet_load_case = load_cases["dead_load_cases"]["leuning"]
    load_case_name = parapet_load_case.name

    # builder.plates is now a dict: {plate_name: Plane}
    plates = getattr(builder, "plates", {})
    for plate_name, _plane in plates.items():  # noqa: PERF102
        # Expect plate_name like 'Z1_1', 'Z3_2', etc.
        try:
            zone_part = plate_name.split("_")[0]  # e.g., 'Z1'
            zone_number = int(zone_part[1:])
        except (IndexError, ValueError):
            continue
        if zone_number == 3:
            builder.create_line_load_on_plane(
                name=f"parapet_load_zone3_{plate_name}",
                load_case_name=load_case_name,
                plane_name=plate_name,
                edge_index=3,
                load_value=-load_value,
            )
        elif zone_number == 1:
            builder.create_line_load_on_plane(
                name=f"parapet_load_zone1_{plate_name}",
                load_case_name=load_case_name,
                plane_name=plate_name,
                edge_index=1,
                load_value=-load_value,
            )
    return []


def add_pedestrian_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
    _load_cases: dict[str, Any],
) -> list[Any]:
    """PLACEHOLDER: Add pedestrian loads to the SCIA model."""
    # This will be implemented based on pedestrian area parameters.
    return []


def add_asfalt_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """Add asphalt loads to the SCIA model."""
    # Get the asphalt load case name from the load cases dictionary
    asphalt_load_case = load_cases["dead_load_cases"]["asfalt"]
    load_case_name = asphalt_load_case.name

    material_config = {"Asfalt": load_case_name}
    add_material_loads(builder, params, material_config)
    return []


def add_concrete_fill_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """Add concrete fill loads to the SCIA model."""
    # Get the concrete fill load case name from the load cases dictionary
    concrete_fill_load_case = load_cases["dead_load_cases"]["uitvulling"]
    load_case_name = concrete_fill_load_case.name

    material_config = {
        "Beton (normaal)": load_case_name,
        "Beton (gewapend)": load_case_name,
    }
    add_material_loads(builder, params, material_config)
    return []


def add_pavement_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """Add pavement loads (klinkers, grind, tegels) to the SCIA model."""
    # Get the pavement load case name from the load cases dictionary
    pavement_load_case = load_cases["dead_load_cases"]["ophogingen"]
    load_case_name = pavement_load_case.name

    material_config = {
        "Klinkers": load_case_name,
        "Grind": load_case_name,
        "Tegels": load_case_name,
    }
    add_material_loads(builder, params, material_config)
    return []


def add_crowd_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    load_cases: dict[str, Any],
) -> list[Any]:
    """PLACEHOLDER: Add crowd loads to the SCIA model."""
    # Crowd load according to NEN-EN 1991-2 art. 5.3.2.1 (LM4)
    crowd_load_per_sqm = 5.0  # kN/m²
    crowd_load_per_sqm_n = crowd_load_per_sqm * 1000  # Convert to N/m²

    # Get load zone information from params using the utility functions
    bridge_geom_data = get_bridge_geom_data(params)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return []

    y_top = bridge_geom_data.y_top_structural_edge_at_d_points[0]
    y_bottom = bridge_geom_data.y_bridge_bottom_at_d_points[0]
    x_left = bridge_geom_data.x_coords_d_points[0]
    x_right = bridge_geom_data.x_coords_d_points[-1]

    corners = [
        (x_left, y_top, 0.0),
        (x_right, y_top, 0.0),
        (x_right, y_bottom, 0.0),
        (x_left, y_bottom, 0.0),
    ]

    # Get the pedestrian load case name from the load cases dictionary
    pedestrian_load_case = load_cases["pedestrian"]
    load_case_name = pedestrian_load_case.name

    builder.create_surface_load(
        name="mensenmenigte_belasting",
        load_case_name=load_case_name,
        corner_points=corners,
        load_value=-crowd_load_per_sqm_n,  # Negative for downward load
    )
    return []  # Placeholder return to match function signature


def add_service_vehicle_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:
    """Add service vehicle loads to the SCIA model."""
    # Dienstvoertuig volgens NEN-EN 1991-2 art. 5.3.2.3
    vehicle_length = 3.0
    vehicle_width = 1.75
    force_per_axle = 25 * 1000  # Convert to N/m2
    wheel_contact_area = 0.25

    # Get load zone information from params using the utility functions
    load_zones_data_params = get_load_zones_data_from_params(params)
    bridge_geom_data = get_bridge_geom_data(params)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return

    # Update load zones data with geometry properties
    load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

    # Get the service vehicle load case names from the load cases dictionary
    service_vehicle_cases = load_cases["service_vehicle_cases"]
    y_plus_load_case = service_vehicle_cases["y_plus"]
    y_minus_load_case = service_vehicle_cases["y_minus"]
    y_plus_load_case_name = y_plus_load_case.name
    y_minus_load_case_name = y_minus_load_case.name

    # TODO for now we only add the service vehicle loads on the edge of the bridge
    # in the future we can filter out a load zone based on name etc.
    # the input is basically a list of points that represent a line along the bridge
    x_coords_d_points = bridge_geom_data.x_coords_d_points
    y_top_structural_edge_at_d_points = bridge_geom_data.y_top_structural_edge_at_d_points
    y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points

    # Create a line representing the top bridge edge using x and y coordinates
    top_bridge_edge_line = [(x, y, 0.0) for x, y in zip(x_coords_d_points, y_top_structural_edge_at_d_points)]

    # Interpolate points every 0.5m along the top bridge edge and add offsets for wheel contact area
    top_edge_points_interpolated = interpolate_points_along_line(top_bridge_edge_line, 0.5)
    y_offset_top = -wheel_contact_area / 2  # Offset for the top edge points
    x_offset_top = wheel_contact_area / 2  # No offset for the top edge points
    top_edge_points_interpolated = [(x + x_offset_top, y + y_offset_top, z) for x, y, z in top_edge_points_interpolated]

    # Create a line representing the bottom bridge edge using x and y coordinates
    bottom_bridge_edge_line = [(x, y, 0.0) for x, y in zip(x_coords_d_points, y_bridge_bottom_at_d_points)]

    # Interpolate points every 0.5m along the bottom bridge edge and add offsets for wheel contact area
    bottom_edge_points_interpolated = interpolate_points_along_line(bottom_bridge_edge_line, 0.5)
    y_offset_bottom = wheel_contact_area / 2 + vehicle_width  # Offset for the bottom edge points
    x_offset_bottom = wheel_contact_area / 2  # No offset for the bottom edge points
    bottom_edge_points_interpolated = [(x + x_offset_bottom, y + y_offset_bottom, z) for x, y, z in bottom_edge_points_interpolated]

    # Trim top_edge_points_interpolated so that the last x value is <= last x - vehicle_length - wheel_contact_area/
    # This ensures that the last wheel load does not extend beyond the bridge edge
    if top_edge_points_interpolated:
        last_x_top = top_edge_points_interpolated[-1][0]
        top_edge_points_interpolated = [pt for pt in top_edge_points_interpolated if pt[0] <= last_x_top - vehicle_length - wheel_contact_area / 2]

    # Trim bottom_edge_points_interpolated so that the last x value is <= last x - vehicle_length - wheel_contact_area/2
    # This ensures that the last wheel load does not extend beyond the bridge edge
    if bottom_edge_points_interpolated:
        last_x_bottom = bottom_edge_points_interpolated[-1][0]
        bottom_edge_points_interpolated = [
            pt for pt in bottom_edge_points_interpolated if pt[0] <= last_x_bottom - vehicle_length - wheel_contact_area / 2
        ]

    # Create service vehicle load locations based on the interpolated points
    # top edge
    for i, (x, y, z) in enumerate(top_edge_points_interpolated):
        # Calculate wheel locations based on the vehicle length and width
        # This will return a dictionary with wheel locations and their corner points
        wheel_locations = calc_vehicle_load_locations(
            x_coord=x,
            y_coord=y,
            vehicle_length=vehicle_length,
            vehicle_width=vehicle_width,
            wheel_contact_area=wheel_contact_area,
        )

        # Create surface load cases for each wheel location
        for j, (wheel_loc, wheel_corners) in enumerate(wheel_locations.items()):
            # Create surface load for each wheel
            builder.create_surface_load(
                name=f"service_vehicle_top_{i}_{j}",
                load_case_name=y_plus_load_case_name,
                corner_points=wheel_corners,
                load_value=-force_per_axle,
            )

    # bottom edge
    for i, (x, y, z) in enumerate(bottom_edge_points_interpolated):
        # Calculate wheel locations based on the vehicle length and width
        wheel_locations = calc_vehicle_load_locations(
            x_coord=x,
            y_coord=y,
            vehicle_length=vehicle_length,
            vehicle_width=vehicle_width,
            wheel_contact_area=wheel_contact_area,
        )
        # This will return a dictionary with wheel locations and their corner points
        # Create surface load cases for each wheel location
        for j, (wheel_loc, wheel_corners) in enumerate(wheel_locations.items()):
            builder.create_surface_load(
                name=f"service_vehicle_bottom_{i}_{j}",
                load_case_name=y_minus_load_case_name,
                corner_points=wheel_corners,
                load_value=-force_per_axle,
            )


def create_all_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:
    """
    Create and apply all load types to the bridge model.

    This function orchestrates the application of all loads, including:
    - Tandem system loads
    - Railing loads (placeholder)
    - Pedestrian loads (placeholder)

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    :param load_cases: Dictionary of created load cases.
    """
    # Apply theoretical tandem loads
    add_asfalt_loads(builder, params, load_cases)
    add_concrete_fill_loads(builder, params, load_cases)
    add_pavement_loads(builder, params, load_cases)
    add_parapet_loads(builder, params, load_cases)
    add_crowd_loads(builder, params, load_cases)
    add_theoretical_tandem_loads(builder, params, load_cases)

    add_service_vehicle_loads(builder, params, load_cases)

    # TODO: Add calls to other load functions when they are implemented
    # add_actual_tandem_loads(builder, params, load_cases)  # noqa: ERA001
    # add_railing_loads(builder, params, load_cases)  # noqa: ERA001
    # add_pedestrian_loads(builder, params, load_cases)  # noqa: ERA001
