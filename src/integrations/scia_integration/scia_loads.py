"""
Module for creating SCIA loads.

This module provides functions for creating SCIA loads by calling the SciaModelBuilder.
These functions are pure Python and can be used by the app layer to construct the actual SCIA model.
"""

from typing import Any, Dict, List, TypedDict

# Type definitions for wheel configurations
class WheelConfig(TypedDict):
    """Type definition for standard vehicle wheel configuration."""
    position: str
    side: str
    corners_key: str
    load: float
    axle_locations: Dict[str, List[tuple[float, float, float]]]

class AmsterdamWheelConfig(TypedDict):
    """Type definition for Amsterdam vehicle wheel configuration."""
    position: str
    corners_key: str
    load: float

from src.geometry.load_zone_geometry import get_bridge_geom_data

from .scia_coordinate_utils import convert_loads_to_scia_format
from .scia_load_generators import extract_bridge_dimensions, generate_tandem_loads

# Import functions at runtime to avoid circular imports
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
    # Use the mode-aware UDL generation function
    from .scia_load_generators import generate_udl_loads

    # Generate UDL loads - this will auto-detect mode from berekeningsniveau
    udl_load_list = generate_udl_loads(params)

    # Convert from our standard format back to the expected format
    udl_results: dict[str, dict[str, Any]] = {}
    for load_data in udl_load_list:
        load_case = load_data["load_case"]
        # Extract the BG group from load_case (e.g., "BG4001_main" -> "BG4001")
        bg_group = load_case.split("_")[0]
        load_type = load_case.split("_")[1] if "_" in load_case else "main"

        if bg_group not in udl_results:
            udl_results[bg_group] = {"main": [], "other": [], "rest": []}

        udl_results[bg_group][load_type].append({"polygon": load_data["polygon"], "load": load_data["load_value"]})

    bg_to_rs = {"BG4001": "rs_1", "BG4002": "rs_2", "BG4003": "rs_3"}
    for key, udl in udl_results.items():
        rs_key = bg_to_rs.get(key)
        if rs_key and rs_key in load_cases["udl_traffic_cases"]:
            scia_case = load_cases["udl_traffic_cases"][rs_key]

            # Create surface loads for main notional lane(s)
            for i, main_load in enumerate(udl["main"]):
                builder.create_surface_load(
                    name=f"udl_{key}_main_{i + 1}",
                    load_case_name=scia_case.name,
                    corner_points=main_load["polygon"],
                    load_value=-main_load["load"],
                )

            # Create surface loads for other notional lanes
            for i, other_load in enumerate(udl["other"]):
                builder.create_surface_load(
                    name=f"udl_{key}_other_{i + 1}",
                    load_case_name=scia_case.name,
                    corner_points=other_load["polygon"],
                    load_value=-other_load["load"],
                )

            # Create surface loads for remaining areas
            for i, rest_load in enumerate(udl["rest"]):
                builder.create_surface_load(
                    name=f"udl_{key}_rest_{i + 1}",
                    load_case_name=scia_case.name,
                    corner_points=rest_load["polygon"],
                    load_value=-rest_load["load"],
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
    # Generate tandem loads based on theoretical lanes
    raw_tandem_data = generate_tandem_loads(params)  # Auto-detects mode from berekeningsniveau

    # Convert tandem data to SCIA format for surface loads
    scia_tandem_data = convert_loads_to_scia_format(raw_tandem_data)

    # Create surface loads using the builder, applying them to the correct load case
    for tandem in scia_tandem_data:
        load_case_name = tandem["load_case"]
        if params.input.berekeningsinstellingen.spreiding:
            # If dispersion is enabled, adjust each patch load's corners and load value
            for patch_load in tandem["patch_loads"]:
                dispersed_corners, dispersed_load_value = dispersal_function(
                    params=params,
                    corner_points=patch_load["corners"],
                    load_value=patch_load["load_value"],
                    load_case_type="axle_load",
                )
                patch_load["corners"] = dispersed_corners
                patch_load["load_value"] = dispersed_load_value

        for i, patch_load in enumerate(tandem["patch_loads"]):
            builder.create_surface_load(
                name=f"{load_case_name}_Wheel_{i + 1}",
                load_case_name=load_case_name,
                corner_points=patch_load["corners"],
                load_value=-patch_load["load_value"],  # Negative for downward load
            )


def dispersal_function(  # noqa: C901
    params: object,
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_case_type: str,
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
        params: object, coords: list[tuple[float, float, float]], load_case_type: str
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
            # Import at runtime to avoid circular imports
            from .scia_coordinate_utils import get_dispersion_at_coord

            dispersion_deck_zone = get_dispersion_at_coord(params=params, coord=coords[i])["deck_zone"]
            dispersion_load_zone = get_dispersion_at_coord(params=params, coord=coords[i])["load_zone"]

            # Add half the deck zone dispersion and the full load zone dispersion for each corner. Distinguish in x- and y-direction
            # Handle None values robustly
            deck_half = (dispersion_deck_zone / 2) if isinstance(dispersion_deck_zone, (int, float)) else 0.0
            load_full = dispersion_load_zone if isinstance(dispersion_load_zone, (int, float)) else 0.0
            dispersion_tot = deck_half + load_full
            dispersion_x_tot = dispersion_tot if load_case_type == "axle_load" else 0.0
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

    # If bridge geometry parameters are not available (e.g., in unit tests with simple mocks),
    # skip dispersion and return the original values to keep behavior predictable.
    if (
        not hasattr(params, "bridge_segments_array")
        or not isinstance(getattr(params, "bridge_segments_array"), list)
        or not getattr(params, "bridge_segments_array")
    ):
        return corner_points, load_value
    # For axle loads we also allow skipping dispersion if load zones are not defined
    if load_case_type == "axle_load" and (
        not hasattr(params, "load_zones_data_array")
        or not isinstance(getattr(params, "load_zones_data_array"), list)
        or not getattr(params, "load_zones_data_array")
    ):
        return corner_points, load_value

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
    from .scia_loads_helper import add_material_loads

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
    from .scia_loads_helper import add_material_loads

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
    from .scia_loads_helper import add_material_loads

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


def add_accidental_vehicle_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:  # noqa: C901, PLR0915
    """Add accidental vehicle loads to the SCIA model using sequenced X positions."""
    # Buitengewone belasting volgens NEN-EN 1991-2 art. 5.3.2.3(1)P
    vehicle_width = 1.30  # From diagram: 1.30 m between wheel centers
    vehicle_width_amsterdam = 2.0  # From diagram: 2.0 m between wheel centers
    force_axle_1 = 80 * 1000  # Q_sv1 = 80 kN, convert to N
    force_axle_2 = 40 * 1000  # Q_sv2 = 40 kN, convert to N
    force_axle_amsterdam = 240 * 1000  # Q_sv = 240 kN, convert to N
    wheel_contact_area = 0.20  # From diagram: 0.20 m contact area
    wheel_contact_area_amsterdam = 0.4  # From diagram: 0.4 m contact area
    axle_spacing = 1.2  # Derived from 3.0m total - wheel contact areas
    inset_distance = 0.5  # Distance from bridge edge to outer wheel (m)

    # Get bridge geometry data
    bridge_geom_data = get_bridge_geom_data(params)
    if bridge_geom_data is None:
        return

    # Extract bridge dimensions and get X positions
    dims = extract_bridge_dimensions(params)
    length = dims.total_length
    thickness = dims.thickness
    from .scia_loads_helper import tandem_system_sequencer, tandem_system_sequencer_single_axis, tandem_system_sequencer_single_axis_rotated

    # Obtain different x positions for the accidental vehicles
    positions = tandem_system_sequencer(length, thickness, length_vehicle=1.2)
    positions_amsterdam = tandem_system_sequencer_single_axis(length, thickness)
    positions_amsterdam_rotated = tandem_system_sequencer_single_axis_rotated(length, thickness, length_vehicle=2.0)

    # Get geometry coordinates
    y_top_structural_edge_at_d_points = bridge_geom_data.y_top_structural_edge_at_d_points
    y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points

    # Get load cases dictionary
    accidental_vehicle_cases = load_cases["unintended_vehicle_cases"]

    # Create the regular accidental vehicle loads from eurocode
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
        from .scia_loads_helper import calc_vehicle_load_locations

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
        # Define wheel configurations
        wheel_configs: List[WheelConfig] = [
            # front axle
            {
                "position": "front",
                "side": "left",
                "corners_key": "top_left_wheel_corners",
                "load": front_wheel_load,
                "axle_locations": front_axle_locations,
            },
            {
                "position": "front",
                "side": "right",
                "corners_key": "bottom_left_wheel_corners",
                "load": front_wheel_load,
                "axle_locations": front_axle_locations,
            },
            # rear axle
            {
                "position": "rear",
                "side": "left",
                "corners_key": "top_left_wheel_corners",
                "load": rear_wheel_load,
                "axle_locations": rear_axle_locations,
            },
            {
                "position": "rear",
                "side": "right",
                "corners_key": "bottom_left_wheel_corners",
                "load": rear_wheel_load,
                "axle_locations": rear_axle_locations,
            },
        ]

        # Create surface loads for each wheel
        for config in wheel_configs:
            corner_points = config["axle_locations"][config["corners_key"]]
            load_value = config["load"]

            # Apply dispersion if enabled
            if params.input.berekeningsinstellingen.spreiding:
                corner_points, load_value = dispersal_function(
                    params=params,
                    corner_points=corner_points,
                    load_value=load_value,
                    load_case_type="axle_load",
                )

            builder.create_surface_load(
                name=f"accidental_vehicle_{edge_type}_x{x_pos}_{direction}_{config['position']}_{config['side']}",
                load_case_name=load_case_name,
                corner_points=corner_points,
                load_value=-load_value,
            )

    # Create the amsterdam accidental vehicle loads, a single axis along the bridge deck
    def create_accidental_vehicle_amsterdam(x_pos: float, edge_type: str, y_coords: list[float]) -> None:
        """Create amsterdam accidental vehicle loads at a specific X position and direction."""
        # Get the load case keys
        load_case_key = f"{edge_type}_x{x_pos}_amsterdam"
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
            vehicle_top_edge = vehicle_bottom_edge + vehicle_width_amsterdam
        wheel_load = force_axle_amsterdam / (2 * (wheel_contact_area_amsterdam**2))  # N/m² per wheel

        # Use the same helper function as service vehicle for front axle
        from .scia_loads_helper import calc_vehicle_load_locations

        axle_locations = calc_vehicle_load_locations(
            x_coord=x_pos,  # Fix: Use single x_pos value instead of positions_amsterdam list
            y_coord=vehicle_top_edge,  # Pass vehicle top edge directly
            vehicle_length=wheel_contact_area_amsterdam,
            vehicle_width=vehicle_width_amsterdam,
            wheel_contact_area=wheel_contact_area_amsterdam,
        )
        # Define wheel configurations for Amsterdam vehicle (240 kN total = 120 kN per wheel)
        wheel_configs: List[AmsterdamWheelConfig] = [
            {
                "position": "left",
                "corners_key": "bottom_left_wheel_corners",
                "load": wheel_load,
            },
            {
                "position": "right",
                "corners_key": "top_left_wheel_corners",
                "load": wheel_load,
            },
        ]

        # Create surface loads for each wheel
        for config in wheel_configs:
            corner_points = axle_locations[config["corners_key"]]
            load_value = config["load"]

            # Apply dispersion if enabled
            if params.input.berekeningsinstellingen.spreiding:
                corner_points, load_value = dispersal_function(
                    params=params,
                    corner_points=corner_points,
                    load_value=load_value,
                    load_case_type="axle_load",
                )

            builder.create_surface_load(
                name=f"accidental_vehicle_{edge_type}_x{x_pos}_amsterdam_{config['position']}",
                load_case_name=load_case_name,
                corner_points=corner_points,
                load_value=-load_value,
            )

    # Create the rotated amsterdam accidental vehicle loads, a single axis perpendicular on the bridge deck, on the outer edges
    def create_accidental_vehicle_amsterdam_rotated(x_pos: float, edge_type: str, y_coords: list[float]) -> None:
        """Create rotated amsterdam accidental vehicle loads at a specific X position and direction."""
        # Get the load case keys
        load_case_key = f"{edge_type}_x{x_pos}_amsterdam_rotated"
        if load_case_key not in accidental_vehicle_cases:
            return
        load_case_name = accidental_vehicle_cases[load_case_key].name

        # Calculate vehicle top edge position with 0.5m inset from bridge edge
        # Helper function expects y_coord to be the vehicle's top edge (front-left corner)
        if edge_type == "rs_1":
            # For rs_1: top edge should be inward from bridge edge
            vehicle_top_edge = y_coords[0] - inset_distance
        else:  # rs_3
            # For rs_3: In this case we want the loads to be next to the bottom edge of the plate
            vehicle_bottom_edge = y_coords[0] + inset_distance
            vehicle_top_edge = vehicle_bottom_edge
        wheel_load = force_axle_amsterdam / (2 * (wheel_contact_area_amsterdam**2))  # N/m² per wheel

        # Use the same helper function as service vehicle for front axle (80 kN total)
        from .scia_loads_helper import calc_vehicle_load_locations

        axle_locations = calc_vehicle_load_locations(
            x_coord=x_pos,  # Fix: Use single x_pos value instead of positions_amsterdam list
            y_coord=vehicle_top_edge,  # Pass vehicle top edge directly
            vehicle_length=vehicle_width_amsterdam,
            vehicle_width=wheel_contact_area_amsterdam,
            wheel_contact_area=wheel_contact_area_amsterdam,
        )
        # Define wheel configurations for rotated Amsterdam vehicle (240 kN total = 120 kN per wheel)
        wheel_configs: List[AmsterdamWheelConfig] = [
            {
                "position": "bottom",
                "corners_key": "top_left_wheel_corners",
                "load": wheel_load,
            },
            {
                "position": "top",
                "corners_key": "top_right_wheel_corners",
                "load": wheel_load,
            },
        ]

        # Create surface loads for each wheel
        for config in wheel_configs:
            corner_points = axle_locations[config["corners_key"]]
            load_value = config["load"]

            # Apply dispersion if enabled
            if params.input.berekeningsinstellingen.spreiding:
                corner_points, load_value = dispersal_function(
                    params=params,
                    corner_points=corner_points,
                    load_value=load_value,
                    load_case_type="axle_load",
                )

            builder.create_surface_load(
                name=f"accidental_vehicle_{edge_type}_x{x_pos}_amsterdam_rotated_{config['position']}",
                load_case_name=load_case_name,
                corner_points=corner_points,
                load_value=-load_value,
            )

    # Create loads for each X position on both edges (RS 1 and RS 3) in both directions
    for x_pos in positions:
        # RS 1 (top edge) - both directions
        create_accidental_vehicle_at_position(x_pos, "rs_1", y_top_structural_edge_at_d_points, "forward")
        create_accidental_vehicle_at_position(x_pos, "rs_1", y_top_structural_edge_at_d_points, "reverse")

        # RS 3 (bottom edge) - both directions
        create_accidental_vehicle_at_position(x_pos, "rs_3", y_bridge_bottom_at_d_points, "forward")
        create_accidental_vehicle_at_position(x_pos, "rs_3", y_bridge_bottom_at_d_points, "reverse")

    # Create amsterdam vehicle loads
    for x_pos in positions_amsterdam:
        # RS 1 (top edge) - amsterdam vehicle
        create_accidental_vehicle_amsterdam(x_pos, "rs_1", y_top_structural_edge_at_d_points)
        # RS 3 (bottom edge) - amsterdam vehicle
        create_accidental_vehicle_amsterdam(x_pos, "rs_3", y_bridge_bottom_at_d_points)

    # Create rotated amsterdam vehicle loads
    for x_pos in positions_amsterdam_rotated:
        # RS 1 (top edge) - amsterdam vehicle rotated
        create_accidental_vehicle_amsterdam_rotated(x_pos, "rs_1", y_top_structural_edge_at_d_points)
        # RS 3 (bottom edge) - amsterdam vehicle rotated
        create_accidental_vehicle_amsterdam_rotated(x_pos, "rs_3", y_bridge_bottom_at_d_points)


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

    # Extract bridge dimensions and get X positions
    dims = extract_bridge_dimensions(params)
    length = dims.total_length
    thickness = dims.thickness
    from .scia_loads_helper import tandem_system_sequencer

    positions = tandem_system_sequencer(length, thickness, length_vehicle=3.25)

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
        from .scia_loads_helper import calc_vehicle_load_locations

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
            if params.input.berekeningsinstellingen.spreiding:
                builder.create_surface_load(
                    name=f"service_vehicle_{edge_type}_x{x_pos}_wheel_{j}",
                    load_case_name=load_case_name,
                    corner_points=corner_points_dispersed,
                    load_value=-load_value_dispersed,  # N/m²
                )
            else:
                builder.create_surface_load(
                    name=f"service_vehicle_{edge_type}_x{x_pos}_wheel_{j}",
                    load_case_name=load_case_name,
                    corner_points=wheel_corners,
                    load_value=-load_per_area,  # N/m²
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
