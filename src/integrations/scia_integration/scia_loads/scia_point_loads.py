"""
SCIA point loads module.

This module provides functions for creating point loads (tandem and vehicle loads)
by calling the SciaModelBuilder interface. These functions handle concentrated
loads from vehicles and tandem systems.
"""

from typing import Any

from src.combinations.load_factors import get_dynamic_load_factor
from src.geometry.load_zone_geometry import get_bridge_geom_data, get_tram_track_y_coordinates
from src.integrations.scia_integration.constants.vehicles import (
    ACCIDENTAL_VEHICLE_AXLE_SPACING,
    ACCIDENTAL_VEHICLE_AXLE_SPACING_AMSTERDAM,
    ACCIDENTAL_VEHICLE_FORCE_AMSTERDAM,
    ACCIDENTAL_VEHICLE_FORCE_AXLE_1,
    ACCIDENTAL_VEHICLE_FORCE_AXLE_2,
    ACCIDENTAL_VEHICLE_INSET_DISTANCE,
    ACCIDENTAL_VEHICLE_WHEEL_DIMENSION_AMSTERDAM,
    ACCIDENTAL_VEHICLE_WHEEL_DIMENSION_STANDARD,
    ACCIDENTAL_VEHICLE_WIDTH_AMSTERDAM,
    ACCIDENTAL_VEHICLE_WIDTH_STANDARD,
    SERVICE_VEHICLE_AXLE_SPACING,
    SERVICE_VEHICLE_FORCE_PER_AXLE,
    SERVICE_VEHICLE_INSET_DISTANCE,
    SERVICE_VEHICLE_WHEEL_DIMENSION,
    SERVICE_VEHICLE_WIDTH,
    TRAM_VEHICLE_AXLE_FORCES_N,
    TRAM_VEHICLE_AXLE_SPACING,
    TRAM_VEHICLE_TRACK_GAUGE,
)
from src.integrations.scia_integration.load_system.scia_load_generators import extract_bridge_dimensions, generate_tandem_loads
from src.integrations.scia_integration.model.scia_coordinate_utils import convert_loads_to_scia_format
from src.integrations.scia_integration.model.scia_model_interface import SciaModelBuilder
from src.integrations.scia_integration.types import BridgeParametrization


def calculate_polygon_area(corner_points: list[tuple[float, float, float]]) -> float:
    """
    Calculate the area of a polygon defined by corner points using the Shoelace formula.

    :param corner_points: List of 3D corner points [(x, y, z), ...]
    :returns: Area of the polygon in the XY plane
    """
    if len(corner_points) < 3:
        return 0.0

    # Project to XY plane and apply Shoelace formula
    area = 0.0
    n = len(corner_points)
    for i in range(n):
        x1, y1, _ = corner_points[i]
        x2, y2, _ = corner_points[(i + 1) % n]
        area += x1 * y2 - x2 * y1

    return abs(area) * 0.5


def dispersal_function(  # noqa: C901
    params: object,
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_case_type: str,
    _load_case_name: str = "",
) -> tuple[list[tuple[float, float, float]], float]:
    """
    Disperse the load value across the corners based on bridge parameters.

    :param params: Bridge parameters used for dispersion logic.
    :type params: Any
    :param corner_points: list of corner points for the load (each as (x, y, z)).
    :type corner_points: list[tuple[float, float, float]]
    :param load_value: Load value to be dispersed.
    :type load_value: float
    :param load_case_type: Type of load case for dispersion calculation.
    :type load_case_type: str
    :param _load_case_name: Name of load case for debugging (optional, unused).
    :type _load_case_name: str
    :returns: Tuple of (dispersed corner points, adjusted load value).
    :rtype: tuple[list[tuple[float, float, float]], float]
    """

    def _calculate_quadrilateral_area(coords: list[tuple[float, float, float]]) -> float:
        """
        Calculates the area spanned by four coordinates (assumed to be a planar quadrilateral).

        :param coords: list of four (x, y, z) tuples representing the vertices in order.
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
        The minimum dispersion_tot across all corners is used to ensure conservative results.
        Assumes corners are ordered: [bottom-right, top-right, top-left, bottom-left].
        """
        if len(coords) != 4:
            raise ValueError("Exactly four coordinates are required.")

        # Import at runtime to avoid circular imports
        from src.integrations.scia_integration.model.scia_coordinate_utils import get_dispersion_at_coord

        # First pass: calculate dispersion_tot for each corner
        dispersion_tots = []
        for i in range(4):
            x, y, z = coords[i]
            dispersion_result = get_dispersion_at_coord(params=params, coord=coords[i])
            dispersion_deck_zones = dispersion_result["deck_zone"]  # List of dispersions
            dispersion_load_zones = dispersion_result["load_zone"]  # List of dispersions

            # For boundary cases with multiple matches, take the minimum of each layer
            # A coordinate can only physically be in one deck zone AND one load zone at a time
            min_deck_disp = min(dispersion_deck_zones) if dispersion_deck_zones else 0.0
            min_load_disp = min(dispersion_load_zones) if dispersion_load_zones else 0.0

            # Add half the deck zone dispersion and the full load zone dispersion
            deck_half = min_deck_disp / 2
            load_full = min_load_disp
            dispersion_tot = min((deck_half + load_full), 0.5)  # Ensure maximum dispersion of 0.5m to either side
            dispersion_tots.append(dispersion_tot)

        # Take minimum dispersion_tot across corners that actually intersect the deck
        positive_dispersions = [dispersion for dispersion in dispersion_tots if dispersion > 0.0]
        min_dispersion_tot = min(positive_dispersions) if positive_dispersions else 0.0

        # Second pass: expand corners using the minimum dispersion_tot
        expanded_coords = []
        dispersion_x_tot = min_dispersion_tot if load_case_type == "axle_load" else 0.0
        dispersion_y_tot = min_dispersion_tot

        for i in range(4):
            x, y, z = coords[i]
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

    # Clip dispersed coordinates to bridge boundaries
    from src.geometry.load_zone_geometry import get_bridge_geom_data
    from src.integrations.scia_integration.model.scia_coordinate_utils import move_polygon_to_bridge_boundaries

    bridge_geom_data = get_bridge_geom_data(params)  # type: ignore[arg-type]
    if bridge_geom_data is not None:
        dispersed_load_coords = move_polygon_to_bridge_boundaries(dispersed_load_coords, bridge_geom_data)

    # Calculate load areas and load value
    initial_load_area = _calculate_quadrilateral_area(coords=corner_points)

    # For point forces (area = 0), use area of 1 to avoid division by zero
    if initial_load_area == 0:
        initial_load_area = 1.0

    dispersed_load_area = _calculate_quadrilateral_area(coords=dispersed_load_coords)

    # Also check dispersed area to avoid division by zero
    if dispersed_load_area == 0:
        dispersed_load_area = 1.0

    dispersed_load_value = load_value * (initial_load_area / dispersed_load_area)

    return dispersed_load_coords, dispersed_load_value


def add_theoretical_tandem_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
    _load_cases: dict[str, Any],
) -> None:
    """
    Create theoretical tandem loads and apply them to their existing load cases.

    This function assumes that the required load cases have already been created
    by `create_all_load_cases`.

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: VIKTOR parameters for the bridge
    :type params: Any
    :param _load_cases: Dictionary of created load cases (unused but kept for compatibility)
    :type _load_cases: dict[str, Any]
    :raises ValueError: When tandem load creation fails
    """
    try:
        # Generate tandem loads based on theoretical lanes
        raw_tandem_data = generate_tandem_loads(params)  # Auto-detects mode from berekeningsniveau

        # Convert tandem data to SCIA format for surface loads
        scia_tandem_data = convert_loads_to_scia_format(raw_tandem_data)

        # Create surface loads using the builder, applying them to the correct load case
        for tandem in scia_tandem_data:
            load_case_name = tandem["load_case"]
            if params.spreiding:
                # If dispersion is enabled, adjust each patch load's corners and load value
                for patch_load in tandem["patch_loads"]:
                    dispersed_corners, dispersed_load_value = dispersal_function(
                        params=params,
                        corner_points=patch_load["corners"],
                        load_value=patch_load["load_value"],
                        load_case_type="axle_load",
                        _load_case_name=load_case_name,
                    )
                    patch_load["corners"] = dispersed_corners
                    patch_load["load_value"] = dispersed_load_value

            for i, patch_load in enumerate(tandem["patch_loads"]):
                # Check if polygon has non-zero area
                area = calculate_polygon_area(patch_load["corners"])
                if area > 0:
                    builder.create_surface_load(
                        name=f"{load_case_name}_Wheel_{i + 1}",
                        load_case_name=load_case_name,
                        corner_points=patch_load["corners"],
                        load_value=-patch_load["load_value"],  # Negative for downward load
                    )
    except Exception as e:
        raise ValueError(f"Failed to add theoretical tandem loads: {e}") from e


def add_actual_tandem_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
    _load_cases: dict[str, Any],
) -> list[Any]:
    """
    Add actual tandem loads based on user-defined lanes.

    This is a placeholder function that will be implemented when
    user-defined lanes are supported.

    :param _builder: The SCIA model builder instance (unused)
    :type _builder: SciaModelBuilder
    :param _params: VIKTOR parameters for the bridge (unused)
    :type _params: Any
    :param _load_cases: Dictionary of created load cases (unused)
    :type _load_cases: dict[str, Any]
    :returns: Empty list (placeholder)
    :rtype: list[Any]
    """
    # This will be implemented when user-defined lanes are supported.
    return []


def add_tram_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:  # noqa: C901
    """
    Add tram loads to the SCIA model at tram track centerlines.

    Tram specifications (CAF Urbos 100, drawing EE-780):
    - Total length: 30.128m
    - Track gauge: 1.435m
    - 6 axles with 97 kN per axle (static load)
    - Axle spacing from front: 0m, 1.8m, 11.812m, 13.662m, 23.674m, 25.474m

    Dynamic amplification according to NEN-EN 1991-2 art. 4.3.4.2 (d):
    - Dynamic factor Φ = 1.40 - L / 500 (with Φ >= 1.0)
    - Applied to static axle loads: Dynamic load = 97 kN × Φ

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :raises ValueError: When tram load creation fails
    """
    try:
        # Tram specifications from constants (CAF Urbos 100, drawing EE-780)
        track_gauge = TRAM_VEHICLE_TRACK_GAUGE  # Distance between rail centerlines (m)
        axle_forces_static_n = TRAM_VEHICLE_AXLE_FORCES_N  # Static forces per axle in N
        axle_distances = TRAM_VEHICLE_AXLE_SPACING  # Distances between consecutive axles (m)

        # Calculate vehicle length from sum of axle spacing
        vehicle_length = sum(axle_distances)

        # Extract bridge dimensions
        dims = extract_bridge_dimensions(params)
        length = dims.total_length
        thickness = dims.thickness

        # Calculate dynamic load factor according to NEN-EN 1991-2 art. 4.3.4.2 (d)
        # Φ = 1.40 - L / 500 (with Φ >= 1.0)
        dynamic_factor = get_dynamic_load_factor(span=length)

        # Calculate cumulative axle positions from front of tram
        axle_positions = [0.0]  # First axle at front
        cumulative = 0.0
        for distance in axle_distances:
            cumulative += distance
            axle_positions.append(cumulative)

        # Get tram track centerline coordinates
        tram_tracks = get_tram_track_y_coordinates(params)
        if tram_tracks is None or not tram_tracks:
            # No tram tracks defined, skip tram loads
            return
        from src.integrations.scia_integration.load_system.scia_load_cases import _extract_support_x_coordinates
        from src.integrations.scia_integration.load_system.tandem_sequencer import tandem_system_sequencer

        # Extract support X coordinates for fine spacing zones
        support_x_coords = _extract_support_x_coordinates(params)

        # Get positions where the front of the tram can be placed
        positions = tandem_system_sequencer(length, thickness, length_vehicle=vehicle_length, support_x_coords=support_x_coords)

        # Get load cases dictionary for tram tracks
        tram_load_cases = load_cases.get("tram_track_tandem_cases", {})
        if not tram_load_cases:
            return

        def create_tram_axle_loads(x_pos: float, track_idx: int, track_y_coords: list[float]) -> None:
            """Create all 6 axle loads for a tram at a specific X position on a specific track."""
            # Get the appropriate load case for this position and track
            load_case_key = f"tandem_tram_track{track_idx}_x{x_pos}"
            if load_case_key not in tram_load_cases:
                return

            load_case_name = tram_load_cases[load_case_key].name

            # Half gauge for wheel positioning (distance from centerline to each wheel)
            half_gauge = track_gauge / 2.0

            # Get track centerline y-coordinate at first D-point (assumed constant along length)
            track_centerline_y = track_y_coords[0]

            # Create loads for each axle
            for axle_idx, (axle_offset, static_force_n) in enumerate(zip(axle_positions, axle_forces_static_n), start=1):
                # Apply dynamic factor to this axle's static load
                force_per_axle = static_force_n * dynamic_factor  # Apply dynamic factor to static load in N
                force_per_wheel = force_per_axle / 2  # Each axle has 2 wheels (N)
                # Calculate X position of this axle
                x_axle = x_pos + axle_offset

                # Create loads for both wheels of this axle (left and right of centerline)
                for wheel_side, y_offset in [("left", half_gauge), ("right", -half_gauge)]:
                    y_wheel_center = track_centerline_y + y_offset
                    wheel_corners = [(x_axle, y_wheel_center, 0.0)] * 4  # Point load: all corners at same location

                    # Apply load dispersion if enabled
                    if params.spreiding:
                        corner_points_dispersed, load_value_dispersed = dispersal_function(
                            params=params,
                            corner_points=wheel_corners,
                            load_value=force_per_wheel,
                            load_case_type="axle_load",
                            _load_case_name=load_case_name,
                        )

                        # Check if polygon has non-zero area
                        area = calculate_polygon_area(corner_points_dispersed)
                        if area > 0:
                            builder.create_surface_load(
                                name=f"tram_track{track_idx}_x{x_pos}_axle{axle_idx}_{wheel_side}",
                                load_case_name=load_case_name,
                                corner_points=corner_points_dispersed,
                                load_value=-load_value_dispersed,  # Negative for downward load (N/m²)
                            )
                    else:
                        # Check if polygon has non-zero area
                        area = calculate_polygon_area(wheel_corners)
                        if area > 0:
                            builder.create_surface_load(
                                name=f"tram_track{track_idx}_x{x_pos}_axle{axle_idx}_{wheel_side}",
                                load_case_name=load_case_name,
                                corner_points=wheel_corners,
                                load_value=-force_per_wheel,  # Negative for downward load (N/m²)
                            )

        # Create loads for each tram position on each track
        for track_name, track_y_coords in tram_tracks.items():
            # Extract track index from track name (e.g., "tram_track_1" -> 1)
            track_idx = int(track_name.split("_")[-1])

            for x_pos in positions:
                create_tram_axle_loads(x_pos, track_idx, track_y_coords)

    except Exception as e:
        raise ValueError(f"Failed to add tram loads: {e}") from e


def _create_vehicle_wheel_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
    vehicle_config: dict[str, Any],
    wheel_forces: dict[str, float],
) -> None:
    """
    Create all wheel loads for a vehicle at a specific position.

    :param builder: SCIA model builder instance
    :param params: Bridge parameters
    :param vehicle_config: Dict with keys: x_pos, vehicle_top_edge, vehicle_length, vehicle_width,
                          wheel_contact_dimension, load_case_name, load_name_prefix
    :param wheel_forces: Dict mapping wheel corner keys to force values in N
    """
    x_pos = vehicle_config["x_pos"]
    vehicle_top_edge = vehicle_config["vehicle_top_edge"]
    vehicle_length = vehicle_config["vehicle_length"]
    vehicle_width = vehicle_config["vehicle_width"]
    wheel_contact_dimension = vehicle_config["wheel_contact_dimension"]
    load_case_name = vehicle_config["load_case_name"]
    load_name_prefix = vehicle_config["load_name_prefix"]

    # Calculate wheel center positions
    half_contact = wheel_contact_dimension / 2
    wheel_area = wheel_contact_dimension * wheel_contact_dimension

    # Define wheel positions: (x_center, y_center)
    wheel_positions = {
        "bottom_right_wheel_corners": (x_pos + vehicle_length, vehicle_top_edge - vehicle_width),
        "top_right_wheel_corners": (x_pos + vehicle_length, vehicle_top_edge),
        "top_left_wheel_corners": (x_pos, vehicle_top_edge),
        "bottom_left_wheel_corners": (x_pos, vehicle_top_edge - vehicle_width),
    }

    # Create loads for each wheel
    for wheel_idx, (wheel_key, (x_center, y_center)) in enumerate(wheel_positions.items(), start=1):
        # Skip wheels with zero force (e.g., when vehicle_width is zero)
        force_per_wheel = wheel_forces[wheel_key]
        if force_per_wheel == 0:
            continue

        # Calculate wheel corners (order: bottom-right, top-right, top-left, bottom-left)
        wheel_corners = [
            (x_center + half_contact, y_center - half_contact, 0.0),
            (x_center + half_contact, y_center + half_contact, 0.0),
            (x_center - half_contact, y_center + half_contact, 0.0),
            (x_center - half_contact, y_center - half_contact, 0.0),
        ]

        # Calculate load per area
        load_per_area = force_per_wheel / wheel_area

        # Apply dispersion
        corner_points_dispersed, load_value_dispersed = dispersal_function(
            params=params,
            corner_points=wheel_corners,
            load_value=load_per_area,
            load_case_type="axle_load",
            _load_case_name=load_case_name,
        )

        load_name = f"{load_name_prefix}_wheel{wheel_idx}"

        if params.spreiding:
            area = calculate_polygon_area(corner_points_dispersed)
            if area > 0:
                builder.create_surface_load(
                    name=load_name,
                    load_case_name=load_case_name,
                    corner_points=corner_points_dispersed,
                    load_value=-load_value_dispersed,
                )
        else:
            area = calculate_polygon_area(wheel_corners)
            if area > 0:
                builder.create_surface_load(
                    name=load_name,
                    load_case_name=load_case_name,
                    corner_points=wheel_corners,
                    load_value=-load_per_area,
                )


def add_service_vehicle_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:
    """
    Add service vehicle loads to the SCIA model using sequenced X positions.

    Implements service vehicle loads according to NEN-EN 1991-2 art. 5.3.2.3.

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :raises ValueError: When service vehicle load creation fails
    """
    try:
        # Dienstvoertuig volgens NEN-EN 1991-2 art. 5.3.2.3
        vehicle_length = SERVICE_VEHICLE_AXLE_SPACING
        vehicle_width = SERVICE_VEHICLE_WIDTH
        force_per_axle = SERVICE_VEHICLE_FORCE_PER_AXLE
        wheel_contact_dimension = SERVICE_VEHICLE_WHEEL_DIMENSION
        inset_distance = SERVICE_VEHICLE_INSET_DISTANCE
        service_vehicle_total_length = vehicle_length + wheel_contact_dimension

        # Get bridge geometry data
        bridge_geom_data = get_bridge_geom_data(params)
        if bridge_geom_data is None:
            return

        # Extract bridge dimensions and get X positions
        dims = extract_bridge_dimensions(params)
        length = dims.total_length
        thickness = dims.thickness
        from src.integrations.scia_integration.load_system.scia_load_cases import _extract_support_x_coordinates
        from src.integrations.scia_integration.load_system.tandem_sequencer import tandem_system_sequencer

        # Extract support X coordinates for fine spacing zones
        support_x_coords = _extract_support_x_coordinates(params)

        positions = tandem_system_sequencer(length, thickness, length_vehicle=service_vehicle_total_length, support_x_coords=support_x_coords)

        # Get geometry coordinates
        y_top_structural_edge_at_d_points = bridge_geom_data.y_top_structural_edge_at_d_points
        y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points

        # Get load cases dictionary
        service_vehicle_cases = load_cases["service_vehicle_cases"]

        def create_service_vehicle_at_position(x_pos: float, edge_type: str, y_coords: list[float]) -> None:
            """Create service vehicle loads at a specific X position."""
            load_case_key = f"{edge_type}_x{x_pos}"
            if load_case_key not in service_vehicle_cases:
                return

            load_case_name = service_vehicle_cases[load_case_key].name

            # Calculate vehicle top edge position with 0.5m inset from bridge edge
            if edge_type == "y_plus":
                vehicle_top_edge = y_coords[0] - inset_distance
            else:  # y_minus
                vehicle_bottom_edge = y_coords[0] + inset_distance
                vehicle_top_edge = vehicle_bottom_edge + vehicle_width

            # All wheels have equal force for service vehicle
            force_per_wheel = force_per_axle / 2
            wheel_forces = {
                "bottom_right_wheel_corners": force_per_wheel,
                "top_right_wheel_corners": force_per_wheel,
                "top_left_wheel_corners": force_per_wheel,
                "bottom_left_wheel_corners": force_per_wheel,
            }

            vehicle_config = {
                "x_pos": x_pos,
                "vehicle_top_edge": vehicle_top_edge,
                "vehicle_length": vehicle_length,
                "vehicle_width": vehicle_width,
                "wheel_contact_dimension": wheel_contact_dimension,
                "load_case_name": load_case_name,
                "load_name_prefix": f"service_vehicle_{edge_type}_x{x_pos}",
            }

            _create_vehicle_wheel_loads(
                builder=builder,
                params=params,
                vehicle_config=vehicle_config,
                wheel_forces=wheel_forces,
            )

        # Create loads for each X position on both edges
        for x_pos in positions:
            create_service_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points)
            create_service_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points)

    except Exception as e:
        raise ValueError(f"Failed to add service vehicle loads: {e}") from e


def add_accidental_vehicle_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:  # noqa: C901, PLR0915
    """
    Add accidental vehicle loads to the SCIA model using sequenced X positions.

    Implements accidental vehicle loads according to NEN-EN 1991-2 art. 5.3.2.3(1)P.

    :param builder: The SCIA model builder instance
    :type builder: SciaModelBuilder
    :param params: Bridge parameters
    :type params: BridgeParametrization
    :param load_cases: Dictionary of created load cases
    :type load_cases: dict[str, Any]
    :raises ValueError: When accidental vehicle load creation fails
    """
    try:
        # Buitengewone belasting volgens NEN-EN 1991-2 art. 5.3.2.3(1)P
        vehicle_width = ACCIDENTAL_VEHICLE_WIDTH_STANDARD
        vehicle_width_amsterdam = ACCIDENTAL_VEHICLE_WIDTH_AMSTERDAM
        force_axle_1 = ACCIDENTAL_VEHICLE_FORCE_AXLE_1
        force_axle_2 = ACCIDENTAL_VEHICLE_FORCE_AXLE_2
        force_axle_amsterdam = ACCIDENTAL_VEHICLE_FORCE_AMSTERDAM
        wheel_contact_dimension = ACCIDENTAL_VEHICLE_WHEEL_DIMENSION_STANDARD
        wheel_contact_dimension_amsterdam = ACCIDENTAL_VEHICLE_WHEEL_DIMENSION_AMSTERDAM
        axle_spacing = ACCIDENTAL_VEHICLE_AXLE_SPACING
        axle_spacing_amsterdam = ACCIDENTAL_VEHICLE_AXLE_SPACING_AMSTERDAM
        inset_distance = ACCIDENTAL_VEHICLE_INSET_DISTANCE
        accidental_vehicle_total_length = axle_spacing + wheel_contact_dimension
        accidental_vehicle_total_length_amsterdam = axle_spacing_amsterdam + wheel_contact_dimension_amsterdam

        # Get bridge geometry data
        bridge_geom_data = get_bridge_geom_data(params)
        if bridge_geom_data is None:
            return

        # Extract bridge dimensions and get X positions
        dims = extract_bridge_dimensions(params)
        length = dims.total_length
        thickness = dims.thickness
        from src.integrations.scia_integration.load_system.scia_load_cases import _extract_support_x_coordinates
        from src.integrations.scia_integration.load_system.tandem_sequencer import tandem_system_sequencer

        # Extract support X coordinates for fine spacing zones
        support_x_coords = _extract_support_x_coordinates(params)

        # Obtain different x positions for the accidental vehicles
        positions = tandem_system_sequencer(length, thickness, length_vehicle=accidental_vehicle_total_length, support_x_coords=support_x_coords)
        positions_amsterdam = tandem_system_sequencer(length, thickness, support_x_coords=support_x_coords)
        positions_amsterdam_rotated = tandem_system_sequencer(
            length, thickness, length_vehicle=accidental_vehicle_total_length_amsterdam, support_x_coords=support_x_coords
        )

        # Get geometry coordinates
        y_top_structural_edge_at_d_points = bridge_geom_data.y_top_structural_edge_at_d_points
        y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points

        # Get load cases dictionary
        unintended_vehicle_cases = load_cases["unintended_vehicle_cases"]

        def create_standard_accidental_vehicle_at_position(x_pos: float, edge_type: str, y_coords: list[float], direction: str) -> None:
            """Create standard accidental vehicle loads at a specific X position."""
            load_case_key = f"{edge_type}_x{x_pos}_{direction}"
            if load_case_key not in unintended_vehicle_cases:
                return

            load_case_name = unintended_vehicle_cases[load_case_key].name

            # Calculate vehicle top edge position with inset from bridge edge
            if edge_type == "y_plus":
                vehicle_top_edge = y_coords[0] - inset_distance
            else:  # y_minus
                vehicle_bottom_edge = y_coords[0] + inset_distance
                vehicle_top_edge = vehicle_bottom_edge + vehicle_width

            # Assign forces to wheels based on direction
            if direction == "forward":
                # Forward: 80kN front axle (TL/BL), 40kN rear axle (TR/BR)
                wheel_forces = {
                    "top_left_wheel_corners": force_axle_1 / 2,
                    "bottom_left_wheel_corners": force_axle_1 / 2,
                    "top_right_wheel_corners": force_axle_2 / 2,
                    "bottom_right_wheel_corners": force_axle_2 / 2,
                }
            else:  # reverse
                # Reverse: 40kN front axle (TL/BL), 80kN rear axle (TR/BR)
                wheel_forces = {
                    "top_left_wheel_corners": force_axle_2 / 2,
                    "bottom_left_wheel_corners": force_axle_2 / 2,
                    "top_right_wheel_corners": force_axle_1 / 2,
                    "bottom_right_wheel_corners": force_axle_1 / 2,
                }

            vehicle_config = {
                "x_pos": x_pos,
                "vehicle_top_edge": vehicle_top_edge,
                "vehicle_length": axle_spacing,
                "vehicle_width": vehicle_width,
                "wheel_contact_dimension": wheel_contact_dimension,
                "load_case_name": load_case_name,
                "load_name_prefix": f"accidental_vehicle_{edge_type}_x{x_pos}_{direction}",
            }

            _create_vehicle_wheel_loads(
                builder=builder,
                params=params,
                vehicle_config=vehicle_config,
                wheel_forces=wheel_forces,
            )

        def create_amsterdam_vehicle_at_position(x_pos: float, edge_type: str, y_coords: list[float], vehicle_type: str = "amsterdam") -> None:
            """Create Amsterdam vehicle loads at a specific X position."""
            load_case_key = f"{edge_type}_x{x_pos}_{vehicle_type}"
            if load_case_key not in unintended_vehicle_cases:
                return

            load_case_name = unintended_vehicle_cases[load_case_key].name

            # Determine if this is a rotated vehicle (90-degree rotation)
            is_rotated = "rotated" in vehicle_type

            if is_rotated:
                # Rotated: axle_spacing_amsterdam in X-direction, vehicle_width_amsterdam in Y-direction
                vehicle_length = axle_spacing_amsterdam
                vehicle_width = float(vehicle_width_amsterdam)
            else:
                # Normal: vehicle_width_amsterdam in X-direction, axle_spacing_amsterdam in Y-direction
                vehicle_length = vehicle_width_amsterdam
                vehicle_width = float(axle_spacing_amsterdam)

            # Calculate vehicle position
            if edge_type == "y_plus":
                vehicle_top_edge = y_coords[0] - inset_distance
            else:  # y_minus
                vehicle_bottom_edge = y_coords[0] + inset_distance
                vehicle_top_edge = vehicle_bottom_edge + vehicle_width

            # Configure wheel forces
            force_per_wheel = force_axle_amsterdam / 2
            if is_rotated:
                # Rotated: if width is zero, only model two wheels (top left and top right) at same X
                if vehicle_width_amsterdam == 0:
                    wheel_forces = {
                        "bottom_right_wheel_corners": 0.0,
                        "top_right_wheel_corners": force_per_wheel,
                        "top_left_wheel_corners": force_per_wheel,
                        "bottom_left_wheel_corners": 0.0,
                    }
                else:
                    wheel_forces = {
                        "bottom_right_wheel_corners": force_per_wheel,
                        "top_right_wheel_corners": force_per_wheel,
                        "top_left_wheel_corners": force_per_wheel,
                        "bottom_left_wheel_corners": force_per_wheel,
                    }
            # Non-rotated: if width_amsterdam is zero, only model two wheels (top left and bottom left) at same Y
            elif vehicle_width_amsterdam == 0:
                wheel_forces = {
                    "bottom_right_wheel_corners": 0.0,
                    "top_right_wheel_corners": 0.0,
                    "top_left_wheel_corners": force_per_wheel,
                    "bottom_left_wheel_corners": force_per_wheel,
                }
            else:
                wheel_forces = {
                    "bottom_right_wheel_corners": force_per_wheel,
                    "top_right_wheel_corners": force_per_wheel,
                    "top_left_wheel_corners": force_per_wheel,
                    "bottom_left_wheel_corners": force_per_wheel,
                }

            vehicle_config = {
                "x_pos": x_pos,
                "vehicle_top_edge": vehicle_top_edge,
                "vehicle_length": vehicle_length,
                "vehicle_width": vehicle_width,
                "wheel_contact_dimension": wheel_contact_dimension_amsterdam,
                "load_case_name": load_case_name,
                "load_name_prefix": f"amsterdam_vehicle_{edge_type}_x{x_pos}_{vehicle_type}",
            }

            _create_vehicle_wheel_loads(
                builder=builder,
                params=params,
                vehicle_config=vehicle_config,
                wheel_forces=wheel_forces,
            )

        # Create loads for all positions and vehicle types
        # Standard vehicle: forward and reverse directions for each position
        for x_pos in positions:
            create_standard_accidental_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points, "forward")
            create_standard_accidental_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points, "reverse")
            create_standard_accidental_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points, "forward")
            create_standard_accidental_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points, "reverse")

        # Amsterdam vehicle: single direction per position
        for x_pos in positions_amsterdam:
            create_amsterdam_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points, "amsterdam")
            create_amsterdam_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points, "amsterdam")

        # Amsterdam vehicle rotated: single direction per position
        for x_pos in positions_amsterdam_rotated:
            create_amsterdam_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points, "amsterdam_rotated")
            create_amsterdam_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points, "amsterdam_rotated")

    except Exception as e:
        raise ValueError(f"Failed to add accidental vehicle loads: {e}") from e
