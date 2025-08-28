"""
Module for creating SCIA loads.

This module provides functions for creating SCIA loads by calling the SciaModelBuilder.
These functions are pure Python and can be used by the app layer to construct the actual SCIA model.
"""

from typing import Any

from src.geometry.load_zone_geometry import get_bridge_geom_data

from .scia_bridge_geometry import (
    convert_tandem_data_to_scia_format,
    extract_tandem_parameters_from_bridge,
    generate_tandem_loads_for_bridge,
    get_dispersion_at_coord
)
from .scia_loads_helper import add_material_loads, calc_vehicle_load_locations, create_udl_traffic_loads, tandem_system_sequencer
from .scia_model_interface import SciaModelBuilder

# Type alias to avoid importing from app layer
BridgeParametrization = Any


def add_udl_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    load_cases: dict[str, Any],
) -> None:
    """
    Create UDL traffic loads with separate polygons for main lane (9 kN/m²), other notional lanes (2.5 kN/m²),
    and remaining areas (2.5 kN/m²). Applied to load cases BG4001, BG4002, BG4003.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
    :param load_cases: Dictionary of created load cases.
    """
    # Extract bridge parameters needed for load geometry calculation
    bridge_params = extract_tandem_parameters_from_bridge(params)
    length = bridge_params["length_bridgedeck"]
    width = bridge_params["width_bridgedeck"]
    width_firstsegment_zone3 = bridge_params["width_firstsegment_zone3"]
    width_firstsegment_zone2 = bridge_params["width_firstsegment_zone2"]

    # Call the helper to get UDL polygons and loads
    udl_results = create_udl_traffic_loads(
        params,
        length,
        width,
        width_firstsegment_zone3,
        width_firstsegment_zone2,
    )

    bg_to_rs = {"BG4001": "rs_1", "BG4002": "rs_2", "BG4003": "rs_3"}
    for key, udl in udl_results.items():
        rs_key = bg_to_rs.get(key)
        if rs_key and rs_key in load_cases["udl_traffic_cases"]:
            scia_case = load_cases["udl_traffic_cases"][rs_key]

            # Create surface loads for main notional lane(s)
            for i, main_load in enumerate(udl["main"]):

                # Take into account load dispersion
                corner_points_dispersed, load_value_dispersed = dispersal_function(
                params=params, corner_points=main_load["polygon"], load_value=main_load["load"], load_case_type="udl"
                )

                builder.create_surface_load(
                    name=f"udl_{key}_main_{i + 1}",
                    load_case_name=scia_case.name,
                    corner_points=corner_points_dispersed,
                    load_value=-load_value_dispersed,
                )

            # Create surface loads for other notional lanes
            for i, other_load in enumerate(udl["other"]):

                # Take into account load dispersion
                corner_points_dispersed, load_value_dispersed = dispersal_function(
                    params=params, corner_points=other_load["polygon"], load_value=other_load["load"], load_case_type="udl"
                )

                builder.create_surface_load(
                    name=f"udl_{key}_other_{i + 1}",
                    load_case_name=scia_case.name,
                    corner_points=corner_points_dispersed,
                    load_value=-load_value_dispersed,
                )

            # Create surface loads for remaining areas
            for i, rest_load in enumerate(udl["rest"]):

                # Take into account load dispersion
                corner_points_dispersed, load_value_dispersed = dispersal_function(
                    params=params, corner_points=rest_load["polygon"], load_value=rest_load["load"], load_case_type="udl"
                )

                builder.create_surface_load(
                    name=f"udl_{key}_rest_{i + 1}",
                    load_case_name=scia_case.name,
                    corner_points=corner_points_dispersed,
                    load_value=-load_value_dispersed,
                )


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
    raw_tandem_data = generate_tandem_loads_for_bridge(params, bridge_params, mode="theoretical")

    # 3. Convert tandem data to SCIA format for surface loads
    scia_tandem_data = convert_tandem_data_to_scia_format(raw_tandem_data)

    # 4. Create surface loads using the builder, applying them to the correct load case
    for tandem in scia_tandem_data:
        load_case_name = tandem["load_case"]
        for i, patch_load in enumerate(tandem["patch_loads"]):

            # Take into account load dispersion
            corner_points_dispersed, load_value_dispersed = dispersal_function(
                params=params, corner_points=patch_load["corners"], load_value=patch_load["load_value"], load_case_type="axle_load"
            )

            # Pass through the builder
            builder.create_surface_load(
                name=f"{load_case_name}_Wheel_{i + 1}",
                load_case_name=load_case_name,
                corner_points=corner_points_dispersed,
                load_value=-load_value_dispersed,  # Negative for downward load
            )


def dispersal_function(
    params: Any,  # noqa: ARG001
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_case_type: str
) -> tuple[list[tuple[float, float, float]], float]:
    """
    Disperse the load value across the corners based on bridge parameters.

    :param params: Bridge parameters used for dispersion logic.
    :type params: Any
    :param corner_points: List of corner points for the load (each as (x, y, z)).
    :type corner_points: list[tuple[float, float, float]]
    :param load_value: Load value to be dispersed.
    :type load_value: float
    :returns: Tuple of (dispersed corner points, adjusted load value).
    :rtype: tuple[list[tuple[float, float, float]], float]
    """

    def _calculate_quadrilateral_area(coords: list[tuple[float, float, float]]) -> float:
        """
        Calculates the area spanned by four coordinates (assumed to be a planar quadrilateral).

        :param coords: List of four (x, y, z) tuples representing the vertices in order.
        :type coords: list[tuple[float, float, float]]
        :returns: Area of the quadrilateral in the XY plane.
        :rtype: float
        :raises ValueError: If the input does not contain exactly four coordinates.
        """
        if len(coords) != 4:
            raise ValueError("Exactly four coordinates are required.")
        # Project to XY plane
        xy = [(x, y) for x, y, _ in coords]
        # Shoelace formula for quadrilateral
        area = 0.0
        for i in range(4):
            x1, y1 = xy[i]
            x2, y2 = xy[(i + 1) % 4]
            area += x1 * y2 - x2 * y1
        return abs(area) * 0.5


    def _expand_corners_with_dispersion(
        params: Any,  # noqa: ARG001
        coords: list[tuple[float, float, float]],
        load_case_type: str
    ) -> list[tuple[float, float, float]]:
        """
        Expands the quadrilateral defined by four coordinates to include dispersion in x and y directions for each corner.
        Dispersion is calculated using get_dispersion_at_coord for each corner.
        Assumes corners are ordered: [bottom-right, top-right, top-left, bottom-left].
        """
        if len(coords) != 4:
            raise ValueError("Exactly four coordinates are required.")
        expanded_coords = []
        for i in range(4):
            x, y, z = coords[i]
            dispersion_deck_zone = get_dispersion_at_coord(params=params, coord=coords[i])["deck_zone"]
            dispersion_load_zone = get_dispersion_at_coord(params=params, coord=coords[i])["load_zone"]

            # Add half the deck zone dispersion and the full load zone dispersion for each corner. Distinguish in x- and y-direction
            dispersion_tot = dispersion_deck_zone / 2 + dispersion_load_zone
            if load_case_type == 'axle_load':
                dispersion_x_tot = dispersion_tot
            else:
                dispersion_x_tot = 0
            dispersion_y_tot = dispersion_tot

            # Expand in the correct direction for each corner based on its position
            if i == 0:  # bottom-right
                expanded_coords.append((x + dispersion_x_tot, y - dispersion_y_tot, z))
            elif i == 1:  # top-right
                expanded_coords.append((x + dispersion_x_tot, y + dispersion_y_tot, z))
            elif i == 2:  # top-left
                expanded_coords.append((x - dispersion_x_tot, y + dispersion_y_tot, z))
            elif i == 3:  # bottom-left
                expanded_coords.append((x - dispersion_x_tot, y - dispersion_y_tot, z))
        return expanded_coords

    dispersed_load_coords = _expand_corners_with_dispersion(params=params, coords=corner_points, load_case_type=load_case_type)
    initial_load_area = _calculate_quadrilateral_area(coords=corner_points)
    dispersed_load_area = _calculate_quadrilateral_area(coords=dispersed_load_coords)
    dispersed_load_value = load_value * (initial_load_area / dispersed_load_area)

    return dispersed_load_coords, dispersed_load_value


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
    # Get parapet line load value, defaulting to 0 if not specified
    try:
        leuning_value = params.input.belastingzones.lijnlast_leuning
        leuning_numeric = float(leuning_value) if leuning_value is not None else 0.0
    except (AttributeError, ValueError, TypeError):
        # If the parameter structure is missing or invalid, use default value
        leuning_numeric = 0.0

    load_value = leuning_numeric * 1000  # Convert to N/m

    # Get the parapet load case name from the load cases dictionary
    parapet_load_case = load_cases["dead_load_cases"]["leuning"]
    load_case_name = parapet_load_case.name

    # builder.plates is now a dict: {plate_name: Plane}
    plates = getattr(builder, "plates", {})
    if not isinstance(plates, dict):
        return []
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


def add_accidental_vehicle_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:
    """Add accidental vehicle loads to the SCIA model using sequenced X positions."""
    # Buitengewone belasting volgens NEN-EN 1991-2 art. 5.3.2.3(1)P
    vehicle_width = 1.30  # From diagram: 1.30 m between wheel centers
    force_axle_1 = 80 * 1000  # Q_sv1 = 80 kN, convert to N
    force_axle_2 = 40 * 1000  # Q_sv2 = 40 kN, convert to N
    wheel_contact_area = 0.20  # From diagram: 0.20 m contact area
    axle_spacing = 1.2  # Derived from 3.0m total - wheel contact areas
    inset_distance = 0.5  # Distance from bridge edge to outer wheel (m)

    # Get bridge geometry data
    bridge_geom_data = get_bridge_geom_data(params)
    if bridge_geom_data is None:
        return

    # Extract bridge parameters and get X positions
    bridge_params = extract_tandem_parameters_from_bridge(params)
    length = bridge_params["length_bridgedeck"]
    thickness = bridge_params["thickness_bridgedeck"]
    positions = tandem_system_sequencer(length, thickness)

    # Get geometry coordinates
    y_top_structural_edge_at_d_points = bridge_geom_data.y_top_structural_edge_at_d_points
    y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points

    # Get load cases dictionary
    accidental_vehicle_cases = load_cases["unintended_vehicle_cases"]

    def create_accidental_vehicle_at_position(x_pos: float, edge_type: str, y_coords: list[float], direction: str) -> None:
        """Create accidental vehicle loads at a specific X position and direction."""
        # Get the appropriate load case for this position, edge, and direction
        load_case_key = f"{edge_type}_x{x_pos}_{direction}"
        if load_case_key not in accidental_vehicle_cases:
            return

        load_case_name = accidental_vehicle_cases[load_case_key].name

        # Calculate vehicle top edge position with 0.5m inset from bridge edge
        # Helper function expects y_coord to be the vehicle's top edge (front-left corner)
        if edge_type == "rs_1":
            # For rs_1: top edge should be inward from bridge edge
            vehicle_top_edge = y_coords[0] - inset_distance
        else:  # rs_3
            # For rs_3: bottom edge should be inward, so top edge = bottom edge + vehicle_width
            vehicle_bottom_edge = y_coords[0] + inset_distance
            vehicle_top_edge = vehicle_bottom_edge + vehicle_width

        # Determine front axle position based on direction (80 kN axle should always be the "front")
        # Forward: 80 kN front axle at x_pos, 40 kN rear axle at x_pos + axle_spacing
        # Reverse: 80 kN front axle at x_pos + axle_spacing, 40 kN rear axle at x_pos
        front_axle_x = x_pos if direction == "forward" else x_pos + axle_spacing

        # Calculate wheel contact area and load per unit area
        wheel_area = wheel_contact_area * wheel_contact_area  # Square contact area

        # Load per wheel (divide axle load by 2 wheels per axle) then by contact area
        front_wheel_force = force_axle_1 / 2  # 40 kN per front wheel (80 kN total)
        rear_wheel_force = force_axle_2 / 2  # 20 kN per rear wheel (40 kN total)

        # Calculate wheel load pressure (N/m²) from force and contact area
        front_wheel_load = front_wheel_force / wheel_area  # N/m²
        rear_wheel_load = rear_wheel_force / wheel_area  # N/m²

        # Use the same helper function as service vehicle for front axle (80 kN total)
        front_axle_locations = calc_vehicle_load_locations(
            x_coord=front_axle_x,
            y_coord=vehicle_top_edge,  # Pass vehicle top edge directly
            vehicle_length=wheel_contact_area,  # Single axle, so length = contact area
            vehicle_width=vehicle_width,
            wheel_contact_area=wheel_contact_area,
        )

        # Use the same helper function for rear axle (40 kN total)
        rear_axle_x = front_axle_x + axle_spacing if direction == "forward" else front_axle_x - axle_spacing
        rear_axle_locations = calc_vehicle_load_locations(
            x_coord=rear_axle_x,
            y_coord=vehicle_top_edge,
            vehicle_length=wheel_contact_area,
            vehicle_width=vehicle_width,
            wheel_contact_area=wheel_contact_area,
        )

        # Take into account load dispersion for the front axle wheels
        corner_points_dispersed_front, load_value_dispersed_front = dispersal_function(
            params=params, corner_points=front_axle_locations["top_left_wheel_corners"], load_value=front_wheel_load, load_case_type="axle_load"
        )

        # Take into account load dispersion for the rear axle wheels
        corner_points_dispersed_rear, load_value_dispersed_rear = dispersal_function(
            params=params, corner_points=rear_axle_locations["top_left_wheel_corners"], load_value=rear_wheel_load, load_case_type="axle_load"
        )

        # Create surface loads for front axle wheels (80 kN total = 40 kN per wheel)
        builder.create_surface_load(
            name=f"accidental_vehicle_{edge_type}_x{x_pos}_{direction}_front_left",
            load_case_name=load_case_name,
            corner_points=corner_points_dispersed_front,
            load_value=-load_value_dispersed_front,
        )

        builder.create_surface_load(
            name=f"accidental_vehicle_{edge_type}_x{x_pos}_{direction}_front_right",
            load_case_name=load_case_name,
            corner_points=corner_points_dispersed_front,
            load_value=-load_value_dispersed_front,
        )

        # Create surface loads for rear axle wheels (40 kN total = 20 kN per wheel)
        builder.create_surface_load(
            name=f"accidental_vehicle_{edge_type}_x{x_pos}_{direction}_rear_left",
            load_case_name=load_case_name,
            corner_points=corner_points_dispersed_rear,
            load_value=-load_value_dispersed_rear,
        )

        builder.create_surface_load(
            name=f"accidental_vehicle_{edge_type}_x{x_pos}_{direction}_rear_right",
            load_case_name=load_case_name,
            corner_points=corner_points_dispersed_rear,
            load_value=-load_value_dispersed_rear,
        )

    # Create loads for each X position on both edges (RS 1 and RS 3) in both directions
    for x_pos in positions:
        # RS 1 (top edge) - both directions
        create_accidental_vehicle_at_position(x_pos, "rs_1", y_top_structural_edge_at_d_points, "forward")
        create_accidental_vehicle_at_position(x_pos, "rs_1", y_top_structural_edge_at_d_points, "reverse")

        # RS 3 (bottom edge) - both directions
        create_accidental_vehicle_at_position(x_pos, "rs_3", y_bridge_bottom_at_d_points, "forward")
        create_accidental_vehicle_at_position(x_pos, "rs_3", y_bridge_bottom_at_d_points, "reverse")


def add_service_vehicle_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:
    """Add service vehicle loads to the SCIA model using sequenced X positions."""
    # Dienstvoertuig volgens NEN-EN 1991-2 art. 5.3.2.3
    vehicle_length = 3.0
    vehicle_width = 1.75
    force_per_axle = 25 * 1000  # Convert to N
    wheel_contact_area = 0.25
    inset_distance = 0.5  # Distance from bridge edge to outer wheel (m)

    # Get bridge geometry data
    bridge_geom_data = get_bridge_geom_data(params)
    if bridge_geom_data is None:
        return

    # Extract bridge parameters and get X positions
    bridge_params = extract_tandem_parameters_from_bridge(params)
    length = bridge_params["length_bridgedeck"]
    thickness = bridge_params["thickness_bridgedeck"]
    positions = tandem_system_sequencer(length, thickness)

    # Get geometry coordinates
    y_top_structural_edge_at_d_points = bridge_geom_data.y_top_structural_edge_at_d_points
    y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points

    # Get load cases dictionary
    service_vehicle_cases = load_cases["service_vehicle_cases"]

    def create_service_vehicle_at_position(x_pos: float, edge_type: str, y_coords: list[float]) -> None:
        """Create service vehicle loads at a specific X position."""
        # Get the appropriate load case for this position and edge
        load_case_key = f"{edge_type}_x{x_pos}"
        if load_case_key not in service_vehicle_cases:
            return

        load_case_name = service_vehicle_cases[load_case_key].name

        # Calculate vehicle top edge position with 0.5m inset from bridge edge
        # Helper function expects y_coord to be the vehicle's top edge (front-left corner)
        if edge_type == "y_plus":
            # For y_plus: top edge should be inward from bridge edge
            vehicle_top_edge = y_coords[0] - inset_distance
        else:  # y_minus
            # For y_minus: bottom edge should be inward, so top edge = bottom edge + vehicle_width
            vehicle_bottom_edge = y_coords[0] + inset_distance
            vehicle_top_edge = vehicle_bottom_edge + vehicle_width

        # Calculate wheel contact area and load per unit area
        wheel_area = wheel_contact_area * wheel_contact_area  # Square contact area
        force_per_wheel = force_per_axle / 2  # Divide axle load by 2 wheels
        load_per_area = force_per_wheel / wheel_area  # N/m²

        # Use the helper function to calculate wheel positions
        wheel_locations = calc_vehicle_load_locations(
            x_coord=x_pos,
            y_coord=vehicle_top_edge,  # Pass vehicle top edge directly
            vehicle_length=vehicle_length,
            vehicle_width=vehicle_width,
            wheel_contact_area=wheel_contact_area,
        )

        # Create surface loads for each wheel
        for j, (wheel_loc, wheel_corners) in enumerate(wheel_locations.items()):
            

            # Take into account load dispersion
            corner_points_dispersed, load_value_dispersed = dispersal_function(
                params=params, corner_points=wheel_corners, load_value=load_per_area, load_case_type="axle_load"
            )

            builder.create_surface_load(
                name=f"service_vehicle_{edge_type}_x{x_pos}_wheel_{j}",
                load_case_name=load_case_name,
                corner_points=corner_points_dispersed,
                load_value=-load_value_dispersed,  # N/m²
            )

    # Create loads for each X position on both edges
    for x_pos in positions:
        create_service_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points)
        create_service_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points)


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
    add_udl_loads(builder, params, load_cases)
    add_theoretical_tandem_loads(builder, params, load_cases)

    add_service_vehicle_loads(builder, params, load_cases)
    add_accidental_vehicle_loads(builder, params, load_cases)

    # TODO: Add calls to other load functions when they are implemented
    # add_actual_tandem_loads(builder, params, load_cases)  # noqa: ERA001
    # add_railing_loads(builder, params, load_cases)  # noqa: ERA001
    # add_pedestrian_loads(builder, params, load_cases)  # noqa: ERA001
