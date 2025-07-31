"""
Module for creating SCIA loads.

This module provides functions for creating SCIA loads by calling the SciaModelBuilder.
These functions are pure Python and can be used by the app layer to construct the actual SCIA model.
"""

from dataclasses import dataclass
from typing import Any

from src.geometry.load_zone_geometry import get_bridge_geom_data

from .scia_bridge_geometry import (
    convert_tandem_data_to_scia_format,
    extract_tandem_parameters_from_bridge,
    generate_tandem_loads_for_bridge,
)
from .scia_loads_helper import add_material_loads, calc_vehicle_load_locations, tandem_system_sequencer
from .scia_model_interface import SciaModelBuilder

# Type alias to avoid importing from app layer
BridgeParametrization = Any


@dataclass
class VehicleConfig:
    """Configuration for a vehicle load type."""

    vehicle_width: float
    wheel_contact_area: float
    force_per_wheel: float

    def get_wheel_load_n(self) -> float:
        """Get wheel load in Newtons."""
        return self.force_per_wheel * 1000


@dataclass
class DualAxleVehicleConfig:
    """Configuration for a dual-axle vehicle load type."""

    vehicle_width: float
    wheel_contact_area: float
    front_axle_force: float  # Total force for front axle (kN)
    rear_axle_force: float  # Total force for rear axle (kN)
    axle_spacing: float

    def get_front_wheel_load_n(self) -> float:
        """Get front wheel load in Newtons (per wheel)."""
        return (self.front_axle_force * 1000) // 2

    def get_rear_wheel_load_n(self) -> float:
        """Get rear wheel load in Newtons (per wheel)."""
        return (self.rear_axle_force * 1000) // 2


# Vehicle configurations according to NEN-EN 1991-2
SERVICE_VEHICLE_CONFIG = VehicleConfig(
    vehicle_width=1.75,
    wheel_contact_area=0.25,
    force_per_wheel=25,  # kN per axle, distributed over 4 wheels
)

ACCIDENTAL_VEHICLE_CONFIG = DualAxleVehicleConfig(
    vehicle_width=1.30,  # From diagram: 1.30 m between wheel centers
    wheel_contact_area=0.20,  # From diagram: 0.20 m contact area
    front_axle_force=80,  # Q_sv1 = 80 kN
    rear_axle_force=40,  # Q_sv2 = 40 kN
    axle_spacing=1.2,  # Derived from 3.0m total - wheel contact areas
)


def _calculate_vehicle_y_base(y_coords: list[float], edge_type: str, wheel_contact_area: float, vehicle_width: float) -> float:
    """Calculate Y base coordinate for vehicle positioning on bridge edge."""
    base_coord = y_coords[0]
    if edge_type in ("y_plus", "rs_1"):
        return base_coord - wheel_contact_area / 2
    # y_minus, rs_3
    return base_coord + wheel_contact_area / 2 + vehicle_width


def _create_wheel_surface_loads(
    builder: SciaModelBuilder,
    load_case_name: str,
    name_prefix: str,
    wheel_locations: dict[str, list[tuple[float, float, float]]],
    load_value: float,
) -> None:
    """Create surface loads for all wheels in a vehicle."""
    for wheel_name, wheel_corners in wheel_locations.items():
        builder.create_surface_load(
            name=f"{name_prefix}_{wheel_name.replace('_corners', '')}",
            load_case_name=load_case_name,
            corner_points=wheel_corners,
            load_value=-load_value,  # Negative for downward load
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
    raw_tandem_data = generate_tandem_loads_for_bridge(bridge_params, mode="theoretical")

    # 3. Convert tandem data to SCIA format for surface loads
    scia_tandem_data = convert_tandem_data_to_scia_format(raw_tandem_data)

    # 4. Create surface loads using the builder, applying them to the correct load case

    for tandem in scia_tandem_data:
        # Only process dicts that have both 'load_case' and 'patch_loads' keys
        if "load_case" in tandem and "patch_loads" in tandem:
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


def add_accidental_vehicle_loads(builder: SciaModelBuilder, params: BridgeParametrization, load_cases: dict[str, Any]) -> None:
    """Add accidental vehicle loads to the SCIA model using sequenced X positions."""
    # Buitengewone belasting volgens NEN-EN 1991-2 art. 5.3.2.3(1)P
    config = ACCIDENTAL_VEHICLE_CONFIG

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

        # Calculate Y base coordinate using helper
        y_base = _calculate_vehicle_y_base(y_coords, edge_type, config.wheel_contact_area, config.vehicle_width)

        # Determine front axle position based on direction (80 kN axle should always be the "front")
        # Forward: 80 kN front axle at x_pos, 40 kN rear axle at x_pos + axle_spacing
        # Reverse: 80 kN front axle at x_pos + axle_spacing, 40 kN rear axle at x_pos
        front_axle_x = x_pos if direction == "forward" else x_pos + config.axle_spacing

        # Calculate axle positions for both front and rear axles
        rear_axle_x = front_axle_x + config.axle_spacing if direction == "forward" else front_axle_x - config.axle_spacing

        # Get wheel locations for both axles (using single axle approach)
        front_axle_locations = calc_vehicle_load_locations(
            x_coord=front_axle_x,
            y_coord=y_base + config.wheel_contact_area / 2,  # Adjust for calc_vehicle_load_locations coordinate system
            vehicle_length=config.wheel_contact_area,  # Single axle, so length = contact area
            vehicle_width=config.vehicle_width,
            wheel_contact_area=config.wheel_contact_area,
        )

        rear_axle_locations = calc_vehicle_load_locations(
            x_coord=rear_axle_x,
            y_coord=y_base + config.wheel_contact_area / 2,  # Adjust for calc_vehicle_load_locations coordinate system
            vehicle_length=config.wheel_contact_area,  # Single axle, so length = contact area
            vehicle_width=config.vehicle_width,
            wheel_contact_area=config.wheel_contact_area,
        )

        # Create surface loads for front axle using helper
        _create_wheel_surface_loads(
            builder=builder,
            load_case_name=load_case_name,
            name_prefix=f"accidental_vehicle_{edge_type}_x{x_pos}_{direction}_front",
            wheel_locations=front_axle_locations,
            load_value=config.get_front_wheel_load_n(),
        )

        # Create surface loads for rear axle using helper
        _create_wheel_surface_loads(
            builder=builder,
            load_case_name=load_case_name,
            name_prefix=f"accidental_vehicle_{edge_type}_x{x_pos}_{direction}_rear",
            wheel_locations=rear_axle_locations,
            load_value=config.get_rear_wheel_load_n(),
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
    config = SERVICE_VEHICLE_CONFIG
    vehicle_length = 3.0

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

        # Calculate Y base coordinate using helper
        y_base = _calculate_vehicle_y_base(y_coords, edge_type, config.wheel_contact_area, config.vehicle_width)

        # Use the helper function to calculate wheel positions
        wheel_locations = calc_vehicle_load_locations(
            x_coord=x_pos,
            y_coord=y_base + config.wheel_contact_area / 2,  # Adjust for calc_vehicle_load_locations coordinate system
            vehicle_length=vehicle_length,
            vehicle_width=config.vehicle_width,
            wheel_contact_area=config.wheel_contact_area,
        )

        # Create surface loads for all wheels using helper
        _create_wheel_surface_loads(
            builder=builder,
            load_case_name=load_case_name,
            name_prefix=f"service_vehicle_{edge_type}_x{x_pos}",
            wheel_locations=wheel_locations,
            load_value=config.get_wheel_load_n(),
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
    add_theoretical_tandem_loads(builder, params, load_cases)

    add_service_vehicle_loads(builder, params, load_cases)
    add_accidental_vehicle_loads(builder, params, load_cases)

    # TODO: Add calls to other load functions when they are implemented
    # add_actual_tandem_loads(builder, params, load_cases)  # noqa: ERA001
    # add_railing_loads(builder, params, load_cases)  # noqa: ERA001
    # add_pedestrian_loads(builder, params, load_cases)  # noqa: ERA001
