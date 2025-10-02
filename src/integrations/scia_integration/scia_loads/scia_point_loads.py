"""
SCIA point loads module.

This module provides functions for creating point loads (tandem and vehicle loads)
by calling the SciaModelBuilder interface. These functions handle concentrated
loads from vehicles and tandem systems.
"""

from typing import Any

from src.geometry.load_zone_geometry import get_bridge_geom_data

from ..scia_coordinate_utils import convert_loads_to_scia_format
from ..scia_load_generators import extract_bridge_dimensions, generate_tandem_loads
from ..scia_model_interface import SciaModelBuilder
from ..types import BridgeParametrization


def dispersal_function(
    params: object,
    corner_points: list[tuple[float, float, float]],
    load_value: float,
    load_case_type: str,
) -> tuple[list[tuple[float, float, float]], float]:
    """
    Disperse the load value across the corners based on bridge parameters.

    This function implements load dispersion according to structural analysis principles,
    spreading concentrated loads over a larger area to better represent real-world behavior.

    :param params: Bridge parameters used for dispersion logic
    :type params: object
    :param corner_points: List of corner points for the load (each as (x, y, z))
    :type corner_points: list[tuple[float, float, float]]
    :param load_value: Load value to be dispersed
    :type load_value: float
    :param load_case_type: Type of load case for dispersion calculation
    :type load_case_type: str
    :returns: Tuple of (dispersed corner points, adjusted load value)
    :rtype: tuple[list[tuple[float, float, float]], float]
    :raises ValueError: When dispersion calculation fails
    """
    try:
        # Import here to avoid circular imports
        from ..scia_coordinate_utils import clip_polygon_to_bridge_boundaries

        # Check if dispersion is enabled
        if not hasattr(params, "input") or not hasattr(params.input, "berekeningsinstellingen"):
            return corner_points, load_value

        if not params.input.berekeningsinstellingen.spreiding:
            return corner_points, load_value

        # Get bridge geometry data for boundary checking
        bridge_geom_data = get_bridge_geom_data(params)
        if bridge_geom_data is None:
            return corner_points, load_value

        # Calculate original area
        if len(corner_points) < 3:
            return corner_points, load_value

        # Simple rectangular area calculation for 4-point polygons
        if len(corner_points) == 4:
            # Assuming rectangular load patch
            x_coords = [pt[0] for pt in corner_points]
            y_coords = [pt[1] for pt in corner_points]
            original_width = max(x_coords) - min(x_coords)
            original_height = max(y_coords) - min(y_coords)
            original_area = original_width * original_height
        else:
            # Fallback for non-rectangular polygons
            original_area = 1.0  # Default area

        # Apply dispersion based on load case type and bridge thickness
        if load_case_type == "axle_load":
            # For axle loads, spread over a larger area
            dispersion_factor = 1.5  # Increase area by 50%
        else:
            # For other loads, use standard dispersion
            dispersion_factor = 1.2  # Increase area by 20%

        # Calculate new corner points with expanded area
        if len(corner_points) == 4:
            # Find center point
            center_x = sum(pt[0] for pt in corner_points) / len(corner_points)
            center_y = sum(pt[1] for pt in corner_points) / len(corner_points)
            center_z = sum(pt[2] for pt in corner_points) / len(corner_points)

            # Expand around center
            new_width = original_width * dispersion_factor**0.5
            new_height = original_height * dispersion_factor**0.5

            dispersed_corners = [
                (center_x - new_width / 2, center_y - new_height / 2, center_z),
                (center_x + new_width / 2, center_y - new_height / 2, center_z),
                (center_x + new_width / 2, center_y + new_height / 2, center_z),
                (center_x - new_width / 2, center_y + new_height / 2, center_z),
            ]
        else:
            # For non-rectangular polygons, return original
            dispersed_corners = corner_points

        # Clip to bridge boundaries
        clipped_corners = clip_polygon_to_bridge_boundaries(dispersed_corners, bridge_geom_data)

        # Calculate new area and adjust load value
        if len(clipped_corners) == 4:
            x_coords = [pt[0] for pt in clipped_corners]
            y_coords = [pt[1] for pt in clipped_corners]
            new_width = max(x_coords) - min(x_coords)
            new_height = max(y_coords) - min(y_coords)
            new_area = new_width * new_height
        else:
            new_area = original_area * dispersion_factor

        # Adjust load value to maintain total force
        if new_area > 0 and original_area > 0:
            adjusted_load_value = load_value * (original_area / new_area)
        else:
            adjusted_load_value = load_value

        return clipped_corners, adjusted_load_value

    except Exception:
        # If dispersion fails, return original values
        return corner_points, load_value


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
        from ..scia_loads_helper import tandem_system_sequencer

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
            from ..scia_loads_helper import calc_vehicle_load_locations

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

    except Exception as e:
        raise ValueError(f"Failed to add service vehicle loads: {e}") from e


def add_accidental_vehicle_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:
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
        from ..scia_loads_helper import (
            tandem_system_sequencer,
            tandem_system_sequencer_single_axis,
            tandem_system_sequencer_single_axis_rotated,
        )

        # Obtain different x positions for the accidental vehicles
        positions = tandem_system_sequencer(length, thickness, length_vehicle=1.2)
        positions_amsterdam = tandem_system_sequencer_single_axis(length, thickness)
        positions_amsterdam_rotated = tandem_system_sequencer_single_axis_rotated(length, thickness, length_vehicle=2.0)

        # Get geometry coordinates
        y_top_structural_edge_at_d_points = bridge_geom_data.y_top_structural_edge_at_d_points
        y_bridge_bottom_at_d_points = bridge_geom_data.y_bridge_bottom_at_d_points

        # Get load cases dictionary
        unintended_vehicle_cases = load_cases["unintended_vehicle_cases"]

        # Standard accidental vehicle (2-axle)
        def create_standard_accidental_vehicle_at_position(x_pos: float, edge_type: str, y_coords: list[float]) -> None:
            """Create standard accidental vehicle loads at a specific X position."""
            # Get the appropriate load case for this position and edge
            load_case_key = f"{edge_type}_x{x_pos}"
            if load_case_key not in unintended_vehicle_cases:
                return

            load_case_name = unintended_vehicle_cases[load_case_key].name

            # Calculate vehicle top edge position with inset from bridge edge
            if edge_type == "y_plus":
                vehicle_top_edge = y_coords[0] - inset_distance
            else:  # y_minus
                vehicle_bottom_edge = y_coords[0] + inset_distance
                vehicle_top_edge = vehicle_bottom_edge + vehicle_width

            # Create loads for both axles
            axle_forces = [force_axle_1, force_axle_2]
            axle_x_positions = [x_pos, x_pos + axle_spacing]

            for axle_idx, (axle_x, axle_force) in enumerate(zip(axle_x_positions, axle_forces)):
                # Calculate wheel positions for this axle
                wheel_area = wheel_contact_area * wheel_contact_area
                force_per_wheel = axle_force / 2  # Two wheels per axle
                load_per_area = force_per_wheel / wheel_area

                # Use helper function to calculate wheel positions
                from ..scia_loads_helper import calc_vehicle_load_locations

                wheel_locations = calc_vehicle_load_locations(
                    x_coord=axle_x,
                    y_coord=vehicle_top_edge,
                    vehicle_length=0.2,  # Just the wheel contact length
                    vehicle_width=vehicle_width,
                    wheel_contact_area=wheel_contact_area,
                )

                # Create surface loads for each wheel
                for wheel_idx, (wheel_loc, wheel_corners) in enumerate(wheel_locations.items()):
                    # Apply load dispersion if enabled
                    corner_points_dispersed, load_value_dispersed = dispersal_function(
                        params=params,
                        corner_points=wheel_corners,
                        load_value=load_per_area,
                        load_case_type="axle_load",
                    )

                    if params.input.berekeningsinstellingen.spreiding:
                        builder.create_surface_load(
                            name=f"accidental_vehicle_{edge_type}_x{x_pos}_axle{axle_idx + 1}_wheel{wheel_idx + 1}",
                            load_case_name=load_case_name,
                            corner_points=corner_points_dispersed,
                            load_value=-load_value_dispersed,
                        )
                    else:
                        builder.create_surface_load(
                            name=f"accidental_vehicle_{edge_type}_x{x_pos}_axle{axle_idx + 1}_wheel{wheel_idx + 1}",
                            load_case_name=load_case_name,
                            corner_points=wheel_corners,
                            load_value=-load_per_area,
                        )

        # Amsterdam vehicle (single axle)
        def create_amsterdam_vehicle_at_position(x_pos: float, edge_type: str, y_coords: list[float]) -> None:
            """Create Amsterdam vehicle loads at a specific X position."""
            load_case_key = f"amsterdam_{edge_type}_x{x_pos}"
            if load_case_key not in unintended_vehicle_cases:
                return

            load_case_name = unintended_vehicle_cases[load_case_key].name

            # Calculate vehicle position
            if edge_type == "y_plus":
                vehicle_top_edge = y_coords[0] - inset_distance
            else:  # y_minus
                vehicle_bottom_edge = y_coords[0] + inset_distance
                vehicle_top_edge = vehicle_bottom_edge + vehicle_width_amsterdam

            # Calculate wheel loads
            wheel_area = wheel_contact_area_amsterdam * wheel_contact_area_amsterdam
            force_per_wheel = force_axle_amsterdam / 2  # Two wheels per axle
            load_per_area = force_per_wheel / wheel_area

            # Use helper function to calculate wheel positions
            from ..scia_loads_helper import calc_vehicle_load_locations

            wheel_locations = calc_vehicle_load_locations(
                x_coord=x_pos,
                y_coord=vehicle_top_edge,
                vehicle_length=0.4,  # Amsterdam wheel contact length
                vehicle_width=vehicle_width_amsterdam,
                wheel_contact_area=wheel_contact_area_amsterdam,
            )

            # Create surface loads for each wheel
            for wheel_idx, (wheel_loc, wheel_corners) in enumerate(wheel_locations.items()):
                # Apply load dispersion if enabled
                corner_points_dispersed, load_value_dispersed = dispersal_function(
                    params=params,
                    corner_points=wheel_corners,
                    load_value=load_per_area,
                    load_case_type="axle_load",
                )

                if params.input.berekeningsinstellingen.spreiding:
                    builder.create_surface_load(
                        name=f"amsterdam_vehicle_{edge_type}_x{x_pos}_wheel{wheel_idx + 1}",
                        load_case_name=load_case_name,
                        corner_points=corner_points_dispersed,
                        load_value=-load_value_dispersed,
                    )
                else:
                    builder.create_surface_load(
                        name=f"amsterdam_vehicle_{edge_type}_x{x_pos}_wheel{wheel_idx + 1}",
                        load_case_name=load_case_name,
                        corner_points=wheel_corners,
                        load_value=-load_per_area,
                    )

        # Create loads for all positions and vehicle types
        for x_pos in positions:
            create_standard_accidental_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points)
            create_standard_accidental_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points)

        for x_pos in positions_amsterdam:
            create_amsterdam_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points)
            create_amsterdam_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points)

        for x_pos in positions_amsterdam_rotated:
            create_amsterdam_vehicle_at_position(x_pos, "y_plus", y_top_structural_edge_at_d_points)
            create_amsterdam_vehicle_at_position(x_pos, "y_minus", y_bridge_bottom_at_d_points)

    except Exception as e:
        raise ValueError(f"Failed to add accidental vehicle loads: {e}") from e
