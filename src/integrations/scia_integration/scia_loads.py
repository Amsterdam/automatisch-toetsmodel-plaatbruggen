"""
Module for creating SCIA loads.

This module provides functions for creating SCIA loads by calling the SciaModelBuilder.
These functions are pure Python and can be used by the app layer to construct the actual SCIA model.
"""

from typing import Any

from app.bridge.parametrization import BridgeParametrization
from src.geometry.load_zone_geometry import calculate_zone_geometry_properties, get_bridge_geom_data, get_load_zones_data_from_params

from .scia_bridge_geometry import (
    convert_tandem_data_to_scia_format,
    extract_tandem_parameters_from_bridge,
    generate_tandem_loads_for_bridge,
)
from .scia_loads_helper import calculate_pavement_load_from_material
from .scia_model_interface import SciaModelBuilder


def add_theoretical_tandem_loads(
    builder: SciaModelBuilder,
    params: Any,  # noqa: ANN401
) -> None:
    """
    Create theoretical tandem loads and apply them to their existing load cases.

    This function assumes that the required load cases have already been created
    by `create_all_load_cases`.

    :param builder: The SCIA model builder instance.
    :param params: VIKTOR parameters for the bridge.
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
) -> list[Any]:
    """PLACEHOLDER: Add actual tandem loads based on user-defined lanes."""
    # This will be implemented when user-defined lanes are supported.
    return []


def add_railing_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add railing loads to the SCIA model."""
    # This will be implemented based on railing parameters.
    return []


def add_pedestrian_loads(
    _builder: SciaModelBuilder,
    _params: Any,  # noqa: ANN401
) -> list[Any]:
    """PLACEHOLDER: Add pedestrian loads to the SCIA model."""
    # This will be implemented based on pedestrian area parameters.
    return []


def add_asfalt_loads(
    builder: SciaModelBuilder,
    params: BridgeParametrization,
) -> list[Any]:
    """PLACEHOLDER: Add asphalt loads to the SCIA model."""
    # Get unit weight for asphalt loads

    # Get load zone information from params using the utility functions
    load_zones_data_params = get_load_zones_data_from_params(params)
    bridge_geom_data = get_bridge_geom_data(params)
    load_zones_data_params = calculate_zone_geometry_properties(load_zones_data_params, bridge_geom_data)

    # Check if bridge geometry data is available
    if bridge_geom_data is None:
        return []

    # Iterate through load zones and apply asphalt loads
    i = 0
    for load_zone in load_zones_data_params:
        if load_zone.get("pavement_material", BridgeParametrization) == "Asfalt":
            # Iterate through spans
            for span in range(len(load_zone["y_coords_top_current_zone"]) - 1):
                # Create individual surface load for each span in the asphalt zone
                y_coord_top_left = round(load_zone["y_coords_top_current_zone"][span], 2)
                y_coord_top_right = round(load_zone["y_coords_top_current_zone"][span + 1], 2)
                y_coord_bottom_left = round(y_coord_top_left - load_zone["zone_widths_per_d"][span], 2)
                y_coord_bottom_right = round(y_coord_top_right - load_zone["zone_widths_per_d"][span + 1], 2)
                x_coord_left = round(bridge_geom_data.x_coords_d_points[span], 2)
                x_coord_right = round(bridge_geom_data.x_coords_d_points[span + 1], 2)
                corners = [
                    (x_coord_left, y_coord_top_left, 0.0),
                    (x_coord_right, y_coord_top_right, 0.0),
                    (x_coord_right, y_coord_bottom_right, 0.0),
                    (x_coord_left, y_coord_bottom_left, 0.0),
                ]

                builder.create_surface_load(
                    name=f"{load_zone['zone_type']}_{i}_Asfalt_{span}_d{load_zone['pavement_thickness']}",
                    load_case_name="BG2001",  # TODO is dit correct?
                    corner_points=corners,
                    load_value=-calculate_pavement_load_from_material(load_zone["pavement_thickness"], load_zone["pavement_material"])
                    * 1000,  # Convert to kN/m²
                )
        i += 1


def create_all_loads(builder: SciaModelBuilder, params: BridgeParametrization) -> None:
    """
    Create and apply all load types to the bridge model.

    This function orchestrates the application of all loads, including:
    - Tandem system loads
    - Railing loads (placeholder)
    - Pedestrian loads (placeholder)

    :param builder: The SCIA model builder instance.
    :param params: Bridge parameters.
    """
    # Apply theoretical tandem loads
    add_theoretical_tandem_loads(builder, params)
    add_asfalt_loads(builder, params)

    # TODO: Add calls to other load functions when they are implemented
    # add_actual_tandem_loads(builder, params)  # noqa: ERA001
    # add_railing_loads(builder, params)  # noqa: ERA001
    # add_pedestrian_loads(builder, params)  # noqa: ERA001
